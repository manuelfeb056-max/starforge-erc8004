#!/usr/bin/env python3
"""
play-agent.py — demo bot that plays STARFORGE as an ERC-8004 agent (Monad testnet).

Flow:
  1. register() on the ERC-8004 Identity Registry -> agentId (one-time)
  2. linkAgent(agentId) on AgentReputation (one-time per wallet)
  3. loop: openSession -> wait blocks -> fulfillSpin ->
     [supernova: submitPicks(random 5, collect)] -> settle ->
     session RTP posted as ERC-8004 feedback automatically by the Arena

TESTNET ONLY. Uses a throwaway key; never a real wallet.
Requires: pip install web3 eth-account

Addresses are filled in after deploy (see scripts/deploy-testnet.md).
"""
import json
import os
import random
import time

MONAD_TESTNET_RPC = os.environ.get("MONAD_TESTNET_RPC", "https://testnet-rpc.monad.xyz")
PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "")  # throwaway testnet key only

IDENTITY_REGISTRY = os.environ.get("IDENTITY_REGISTRY", "")
ARENA = os.environ.get("STARFORGE_ARENA", "")
AGENT_REPUTATION = os.environ.get("AGENT_REPUTATION", "")

WAGER_WEI = 10**15  # 0.001 test MON per session
ARTIFACTS = 0x07    # all artifacts (brasa + yunque + temple)

# Minimal ABIs (full ABIs generated at build time)
IDENTITY_ABI = json.loads('[{"name":"register","type":"function","inputs":[{"name":"agentURI","type":"string"},{"name":"metadata","type":"tuple[]","components":[{"name":"metadataKey","type":"string"},{"name":"metadataValue","type":"bytes"}]}],"outputs":[{"name":"agentId","type":"uint256"}]}]')


def main() -> None:
    if not PRIVATE_KEY:
        raise SystemExit("Set AGENT_PRIVATE_KEY (throwaway testnet key) first.")
    # NOTE: skeleton — full web3.py wiring lands in week 2 (see docs/MILESTONES.md).
    print(f"RPC: {MONAD_TESTNET_RPC}")
    print(f"Arena: {ARENA or '<deploy first>'}")
    print("Pick strategy for supernova: uniform random 5 of 12, always collect.")
    print("TODO: implement session loop with web3.py")


if __name__ == "__main__":
    main()
