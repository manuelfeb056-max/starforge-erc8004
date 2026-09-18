"""Shared solc build helper: compile_standard with via-IR + optimizer.

Needed because AgentReputation's giveFeedback call (8 args, 4 dynamic
strings) overflows the legacy codegen stack ("stack too deep").
via-IR is supported by solc 0.8.28 and used for both tests and deploys
so test bytecode == deploy bytecode.
"""
import os

import solcx

SOLC = "0.8.28"


def _ensure():
    solcx.install_solc(SOLC)
    solcx.set_solc_version(SOLC)


def compile_files_via_ir(files, allow_paths):
    """files: list of absolute .sol paths (entry points; the whole tree under
    allow_paths is included so relative imports resolve — standard JSON
    never reads from disk).
    Returns {contract_name: {"abi": abi, "bin": bytecode}} (same shape as
    solcx.compile_files output_values=["abi","bin"])."""
    _ensure()
    sources = {}
    for root, _, fs in os.walk(allow_paths):
        for f in fs:
            if f.endswith(".sol"):
                p = os.path.join(root, f)
                sources[os.path.relpath(p, allow_paths)] = {"content": open(p).read()}
    out = solcx.compile_standard(
        {
            "language": "Solidity",
            "sources": sources,
            "settings": {
                "viaIR": True,
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
            },
        },
        allow_paths=[allow_paths],
    )
    res = {}
    for contracts in out["contracts"].values():
        for name, c in contracts.items():
            res[name] = {"abi": c["abi"], "bin": c["evm"]["bytecode"]["object"]}
    return res


def compile_source_via_ir(source):
    """Compile a single source string. Returns {contract_name: {"abi","bin"}}."""
    _ensure()
    out = solcx.compile_standard(
        {
            "language": "Solidity",
            "sources": {"mock.sol": {"content": source}},
            "settings": {
                "viaIR": True,
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
            },
        },
    )
    res = {}
    for contracts in out["contracts"].values():
        for name, c in contracts.items():
            res[name] = {"abi": c["abi"], "bin": c["evm"]["bytecode"]["object"]}
    return res
