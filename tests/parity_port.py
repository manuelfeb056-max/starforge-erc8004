#!/usr/bin/env python3
"""Parity: ported StarforgeGame.sol (Monad) vs reference Python simulator.

Compiles contracts/StarforgeGame.sol with solc, deploys it on a local
py-evm chain, and compares spin() / applyPicks() / applyGamble() against
~/workspace/chain-jam/starforge/simulator/parity.py for 15 fixed seeds
x artifacts {0x00, 0x07}.

Exit 0 = full parity. Any mismatch aborts with details.
"""
import os
import sys
import json

ROOT = os.path.expanduser("~/workspace/monad/starforge-erc8004")
CHAIN = os.path.expanduser("~/workspace/chain-jam/starforge")
sys.path.insert(0, os.path.join(CHAIN, "simulator"))

import parity  # noqa: E402 — reference simulator
import solcx  # noqa: E402
from eth_hash.auto import keccak  # noqa: E402
from web3 import Web3  # noqa: E402
from web3.providers.eth_tester import EthereumTesterProvider  # noqa: E402

solcx.install_solc("0.8.28")
solcx.set_solc_version("0.8.28")

# ---------- compile ----------
src = os.path.join(ROOT, "contracts", "StarforgeGame.sol")
compiled = solcx.compile_files(
    [src],
    output_values=["abi", "bin"],
    solc_version="0.8.28",
    allow_paths=os.path.join(ROOT, "contracts"),
)
cid, cdef = next(iter(compiled.items()))

# ---------- local chain ----------
w3 = Web3(EthereumTesterProvider())
acct = w3.eth.accounts[0]
game = w3.eth.contract(abi=cdef["abi"], bytecode=cdef["bin"])
txh = game.constructor().transact({"from": acct})
game = w3.eth.contract(address=w3.eth.get_transaction_receipt(txh)["contractAddress"], abi=cdef["abi"])

# ---------- 15 fixed seeds ----------
SEEDS = [keccak(f"starforge-parity-{i}".encode()).hex() for i in range(1, 16)]
ARTIFACT_SETS = [0x00, 0x07]
GAMBLE_SEED = keccak(b"starforge-gamble").hex()

failures = []
checks = 0


def check(name, a, b):
    global checks
    checks += 1
    if a != b:
        failures.append(f"{name}: contract={a} python={b}")


for seed in SEEDS:
    for arts in ARTIFACT_SETS:
        seed_b = bytes.fromhex(seed)
        py = parity.run_spin(seed, arts)
        res = game.functions.spin(seed_b, arts).call({"from": acct})
        # SpinResult: (stage, gridWinBps, artifacts, prizes, grids, stepWins, stepPats, stepCount, picksBps, picks, gambleWin, totalBps)
        stage, gridWinBps, _a, prizes, grids, stepWins, stepPats, stepCount, _pb, _p, _gw, totalBps = res
        label = f"seed={seed[:8]} arts={arts:#04x}"
        check(f"{label} stage", stage, 1 if py["stars"] >= 4 else 0)
        check(f"{label} gridWinBps", gridWinBps, py["grid_win_bps"])
        check(f"{label} stepCount", stepCount, py["step_count"])
        check(f"{label} stepWins", list(stepWins)[:stepCount], py["step_wins_bps"])
        check(f"{label} stepPats", list(stepPats)[:stepCount], py["step_pats"])
        exp_grids = b"".join(bytes(g) for g in py["grids"])
        check(f"{label} grids", bytes(grids), exp_grids)
        check(f"{label} prizes", list(prizes), py["prizes"])
        check(f"{label} totalBps(nosn)", totalBps, py["grid_win_bps"])

        # ---- picks parity (supernova only) ----
        if py["stars"] >= 4:
            picks = [0, 1, 2, 3, 4]
            res2 = game.functions.applyPicks(
                (
                    stage, gridWinBps, arts, list(prizes), bytes(grids),
                    list(stepWins), list(stepPats), stepCount,
                    0, [0, 0, 0, 0, 0], False, 0,
                ),
                picks, False,
            ).call({"from": acct})
            _s2, _g2, _a2, _pr2, _gr2, _sw2, _sp2, _sc2, picksBps, _p2, _gw2, total2 = res2
            exp_picks = sum(py["prizes"][p] for p in picks)
            if arts & 0x04:  # temple +10%
                exp_picks = exp_picks * 11 // 10
            check(f"{label} picksBps", picksBps, exp_picks)
            check(f"{label} totalBps(picks)", total2, py["grid_win_bps"] + exp_picks)

            # ---- gamble parity ----
            res_g = game.functions.applyPicks(
                (
                    stage, gridWinBps, arts, list(prizes), bytes(grids),
                    list(stepWins), list(stepPats), stepCount,
                    0, [0, 0, 0, 0, 0], False, 0,
                ),
                picks, True,
            ).call({"from": acct})
            s_g = res_g[0]
            check(f"{label} gamble stage", s_g, 2)
            res3 = game.functions.applyGamble(res_g, bytes.fromhex(GAMBLE_SEED)).call({"from": acct})
            _s3, _g3, _a3, _pr3, _gr3, _sw3, _sp3, _sc3, _pb3, _p3, gw3, total3 = res3
            exp_win = (bytes.fromhex(GAMBLE_SEED)[0] % 2) == 0
            exp_total3 = py["grid_win_bps"] + (exp_picks * 2 if exp_win else 0)
            check(f"{label} gambleWin", gw3, exp_win)
            check(f"{label} totalBps(gamble)", total3, exp_total3)

print(f"checks={checks} failures={len(failures)}")
for f in failures:
    print("FAIL:", f)
sys.exit(1 if failures else 0)
