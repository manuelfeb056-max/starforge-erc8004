#!/usr/bin/env python3
"""
play-agent.py — demo bot that plays STARFORGE as an ERC-8004 agent (Monad testnet).

Flow:
  1. register() on the ERC-8004 Identity Registry -> agentId (one-time;
     skipped if AGENT_ID is set)
  2. linkAgent(agentId) on AgentReputation (one-time per wallet; skipped if
     already linked)
  3. loop N sessions: openSession -> wait for randomness -> fulfillSpin ->
     [supernova: submitPicks(random 5, collect)] -> settle ->
     session RTP is posted as ERC-8004 feedback automatically by the Arena

TESTNET ONLY. Uses a throwaway key from AGENT_PRIVATE_KEY; never a real wallet.
No mainnet, no real value.

Requires: pip install web3 eth-account

Env:
  MONAD_TESTNET_RPC  (default https://testnet-rpc.monad.xyz)
  AGENT_PRIVATE_KEY  throwaway testnet key (required)
  IDENTITY_REGISTRY  ERC-8004 Identity Registry address (required)
  STARFORGE_ARENA    StarforgeArena address (required)
  AGENT_REPUTATION   AgentReputation address (required)
  RANDOMNESS         IRandomness provider address (required)
  AGENT_ID           existing ERC-8004 agent id (optional, skips registration)
  AGENT_URI          registration file URI for register() (default: ./agent/registration.json as data URI note)

Usage:
  python3 agent/play-agent.py --sessions 3 --wager-wei 1000000000000000
"""
import argparse
import json
import os
import random
import sys
import time

MONAD_TESTNET_RPC = os.environ.get("MONAD_TESTNET_RPC", "https://testnet-rpc.monad.xyz")
PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "")
IDENTITY_REGISTRY = os.environ.get("IDENTITY_REGISTRY", "")
ARENA = os.environ.get("STARFORGE_ARENA", "")
AGENT_REPUTATION = os.environ.get("AGENT_REPUTATION", "")
RANDOMNESS = os.environ.get("RANDOMNESS", "")
AGENT_ID = os.environ.get("AGENT_ID", "")
AGENT_URI = os.environ.get("AGENT_URI", "https://nueve.sh/agents/starforge-player.json")

STAGE = {0: "NONE", 1: "WAIT_SPIN", 2: "WAIT_PICKS", 3: "WAIT_GAMBLE", 4: "SETTLED"}

IDENTITY_ABI = json.loads("""[
 {"name":"register","type":"function","stateMutability":"nonpayable",
  "inputs":[{"name":"agentURI","type":"string"},
            {"name":"metadata","type":"tuple[]","components":[
              {"name":"metadataKey","type":"string"},{"name":"metadataValue","type":"bytes"}]}],
  "outputs":[{"name":"agentId","type":"uint256"}]},
 {"name":"ownerOf","type":"function","stateMutability":"view",
  "inputs":[{"name":"tokenId","type":"uint256"}],"outputs":[{"name":"","type":"address"}]},
 {"name":"Registered","type":"event","anonymous":false,
  "inputs":[{"name":"agentId","type":"uint256","indexed":true},
            {"name":"agentURI","type":"string","indexed":false},
            {"name":"owner","type":"address","indexed":true}]}
]""")

SPIN_RESULT_TUPLE = {
    "name": "spin", "type": "tuple",
    "components": [
        {"name": "stage", "type": "uint8"},
        {"name": "gridWinBps", "type": "uint256"},
        {"name": "artifacts", "type": "uint8"},
        {"name": "prizes", "type": "uint16[12]"},
        {"name": "grids", "type": "bytes"},
        {"name": "stepWins", "type": "uint256[]"},
        {"name": "stepPats", "type": "uint8[]"},
        {"name": "stepCount", "type": "uint8"},
        {"name": "picksBps", "type": "uint256"},
        {"name": "picks", "type": "uint8[5]"},
        {"name": "gambleWin", "type": "bool"},
        {"name": "totalBps", "type": "uint256"},
    ],
}

ARENA_ABI = json.loads("""[
 {"name":"openSession","type":"function","stateMutability":"payable",
  "inputs":[{"name":"artifacts","type":"uint8"}],"outputs":[{"name":"sessionId","type":"uint256"}]},
 {"name":"fulfillSpin","type":"function","stateMutability":"nonpayable",
  "inputs":[{"name":"sessionId","type":"uint256"}]},
 {"name":"submitPicks","type":"function","stateMutability":"nonpayable",
  "inputs":[{"name":"sessionId","type":"uint256"},{"name":"picks","type":"uint8[5]"},{"name":"gamble","type":"bool"}]},
 {"name":"fulfillGamble","type":"function","stateMutability":"nonpayable",
  "inputs":[{"name":"sessionId","type":"uint256"}]},
 {"name":"forfeit","type":"function","stateMutability":"nonpayable",
  "inputs":[{"name":"sessionId","type":"uint256"}]},
 {"name":"SessionOpened","type":"event","anonymous":false,
  "inputs":[{"name":"sessionId","type":"uint256","indexed":true},
            {"name":"player","type":"address","indexed":true},
            {"name":"wager","type":"uint256","indexed":false},
            {"name":"artifacts","type":"uint8","indexed":false}]},
 {"name":"SessionSettled","type":"event","anonymous":false,
  "inputs":[{"name":"sessionId","type":"uint256","indexed":true},
            {"name":"player","type":"address","indexed":true},
            {"name":"payout","type":"uint256","indexed":false},
            {"name":"totalBps","type":"uint256","indexed":false}]}
]""") + [
    {"name": "sessions", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "", "type": "uint256"}],
     "outputs": [
         {"name": "player", "type": "address"},
         {"name": "wager", "type": "uint256"},
         {"name": "artifacts", "type": "uint8"},
         {"name": "stage", "type": "uint8"},
         SPIN_RESULT_TUPLE,
         {"name": "randomnessId", "type": "uint32"},
     ]},
]

REPUTATION_ABI = json.loads("""[
 {"name":"linkAgent","type":"function","stateMutability":"nonpayable",
  "inputs":[{"name":"agentId","type":"uint256"}]},
 {"name":"walletToAgent","type":"function","stateMutability":"view",
  "inputs":[{"name":"","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
 {"name":"lifetimeRtpBps","type":"function","stateMutability":"view",
  "inputs":[{"name":"agentId","type":"uint256"}],"outputs":[{"name":"","type":"uint256"}]}
]""")

RANDOMNESS_ABI = json.loads("""[
 {"name":"isReady","type":"function","stateMutability":"view",
  "inputs":[{"name":"requestId","type":"uint32"}],"outputs":[{"name":"","type":"bool"}]}
]""")


def send(w3, fn, account, value=0):
    tx = fn.build_transaction({
        "from": account.address,
        "value": value,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gasPrice": w3.eth.gas_price,
    })
    tx["gas"] = w3.eth.estimate_gas(tx)
    signed = account.sign_transaction(tx)
    txh = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(txh, timeout=120)


def wait_randomness(w3, rand, request_id, timeout_s=300):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if rand.functions.isReady(request_id).call():
            return True
        time.sleep(2)
    return False


def play_session(w3, arena, rand, account, wager_wei, artifacts, gamble):
    # 1. open
    rcpt = send(w3, arena.functions.openSession(artifacts), account, value=wager_wei)
    ev = arena.events.SessionOpened().process_receipt(rcpt)[0]["args"]
    sid = ev["sessionId"]
    print(f"  session {sid}: opened, wager={wager_wei} wei")

    # 2. spin
    sess = arena.functions.sessions(sid).call()
    if not wait_randomness(w3, rand, sess[5]):
        print("  randomness timeout; forfeiting")
        send(w3, arena.functions.forfeit(sid), account)
        return None
    send(w3, arena.functions.fulfillSpin(sid), account)
    sess = arena.functions.sessions(sid).call()
    stage = sess[3]
    print(f"  session {sid}: stage={STAGE.get(stage, stage)}")

    # 3. supernova picks
    if stage == 2:
        picks = random.sample(range(12), 5)
        rcpt = send(w3, arena.functions.submitPicks(sid, picks, gamble), account)
        print(f"  session {sid}: picks={picks} gamble={gamble}")
        sess = arena.functions.sessions(sid).call()
        stage = sess[3]

    # 4. gamble coin flip
    if stage == 3:
        sess = arena.functions.sessions(sid).call()
        if not wait_randomness(w3, rand, sess[5]):
            print("  gamble randomness timeout; forfeiting")
            send(w3, arena.functions.forfeit(sid), account)
            return None
        send(w3, arena.functions.fulfillGamble(sid), account)

    # 5. read settlement
    logs = arena.events.SessionSettled().get_logs(from_block=max(0, rcpt["blockNumber"] - 50))
    hit = [l for l in logs if l["args"]["sessionId"] == sid]
    if not hit:
        print(f"  session {sid}: no SessionSettled found")
        return None
    payout = hit[0]["args"]["payout"]
    total_bps = hit[0]["args"]["totalBps"]
    rtp_bps = (payout * 10000) // wager_wei if wager_wei else 0
    print(f"  session {sid}: payout={payout} totalBps={total_bps} rtp={rtp_bps/100:.2f}%")
    return {"sessionId": sid, "payout": payout, "totalBps": total_bps, "rtpBps": rtp_bps}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--wager-wei", type=int, default=10**15)
    ap.add_argument("--artifacts", type=int, default=0x07)
    ap.add_argument("--gamble", action="store_true", help="double-or-nothing on supernova")
    ap.add_argument("--sleep", type=int, default=5, help="seconds between sessions")
    args = ap.parse_args()

    missing = [k for k, v in {
        "AGENT_PRIVATE_KEY": PRIVATE_KEY, "IDENTITY_REGISTRY": IDENTITY_REGISTRY,
        "STARFORGE_ARENA": ARENA, "AGENT_REPUTATION": AGENT_REPUTATION,
        "RANDOMNESS": RANDOMNESS}.items() if not v]
    if missing:
        raise SystemExit(f"Missing env: {', '.join(missing)} (testnet addresses, see scripts/deploy-testnet.md)")

    from web3 import Web3
    from eth_account import Account
    w3 = Web3(Web3.HTTPProvider(MONAD_TESTNET_RPC, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        raise SystemExit(f"Cannot reach RPC {MONAD_TESTNET_RPC}")
    print(f"chain id: {w3.eth.chain_id}")
    account = Account.from_key(PRIVATE_KEY)
    print(f"agent wallet: {account.address} (TESTNET ONLY)")

    identity = w3.eth.contract(address=IDENTITY_REGISTRY, abi=IDENTITY_ABI)
    arena = w3.eth.contract(address=ARENA, abi=ARENA_ABI)
    reputation = w3.eth.contract(address=AGENT_REPUTATION, abi=REPUTATION_ABI)
    rand = w3.eth.contract(address=RANDOMNESS, abi=RANDOMNESS_ABI)

    # 1. register agent identity (one-time)
    if AGENT_ID:
        agent_id = int(AGENT_ID)
        print(f"using existing agent id {agent_id}")
    else:
        print(f"registering agent (uri={AGENT_URI}) ...")
        rcpt = send(w3, identity.functions.register(AGENT_URI, []), account)
        ev = identity.events.Registered().process_receipt(rcpt)
        if not ev:
            raise SystemExit("register() mined but no Registered event — check the registry ABI")
        agent_id = ev[0]["args"]["agentId"]
        print(f"registered agent id {agent_id} — save as AGENT_ID to skip next time")

    # 2. link wallet -> agent (one-time)
    linked = reputation.functions.walletToAgent(account.address).call()
    if linked == 0:
        print(f"linking wallet to agent {agent_id} ...")
        send(w3, reputation.functions.linkAgent(agent_id), account)
        print("linked")
    else:
        print(f"already linked to agent {linked}")
        agent_id = linked

    # 3. play loop
    results = []
    for n in range(args.sessions):
        print(f"[session {n+1}/{args.sessions}]")
        try:
            r = play_session(w3, arena, rand, account, args.wager_wei, args.artifacts, args.gamble)
            if r:
                results.append(r)
        except Exception as e:  # noqa: BLE001 — keep the loop alive on testnet flakiness
            print(f"  error: {type(e).__name__}: {str(e)[:160]}")
        if n < args.sessions - 1:
            time.sleep(args.sleep)

    if results:
        avg_rtp = sum(r["rtpBps"] for r in results) / len(results)
        lifetime = reputation.functions.lifetimeRtpBps(agent_id).call()
        print(f"\ndone: {len(results)} sessions, avg session RTP {avg_rtp/100:.2f}%, "
              f"lifetime RTP on-chain {lifetime/100:.2f}%")
    else:
        print("\ndone: no settled sessions")


if __name__ == "__main__":
    main()
