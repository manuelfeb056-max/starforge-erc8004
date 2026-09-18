#!/usr/bin/env python3
"""Arena cycle tests: session -> escrow -> spin -> [picks -> gamble] -> settle
-> reputation hook. Mocks for ERC-8004 registries and randomness.

Exit 0 = all pass. Any failure aborts with details.
"""
import os
import sys

ROOT = os.path.expanduser("~/workspace/monad/starforge-erc8004")

import solcx  # noqa: E402
from eth_hash.auto import keccak  # noqa: E402
from web3 import Web3  # noqa: E402
from web3.providers.eth_tester import EthereumTesterProvider  # noqa: E402

solcx.install_solc("0.8.28")
solcx.set_solc_version("0.8.28")

MOCK_SRC = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract MockIdentity {
    mapping(uint256 => address) public owners;
    mapping(uint256 => address) public wallets;
    function setAgent(uint256 id, address o, address w) external { owners[id] = o; wallets[id] = w; }
    function ownerOf(uint256 id) external view returns (address) { return owners[id]; }
    function getAgentWallet(uint256 id) external view returns (address) { return wallets[id]; }
}
contract MockReputation {
    struct Fb { uint256 agentId; int128 value; uint8 dec; bytes32 t1; bytes32 t2; }
    Fb[] public fbs;
    function giveFeedback(uint256 a, int128 v, uint8 d, bytes32 t1, bytes32 t2,
                          string calldata, string calldata, bytes32) external {
        fbs.push(Fb(a, v, d, t1, t2));
    }
    function count() external view returns (uint256) { return fbs.length; }
}
interface IRandomness {
    function requestRandomness() external returns (uint32);
    function isReady(uint32) external view returns (bool);
    function fulfillRandomness(uint32) external returns (bytes32);
}
contract MockRandomness is IRandomness {
    bytes32 public nextSeed;
    uint32 private _nid = 1;
    mapping(uint32 => bool) public ready;
    function setSeed(bytes32 s) external { nextSeed = s; }
    function requestRandomness() external override returns (uint32 id) { id = _nid++; ready[id] = true; }
    function isReady(uint32 id) external view override returns (bool) { return ready[id]; }
    function fulfillRandomness(uint32 id) external override returns (bytes32) {
        require(ready[id], "not ready"); ready[id] = false; return nextSeed;
    }
}
"""

contracts_dir = os.path.join(ROOT, "contracts")
files = [
    os.path.join(contracts_dir, "StarforgeGame.sol"),
    os.path.join(contracts_dir, "StarforgeArena.sol"),
    os.path.join(contracts_dir, "AgentReputation.sol"),
    os.path.join(contracts_dir, "randomness", "BlockhashRandomness.sol"),
]
compiled = solcx.compile_files(files, output_values=["abi", "bin"],
                               solc_version="0.8.28", allow_paths=contracts_dir)
mocked = solcx.compile_source(MOCK_SRC, output_values=["abi", "bin"], solc_version="0.8.28")


def get(compiled_dict, name):
    for cid, cdef in compiled_dict.items():
        if cid.endswith(":" + name):
            return cdef
    raise KeyError(name)


w3 = Web3(EthereumTesterProvider())
tester = w3.provider.ethereum_tester
owner, player, stranger = w3.eth.accounts[0], w3.eth.accounts[1], w3.eth.accounts[2]

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" [{detail}]" if detail and not cond else ""))


def deploy(cdef, *args, frm=owner):
    c = w3.eth.contract(abi=cdef["abi"], bytecode=cdef["bin"])
    txh = c.constructor(*args).transact({"from": frm})
    return w3.eth.contract(address=w3.eth.get_transaction_receipt(txh)["contractAddress"], abi=cdef["abi"])


game = deploy(get(compiled, "StarforgeGame"))
bh_rand = deploy(get(compiled, "BlockhashRandomness"))
arena = deploy(get(compiled, "StarforgeArena"), game.address, bh_rand.address)
mock_rand = deploy(get(mocked, "MockRandomness"))
arena_mock = deploy(get(compiled, "StarforgeArena"), game.address, mock_rand.address)
mock_id = deploy(get(mocked, "MockIdentity"))
mock_rep = deploy(get(mocked, "MockReputation"))
reputation = deploy(get(compiled, "AgentReputation"), mock_id.address, mock_rep.address)

# wiring (two-step, one-time; one AgentReputation per Arena by design)
arena.functions.setReputation(reputation.address).transact({"from": owner})
reputation.functions.setArena(arena.address).transact({"from": owner})
reputation2 = deploy(get(compiled, "AgentReputation"), mock_id.address, mock_rep.address)
arena_mock.functions.setReputation(reputation2.address).transact({"from": owner})
reputation2.functions.setArena(arena_mock.address).transact({"from": owner})
# fund prize pool so 1000x-cap payouts never revert in tests
w3.eth.send_transaction({"from": owner, "to": arena.address, "value": w3.to_wei(10, "ether")})
w3.eth.send_transaction({"from": owner, "to": arena_mock.address, "value": w3.to_wei(10, "ether")})

WAGER = w3.to_wei("0.01", "ether")
STAGE = {0: "NONE", 1: "WAIT_SPIN", 2: "WAIT_PICKS", 3: "WAIT_GAMBLE", 4: "SETTLED"}


def stage_of(a, sid):
    return a.functions.sessions(sid).call()[3]


def settle_info(a, sid):
    s = a.functions.sessions(sid).call()
    spin = s[4]
    return {"stage": s[3], "totalBps": spin[11], "picksBps": spin[8], "gridWinBps": spin[1]}


# ---- 1. basic cycle on BlockhashRandomness (no supernova expected) ----
sid = arena.functions.openSession(0).transact({"from": player, "value": WAGER})
sid = arena.events.SessionOpened().process_receipt(w3.eth.get_transaction_receipt(sid))[0]["args"]["sessionId"]
check("openSession stage=WAIT_SPIN", stage_of(arena, sid) == 1)
try:
    arena.functions.fulfillSpin(sid).transact({"from": player})
    check("fulfillSpin too early reverts", False)
except Exception:
    check("fulfillSpin too early reverts", True)
tester.mine_blocks(4)
arena.functions.fulfillSpin(sid).transact({"from": player})
info = settle_info(arena, sid)
if info["stage"] == 4:
    exp = game.functions.payoutFor(WAGER, info["totalBps"]).call()
    check("no-supernova auto-settles", True, f"totalBps={info['totalBps']}")
    logs = arena.events.SessionSettled().get_logs(from_block=0)
    last = [l for l in logs if l["args"]["sessionId"] == sid][0]["args"]
    check("SessionSettled payout==expected", last["payout"] == exp, f"{last['payout']} vs {exp}")
    check("SessionSettled totalBps matches", last["totalBps"] == info["totalBps"])
else:
    check("no-supernova auto-settles", False, f"stage={STAGE[info['stage']]}")

# ---- 2. supernova: collect path (mock randomness, rigged seed) ----
sn_seed = None
for i in range(500):
    s = keccak(f"sn-search-{i}".encode())
    if game.functions.spin(s, 7).call({"from": owner})[0] == 1:
        sn_seed = s
        break
check("found supernova seed", sn_seed is not None)
mock_rand.functions.setSeed(sn_seed).transact({"from": owner})
tx = arena_mock.functions.openSession(7).transact({"from": player, "value": WAGER})
sid2 = arena_mock.events.SessionOpened().process_receipt(w3.eth.get_transaction_receipt(tx))[0]["args"]["sessionId"]
arena_mock.functions.fulfillSpin(sid2).transact({"from": player})
check("supernova -> WAIT_PICKS", stage_of(arena_mock, sid2) == 2)
# wrong player cannot pick
try:
    arena_mock.functions.submitPicks(sid2, [0, 1, 2, 3, 4], False).transact({"from": stranger})
    check("submitPicks NotPlayer", False)
except Exception:
    check("submitPicks NotPlayer", True)
# duplicate picks revert
try:
    arena_mock.functions.submitPicks(sid2, [0, 0, 1, 2, 3], False).transact({"from": player})
    check("submitPicks dup BadPicks", False)
except Exception:
    check("submitPicks dup BadPicks", True)
bal_before = w3.eth.get_balance(arena_mock.address)
arena_mock.functions.submitPicks(sid2, [0, 1, 2, 3, 4], False).transact({"from": player})
info2 = settle_info(arena_mock, sid2)
check("collect -> SETTLED", info2["stage"] == 4)
exp2 = game.functions.payoutFor(WAGER, info2["totalBps"]).call()
logs = arena_mock.events.SessionSettled().get_logs(from_block=0)
last2 = [l for l in logs if l["args"]["sessionId"] == sid2][0]["args"]
check("collect payout==expected", last2["payout"] == exp2, f"picksBps={info2['picksBps']}")
check("arena paid out of escrow+pool", w3.eth.get_balance(arena_mock.address) == bal_before - exp2)

# ---- 3. supernova: gamble path ----
mock_rand.functions.setSeed(sn_seed).transact({"from": owner})
tx = arena_mock.functions.openSession(0).transact({"from": player, "value": WAGER})
sid3 = arena_mock.events.SessionOpened().process_receipt(w3.eth.get_transaction_receipt(tx))[0]["args"]["sessionId"]
arena_mock.functions.fulfillSpin(sid3).transact({"from": player})
arena_mock.functions.submitPicks(sid3, [5, 6, 7, 8, 9], True).transact({"from": player})
check("gamble -> WAIT_GAMBLE", stage_of(arena_mock, sid3) == 3)
gseed = keccak(b"gamble-test-seed")
mock_rand.functions.setSeed(gseed).transact({"from": owner})
arena_mock.functions.fulfillGamble(sid3).transact({"from": player})
info3 = settle_info(arena_mock, sid3)
spin3 = arena_mock.functions.getSpin(sid3).call()
exp_win = (gseed[0] % 2) == 0
check("gamble settled", info3["stage"] == 4)
check("gambleWin matches coin", spin3[10] == exp_win)
exp_total3 = info3["gridWinBps"] + (info3["picksBps"] * 2 if exp_win else 0)
check("gamble totalBps", info3["totalBps"] == exp_total3)

# ---- 4. forfeit ----
tx = arena.functions.openSession(0).transact({"from": player, "value": WAGER})
sid4 = arena.events.SessionOpened().process_receipt(w3.eth.get_transaction_receipt(tx))[0]["args"]["sessionId"]
b0 = w3.eth.get_balance(player)
arena.functions.forfeit(sid4).transact({"from": player})
check("forfeit returns wager", w3.eth.get_balance(player) > b0)
check("forfeit stage=SETTLED", stage_of(arena, sid4) == 4)
try:
    arena.functions.forfeit(sid4).transact({"from": player})
    check("double forfeit reverts", False)
except Exception:
    check("double forfeit reverts", True)

# ---- 5. reputation hook (via arena_mock + reputation2) ----
mock_id.functions.setAgent(42, player, player).transact({"from": owner})
reputation2.functions.linkAgent(42).transact({"from": player})
check("linkAgent maps wallet", reputation2.functions.walletToAgent(player).call() == 42)
try:
    reputation2.functions.linkAgent(42).transact({"from": player})
    check("double link reverts", False)
except Exception:
    check("double link reverts", True)
try:
    reputation2.functions.linkAgent(42).transact({"from": stranger})
    check("linkAgent NotAgentOwner", False)
except Exception:
    check("linkAgent NotAgentOwner", True)
fb0 = mock_rep.functions.count().call()
mock_rand.functions.setSeed(sn_seed).transact({"from": owner})
tx = arena_mock.functions.openSession(0).transact({"from": player, "value": WAGER})
sid5 = arena_mock.events.SessionOpened().process_receipt(w3.eth.get_transaction_receipt(tx))[0]["args"]["sessionId"]
arena_mock.functions.fulfillSpin(sid5).transact({"from": player})
arena_mock.functions.submitPicks(sid5, [0, 1, 2, 3, 4], False).transact({"from": player})
check("feedback recorded", mock_rep.functions.count().call() == fb0 + 1)
fb = mock_rep.functions.fbs(fb0).call()
info5 = settle_info(arena_mock, sid5)
exp_rtp = (game.functions.payoutFor(WAGER, info5["totalBps"]).call() * 10000) // WAGER
check("feedback value=session RTP bps", fb[1] == exp_rtp, f"{fb[1]} vs {exp_rtp}")
check("feedback tags", fb[3] == keccak(b"starforge") and fb[4] == keccak(b"session"))
check("lifetimeRtpBps", reputation2.functions.lifetimeRtpBps(42).call() == exp_rtp)
check("agentSessions==1", reputation2.functions.agentSessions(42).call() == 1)
# unlinked player earns no feedback
fb1 = mock_rep.functions.count().call()
mock_rand.functions.setSeed(sn_seed).transact({"from": owner})
tx = arena_mock.functions.openSession(0).transact({"from": stranger, "value": WAGER})
sid6 = arena_mock.events.SessionOpened().process_receipt(w3.eth.get_transaction_receipt(tx))[0]["args"]["sessionId"]
arena_mock.functions.fulfillSpin(sid6).transact({"from": stranger})
arena_mock.functions.submitPicks(sid6, [0, 1, 2, 3, 4], False).transact({"from": stranger})
check("unlinked player: no feedback", mock_rep.functions.count().call() == fb1)

# ---- 6. guards & caps ----
try:
    arena.functions.openSession(0).transact({"from": player, "value": 0})
    check("openSession ZeroWager", False)
except Exception:
    check("openSession ZeroWager", True)
try:
    arena.functions.setReputation(reputation.address).transact({"from": owner})
    check("setReputation twice reverts", False)
except Exception:
    check("setReputation twice reverts", True)
try:
    arena.functions.setReputation(stranger).transact({"from": stranger})
    check("setReputation OnlyOwner", False)
except Exception:
    check("setReputation OnlyOwner", True)
cap = game.functions.payoutFor(WAGER, 50_000_000).call()
check("payoutFor caps at 1000x", cap == WAGER * 1000, str(cap))
check("expectedPayout==97.60%", game.functions.expectedPayout(WAGER).call() == WAGER * 9760 // 10000)
# submitPicks in wrong stage
try:
    arena.functions.submitPicks(sid, [0, 1, 2, 3, 4], False).transact({"from": player})
    check("submitPicks wrong stage reverts", False)
except Exception:
    check("submitPicks wrong stage reverts", True)

print(f"\n{len(passed)} passed, {len(failed)} failed")
for f in failed:
    print("FAILED:", f)
sys.exit(1 if failed else 0)
