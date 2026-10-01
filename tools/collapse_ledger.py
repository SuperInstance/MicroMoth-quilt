#!/usr/bin/env python3
"""collapse_ledger.py — seed-plumbing wrapper so collapse receipts can mint SEALED.

Implements the "Collapse receipts, re-executable" contract of
docs/CELL-MAPPING.md against the import baseline (micromoth.py):

1. The ledger pins `seed` and `shots` as EFFECT parameters.
2. Re-running with the same circuit chain + same seed reproduces the
   same collapse EFFECT chain, byte for byte.
3. Honest limit preserved: simulate() takes NO seed argument today and
   reads the module-global `random`. The wrapper plumbs a seed through
   exactly that source (seed -> simulate -> restore state), records the
   plumbing as the EFFECT parameter, and refuses to call an unseeded
   run sealed. If a future micromoth.py accepts a seed directly, this
   wrapper must delegate to it (pin: test_plumbing_documented).

Cell algebra (canonical source: SuperInstance/AI-Writings algebra.md):
five opcodes BIND / LINK / EFFECT / VIEW / TICK, fnv1a-64 over the
canonical cell encoding, genesis prev = 0x0000000000000000.

Run: python3 tools/collapse_ledger.py   (self-check, prints a receipt)
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

import micromoth
from micromoth import QuantumCircuit, simulate


def _baseline_version() -> str:
    """Simulator version label for LINK boundary cells.

    micromoth.py exposes NO __version__ on the import baseline (the
    CELL-MAPPING design assumed one — corrected by this wrapper). We
    derive the label from the git baseline of micromoth.py instead, so
    a simulator upgrade still moves the boundary cell's id.
    """
    v = getattr(micromoth, "__version__", None)
    if v:
        return str(v)
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD", "--", "micromoth.py"],
            cwd=LAB, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        sha = ""
    return "baseline:%s" % (sha or "unknown")

GENESIS = "0x0000000000000000"

# sugar never ledgers (CELL-MAPPING.md): y/z/ry decompose at append time,
# so their presence in qc.data would mean a hand-built, unbaseline chain.
SUGAR = {"y", "z", "ry"}


def fnv1a64(s: str) -> int:
    """fnv1a-64 over utf-8, the fleet WAL convention."""
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _cell(op: str, prev: str, args: dict) -> dict:
    body = {"op": op, "prev": prev, "args": args}
    body["id"] = "0x%016x" % fnv1a64(_canon({"op": op, "prev": prev, "args": args}))
    return body


def _gate_args(gate) -> dict:
    op = gate[0]
    if op in SUGAR:
        raise ValueError(
            "sugar op %r must never reach a ledger (CELL-MAPPING.md) — "
            "decompose via QuantumCircuit methods before chaining" % op)
    if op == "init":
        sv = gate[1]
        # init payloads embed full statevectors: hash-pinned (sha256,
        # manifest pattern), never inlined into cells.
        payload = _canon(sv)
        return {"op": op, "state_sha256": hashlib.sha256(payload.encode()).hexdigest()}
    if op == "m":
        return {"op": op, "qubit": gate[1], "clbit": gate[2]}
    if op in ("rx", "rz"):
        return {"op": op, "theta": float(gate[1]), "qubit": gate[2]}
    if op in ("cx", "swap"):
        return {"op": op, "qubits": [gate[1], gate[2]]}
    if op == "crx":
        return {"op": op, "theta": float(gate[1]), "qubits": [gate[2], gate[3]]}
    # x, h
    return {"op": op, "qubit": gate[1]}


def circuit_cells(qc: QuantumCircuit, shots: int) -> list:
    """BIND chain for the gate list + one LINK boundary cell.

    First gate's prev is genesis; each later gate's prev is the
    preceding cell's id — the circuit IS a hash chain.
    """
    link = _cell("LINK", GENESIS, {
        "circuit": "micro-moth:%s" % _baseline_version(),
        "num_qubits": qc.num_qubits,
        "num_clbits": qc.num_clbits,
        "shots": shots,
    })
    cells = [link]
    prev = link["id"]
    for gate in qc.data:
        c = _cell("BIND", prev, _gate_args(gate))
        cells.append(c)
        prev = c["id"]
    return cells


def _sample_seeded(qc: QuantumCircuit, shots: int, seed: int, noise_model) -> list:
    """The seed plumbing: simulate() reads the module-global RNG, so we
    seed it, run, and restore — the seed IS the EFFECT parameter."""
    state = random.getstate()
    try:
        random.seed(seed)
        return simulate(qc, shots=shots, get="memory", noise_model=noise_model)
    finally:
        random.setstate(state)


def collapse_receipt(qc: QuantumCircuit, shots: int, seed, noise_model=None) -> dict:
    """Mint the collapse EFFECT chain.

    seed is an int -> SEALED receipt (re-executable). seed is None ->
    EFFECT/UNSEALED, honestly marked, never laundered into sealed.
    """
    if isinstance(seed, float) or (isinstance(seed, int) and seed < 0):
        raise ValueError("seed must be a non-negative int or None")
    # noise_model is an EFFECT parameter (CELL-MAPPING.md), not a silent
    # edit: normalize and pin it in the receipt so replay reproduces it.
    nm = None
    if noise_model:
        nm = ([float(noise_model)] * qc.num_qubits
              if isinstance(noise_model, float)
              else [float(p) for p in noise_model])
    cells = circuit_cells(qc, shots)
    prev = cells[-1]["id"]
    if seed is None:
        outcomes = simulate(qc, shots=shots, get="memory", noise_model=noise_model or [])
        sealed = False
        seed_args = None
    else:
        outcomes = _sample_seeded(qc, shots, seed, noise_model or [])
        sealed = True
        seed_args = seed
    for i, out in enumerate(outcomes):
        args = {"kind": "collapse", "shot": i, "outcome": out}
        if sealed:
            args["seed"] = seed_args
        c = _cell("EFFECT", prev, args)
        cells.append(c)
        prev = c["id"]
    return {
        "dialect": "micro-moth/collapse-ledger v1",
        "micromoth_version": _baseline_version(),
        "sealed": sealed,
        "status": "EFFECT/SEALED" if sealed else "EFFECT/UNSEALED",
        "shots": shots,
        "noise_model": nm,
        "outcomes": outcomes,
        "cells": cells,
    }


def verify(receipt: dict, qc: QuantumCircuit = None) -> dict:
    """Re-derive every cell id; if qc is given, re-execute and compare.

    Returns {"ok": bool, "why": str}. Tamper with any cell body or
    break the prev chain -> named failure. Never fake green.
    """
    cells = receipt["cells"]
    prev = GENESIS
    for i, c in enumerate(cells):
        body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
        want = "0x%016x" % fnv1a64(_canon(body))
        if c["id"] != want:
            return {"ok": False, "why": "id_mismatch@%d" % i}
        if c["prev"] != prev:
            return {"ok": False, "why": "chain_break@%d" % i}
        prev = c["id"]
    if qc is not None:
        if not receipt["sealed"]:
            return {"ok": False, "why": "unsealed_not_reexecutable"}
        rerun = collapse_receipt(qc, receipt["shots"],
                                 receipt["cells"][-1]["args"]["seed"],
                                 noise_model=receipt.get("noise_model"))
        if [c["id"] for c in rerun["cells"]] != [c["id"] for c in cells]:
            return {"ok": False, "why": "replay_divergence"}
    return {"ok": True, "why": "ok"}


if __name__ == "__main__":
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    r = collapse_receipt(qc, 16, seed=42)
    print(_canon({"sealed": r["sealed"], "status": r["status"],
                  "shots": r["shots"], "cells": len(r["cells"]),
                  "verify": verify(r, qc)}))
