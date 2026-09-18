#!/usr/bin/env python3
"""
deploy.py — compile + deploy Starforge x ERC-8004 to Monad TESTNET (chain 10143).

Order: StarforgeGame -> BlockhashRandomness -> AgentReputation(identity, reputation)
       -> StarforgeArena(game, randomness) -> wiring setArena/setReputation.

Env:
  DEPLOYER_KEY   throwaway testnet private key (required; never a real wallet)
  MONAD_TESTNET_RPC (default https://rpc.ankr.com/monad_testnet)
  IDENTITY_REGISTRY (default 0x8004A818BFB912233c491871b3d84c89A494BD9e)
  REPUTATION_REGISTRY (default 0x8004B663056A597Dffe9eCcC1965A193B7388713)

Writes deployed addresses to ../deployments/testnet.json
TESTNET ONLY. No mainnet.
"""
import json
import os
import sys
import time

RPC = os.environ.get("MONAD_TESTNET_RPC", "https://rpc.ankr.com/monad_testnet")
DEPLOYER_KEY = os.environ.get("DEPLOYER_KEY", "")
IDENTITY = os.environ.get("IDENTITY_REGISTRY", "0x8004A818BFB912233c491871b3d84c89A494BD9e")
REPUTATION = os.environ.get("REPUTATION_REGISTRY", "0x8004B663056A597Dffe9eCcC1965A193B7388713")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "deployments", "testnet.json")

if not DEPLOYER_KEY:
    raise SystemExit("DEPLOYER_KEY required (throwaway testnet key)")

from web3 import Web3
from eth_account import Account
import solcx

solcx.set_solc_version("0.8.28")

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
if not w3.is_connected():
    raise SystemExit(f"cannot reach {RPC}")
assert w3.eth.chain_id == 10143, f"wrong chain: {w3.eth.chain_id}"
acct = Account.from_key(DEPLOYER_KEY)
print(f"deployer: {acct.address}")
bal = w3.eth.get_balance(acct.address)
print(f"balance: {w3.from_wei(bal, 'ether')} MON")
if bal == 0:
    raise SystemExit("no testnet MON — fund the throwaway wallet from a faucet first")


def compile_all():
    sources = {}
    for root, _, files in os.walk(os.path.join(ROOT, "contracts")):
        for f in files:
            if f.endswith(".sol"):
                p = os.path.join(root, f)
                rel = os.path.relpath(p, os.path.join(ROOT, "contracts"))
                sources[rel] = {"content": open(p).read()}
    compiled = solcx.compile_standard({
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "viaIR": True,  # required: giveFeedback's 8-arg call overflows legacy codegen
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
            "optimizer": {"enabled": True, "runs": 200}},
    }, allow_paths=[os.path.join(ROOT, "contracts")])
    out = {}
    for path, contracts in compiled["contracts"].items():
        for name, c in contracts.items():
            out[name] = (c["abi"], c["evm"]["bytecode"]["object"])
    return out


def send_tx(tx):
    tx.update({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
    })
    # EIP-1559 chains: build_transaction already fills maxFeePerGas;
    # mixing gasPrice with it breaks signing. Use one fee model only.
    if "maxFeePerGas" in tx:
        tx.pop("gasPrice", None)
    else:
        tx["gasPrice"] = w3.eth.gas_price
    tx["gas"] = w3.eth.estimate_gas(tx)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    if rcpt["status"] != 1:
        raise RuntimeError(f"tx failed: {h.hex()}")
    return rcpt


def deploy(artifacts, name, *args):
    abi, bytecode = artifacts[name]
    c = w3.eth.contract(abi=abi, bytecode=bytecode)
    rcpt = send_tx(c.constructor(*args).build_transaction({"from": acct.address}))
    addr = rcpt["contractAddress"]
    print(f"  {name} -> {addr} (tx {rcpt['transactionHash'].hex()[:16]}...)")
    return addr, abi


def main():
    print("compiling...")
    artifacts = compile_all()
    print(f"  compiled: {sorted(artifacts)}")

    deployed = {"chainId": 10143, "rpc": RPC,
                "identityRegistry": IDENTITY, "reputationRegistry": REPUTATION}

    print("deploying...")
    game_addr, _ = deploy(artifacts, "StarforgeGame")
    rand_addr, _ = deploy(artifacts, "BlockhashRandomness")
    rep_addr, rep_abi = deploy(artifacts, "AgentReputation", IDENTITY, REPUTATION)
    arena_addr, arena_abi = deploy(artifacts, "StarforgeArena", game_addr, rand_addr)

    print("wiring...")
    rep = w3.eth.contract(address=rep_addr, abi=rep_abi)
    send_tx(rep.functions.setArena(arena_addr).build_transaction({"from": acct.address}))
    print("  AgentReputation.setArena done")
    _, arena_abi_full = artifacts["StarforgeArena"]
    arena = w3.eth.contract(address=arena_addr, abi=arena_abi_full)
    send_tx(arena.functions.setReputation(rep_addr).build_transaction({"from": acct.address}))
    print("  StarforgeArena.setReputation done")

    deployed.update({
        "starforgeGame": game_addr,
        "blockhashRandomness": rand_addr,
        "agentReputation": rep_addr,
        "starforgeArena": arena_addr,
        "deployer": acct.address,
    })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(deployed, open(OUT, "w"), indent=2)
    abis = {name: abi for name, (abi, _) in artifacts.items()
            if name in ("StarforgeArena", "AgentReputation", "StarforgeGame",
                        "BlockhashRandomness", "IERC8004Identity", "IERC8004Reputation")}
    json.dump(abis, open(os.path.join(os.path.dirname(OUT), "abis.json"), "w"), indent=2)
    print(f"wrote {OUT} (+ abis.json)")
    print(json.dumps(deployed, indent=2))


if __name__ == "__main__":
    main()
