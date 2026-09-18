#!/usr/bin/env python3
"""
index.py — minimal event indexer feeding the agent leaderboard.

Reads:
  - StarforgeArena.SessionOpened(sessionId, player, wager, artifacts)
  - StarforgeArena.SessionSettled(sessionId, player, payout, totalBps)
  - AgentReputation.AgentLinked(wallet, agentId)
  - ERC-8004 ReputationRegistry.NewFeedback(agentId, clientAddress, ...)
    (filtered to our AgentReputation as client, tag1 == "starforge")

Writes indexer/leaderboard.json:
  [{agentId, wallet, sessions, wageredWei, paidWei, rtpBps,
    feedbackCount, lastSessionBlock}]

Usage:
  python3 indexer/index.py [--from-block N] [--out leaderboard.json]

Reads deployments/testnet.json + deployments/abis.json (written by deploy.py).
TESTNET ONLY. Read-only: no keys, no transactions.
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEPLOY = os.path.join(ROOT, "deployments", "testnet.json")
ABIS = os.path.join(ROOT, "deployments", "abis.json")

# Official ERC-8004 ReputationRegistry NewFeedback event (verified against
# erc-8004-contracts ReputationRegistryUpgradeable.sol):
# NewFeedback(uint256 indexed agentId, address indexed clientAddress,
#   uint64 feedbackIndex, int128 value, uint8 valueDecimals,
#   string indexed indexedTag1, string tag1, string tag2,
#   string endpoint, string feedbackURI, bytes32 feedbackHash)
NEW_FEEDBACK_ABI = [{
    "name": "NewFeedback", "type": "event", "anonymous": False,
    "inputs": [
        {"name": "agentId", "type": "uint256", "indexed": True},
        {"name": "clientAddress", "type": "address", "indexed": True},
        {"name": "feedbackIndex", "type": "uint64", "indexed": False},
        {"name": "value", "type": "int128", "indexed": False},
        {"name": "valueDecimals", "type": "uint8", "indexed": False},
        {"name": "indexedTag1", "type": "string", "indexed": True},
        {"name": "tag1", "type": "string", "indexed": False},
        {"name": "tag2", "type": "string", "indexed": False},
        {"name": "endpoint", "type": "string", "indexed": False},
        {"name": "feedbackURI", "type": "string", "indexed": False},
        {"name": "feedbackHash", "type": "bytes32", "indexed": False},
    ],
}]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-block", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "leaderboard.json"))
    ap.add_argument("--rpc", default=os.environ.get(
        "MONAD_TESTNET_RPC", "https://rpc.ankr.com/monad_testnet"))
    args = ap.parse_args()

    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        raise SystemExit(f"cannot reach {args.rpc}")

    dep = json.load(open(DEPLOY))
    abis = json.load(open(ABIS))
    arena = w3.eth.contract(address=dep["starforgeArena"], abi=abis["StarforgeArena"])
    rep = w3.eth.contract(address=dep["agentReputation"], abi=abis["AgentReputation"])
    reg = w3.eth.contract(address=dep["reputationRegistry"], abi=NEW_FEEDBACK_ABI)

    latest = w3.eth.block_number
    print(f"scanning blocks {args.from_block}..{latest}")

    def chunked_logs(event, lo, hi, step=100):
        out = []
        b = lo
        while b <= hi:
            e = min(b + step - 1, hi)
            out += event.get_logs(from_block=b, to_block=e)
            b = e + 1
        return out

    # 1. wallet -> agentId links
    wallet_of = {}   # agentId -> wallet
    for ev in chunked_logs(rep.events.AgentLinked(), args.from_block, latest):
        a = ev["args"]
        wallet_of[a["agentId"]] = a["wallet"]
    print(f"  AgentLinked: {len(wallet_of)} agents")

    # 2. sessions: join Opened (wager) + Settled (payout)
    wagers = {}
    for ev in chunked_logs(arena.events.SessionOpened(), args.from_block, latest):
        a = ev["args"]
        wagers[a["sessionId"]] = {"player": a["player"], "wager": a["wager"],
                                  "block": ev["blockNumber"]}
    settled = chunked_logs(arena.events.SessionSettled(), args.from_block, latest)
    print(f"  sessions: {len(wagers)} opened, {len(settled)} settled")

    agents = {}
    for ev in settled:
        a = ev["args"]
        sid = a["sessionId"]
        if sid not in wagers:
            continue
        # player -> agentId via our link registry (scan walletOf reverse)
        player = wagers[sid]["player"]
        agent_id = next((gid for gid, w in wallet_of.items() if w == player), None)
        if agent_id is None:
            continue  # unlinked player: no reputation
        st = agents.setdefault(agent_id, {"sessions": 0, "wagered": 0, "paid": 0,
                                          "lastBlock": 0, "feedback": 0})
        st["sessions"] += 1
        st["wagered"] += wagers[sid]["wager"]
        st["paid"] += a["payout"]
        st["lastBlock"] = max(st["lastBlock"], ev["blockNumber"])

    # 3. on-chain feedback count from the official registry (client = our AgentReputation)
    for ev in chunked_logs(reg.events.NewFeedback(), args.from_block, latest):
        a = ev["args"]
        if a["clientAddress"].lower() != dep["agentReputation"].lower():
            continue
        if a["tag1"] != "starforge":
            continue
        gid = a["agentId"]
        if gid in agents:
            agents[gid]["feedback"] += 1
    print(f"  NewFeedback (ours): {sum(s['feedback'] for s in agents.values())}")

    board = []
    for gid, st in agents.items():
        rtp = (st["paid"] * 10000) // st["wagered"] if st["wagered"] else 0
        board.append({
            "agentId": gid,
            "wallet": wallet_of.get(gid),
            "sessions": st["sessions"],
            "wageredWei": str(st["wagered"]),
            "paidWei": str(st["paid"]),
            "rtpBps": rtp,
            "rtpPct": round(rtp / 100, 2),
            "feedbackCount": st["feedback"],
            "lastSessionBlock": st["lastBlock"],
        })
    board.sort(key=lambda r: (-r["sessions"], -r["rtpBps"]))

    out = {"chainId": dep["chainId"], "arena": dep["starforgeArena"],
           "scannedThrough": latest, "agents": board}
    json.dump(out, open(args.out, "w"), indent=2)
    print(f"wrote {args.out}: {len(board)} agents")
    for r in board:
        print(f"  agent {r['agentId']}: {r['sessions']} sessions, "
              f"RTP {r['rtpPct']}%, feedback {r['feedbackCount']}")


if __name__ == "__main__":
    main()
