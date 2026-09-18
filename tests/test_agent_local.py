#!/usr/bin/env python3
"""Integration: run play_agent.play_session against a local py-evm chain.

Deploys Game + MockRandomness + Arena + mocks + AgentReputation locally,
rigs a supernova seed, and drives the agent's real session function.
Proves the agent wiring works end-to-end (no testnet needed).

Exit 0 = pass.
"""
import os
import sys

ROOT = os.path.expanduser("~/workspace/monad/starforge-erc8004")
sys.path.insert(0, os.path.join(ROOT, "agent"))

import solcx  # noqa: E402
from eth_hash.auto import keccak  # noqa: E402
from web3 import Web3  # noqa: E402
from web3.providers.eth_tester import EthereumTesterProvider  # noqa: E402
from eth_account import Account  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "play_agent", os.path.join(ROOT, "agent", "play-agent.py"))
play_agent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(play_agent)

solcx.set_solc_version("0.8.28")
contracts_dir = os.path.join(ROOT, "contracts")
files = [
    os.path.join(contracts_dir, "StarforgeGame.sol"),
    os.path.join(contracts_dir, "StarforgeArena.sol"),
    os.path.join(contracts_dir, "AgentReputation.sol"),
]
compiled = solcx.compile_files(files, output_values=["abi", "bin"],
                               solc_version="0.8.28", allow_paths=contracts_dir)
mocked = solcx.compile_source(play_agent.__doc__ and """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract MockIdentity {
    mapping(uint256 => address) public owners;
    function setAgent(uint256 id, address o) external { owners[id] = o; }
    function ownerOf(uint256 id) external view returns (address) { return owners[id]; }
    function getAgentWallet(uint256) external pure returns (address) { return address(0); }
}
contract MockReputation {
    uint256 public n;
    function giveFeedback(uint256,int128,uint8,bytes32,bytes32,string calldata,string calldata,bytes32) external { n++; }
}
interface IRandomness {
    function requestRandomness() external returns (uint32);
    function isReady(uint32) external view returns (bool);
    function fulfillRandomness(uint32) external returns (bytes32);
}
contract MockRandomness is IRandomness {
    bytes32 public nextSeed; uint32 private _nid = 1; mapping(uint32 => bool) public ready;
    function setSeed(bytes32 s) external { nextSeed = s; }
    function requestRandomness() external override returns (uint32 id) { id = _nid++; ready[id] = true; }
    function isReady(uint32 id) external view override returns (bool) { return ready[id]; }
    function fulfillRandomness(uint32 id) external override returns (bytes32) {
        require(ready[id]); ready[id] = false; return nextSeed;
    }
}
""", output_values=["abi", "bin"], solc_version="0.8.28")


def get(d, name):
    return next(c for cid, c in d.items() if cid.endswith(":" + name))


w3 = Web3(EthereumTesterProvider())
funder = w3.eth.accounts[0]
acct = Account.from_key("0x" + "42" * 32)
w3.eth.send_transaction({"from": funder, "to": acct.address, "value": w3.to_wei(5, "ether")})


def deploy(cdef, *args):
    c = w3.eth.contract(abi=cdef["abi"], bytecode=cdef["bin"])
    txh = c.constructor(*args).transact({"from": funder})
    return w3.eth.contract(address=w3.eth.get_transaction_receipt(txh)["contractAddress"], abi=cdef["abi"])


game = deploy(get(compiled, "StarforgeGame"))
mock_rand = deploy(get(mocked, "MockRandomness"))
arena = deploy(get(compiled, "StarforgeArena"), game.address, mock_rand.address)
mock_id = deploy(get(mocked, "MockIdentity"))
mock_rep = deploy(get(mocked, "MockReputation"))
rep = deploy(get(compiled, "AgentReputation"), mock_id.address, mock_rep.address)
arena.functions.setReputation(rep.address).transact({"from": funder})
rep.functions.setArena(arena.address).transact({"from": funder})
w3.eth.send_transaction({"from": funder, "to": arena.address, "value": w3.to_wei(10, "ether")})

# rig supernova seed
sn_seed = next(s for i in range(500)
               if (s := keccak(f"sn-search-{i}".encode()))
               and game.functions.spin(s, 7).call({"from": funder})[0] == 1)
mock_rand.functions.setSeed(sn_seed).transact({"from": funder})

# link agent identity (as the agent would)
mock_id.functions.setAgent(7, acct.address).transact({"from": funder})
rc = play_agent.send(w3, rep.functions.linkAgent(7), acct)
assert rep.functions.walletToAgent(acct.address).call() == 7, "linkAgent failed"
print("PASS linkAgent via play_agent.send")

arena_c = w3.eth.contract(address=arena.address, abi=play_agent.ARENA_ABI)
rand_c = w3.eth.contract(address=mock_rand.address, abi=play_agent.RANDOMNESS_ABI)
WAGER = 10**15
r = play_agent.play_session(w3, arena_c, rand_c, acct, WAGER, 0x07, False)
assert r is not None, "play_session returned None"
assert r["payout"] == game.functions.payoutFor(WAGER, r["totalBps"]).call(), "payout mismatch"
assert mock_rep.functions.n().call() == 1, "reputation feedback not recorded"
print(f"PASS play_session end-to-end: payout={r['payout']} rtp={r['rtpBps']/100:.2f}% feedback=1")
print("ALL AGENT INTEGRATION CHECKS PASSED")
