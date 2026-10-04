#!/usr/bin/env python3
"""state_witness.py — TICK moments + PROOF statevector witness cells.

Implements the TICK and PROOF clauses of docs/CELL-MAPPING.md against
the import baseline (micromoth.py):

- TICK: partition the executable gate chain into qubit-disjoint layers
  (circuit moments); each layer closes with a TICK cell carrying the
  state hash at that moment. Depth = number of TICKs.
- PROOF: at a chosen TICK, a PROOF cell pins the statevector — not the
  amplitudes themselves (cost law: statevector is 2**n pairs) but the
  sha256 of the amplitude pairs rounded to a declared precision, the
  same hash-pinned-never-inlined convention as init payloads.

Gate arithmetic is a verbatim port of simulate()'s kernels
(superpose/turn/phaseturn with the r2 constant) in the reference
loop order (fleet porting rule 8: fp addition is not associative;
identical op sequence is the only honest parity claim). Per-layer
checkpoints are therefore bitwise-identical to simulate(get=
'statevector') on the same chain — pinned live in the test suite.

Honest limits (CELL-MAPPING.md, kept):
- sugar ops never reach a ledger (refused, as in collapse_ledger).
- measurement ops are records, not moments: 'm' gates shape sampling
  but touch no qubit unitarily, so they partition no TICK.
- verify() replays by recomputation, never by trust; tamper is named.

Run: python3 tools/state_witness.py   (self-check, prints a receipt)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit  # noqa: E402  (baseline authority)

# collapse_ledger.py owns the canonical cell encoding + fnv1a-64.
sys.path.insert(0, str(LAB / "tools"))
from collapse_ledger import GENESIS, SUGAR, _baseline_version, _canon, _cell  # noqa: E402

# simulate()'s own constant (micromoth.py) — the parity pin depends on it.
R2 = 0.70710678118

PRECISION = 12  # decimal places for amplitude rounding (declared in cells)


def _round_c(c, precision=PRECISION):
    return [round(float(c[0]), precision), round(float(c[1]), precision)]


def state_digest(sv, precision=PRECISION) -> str:
    """Canonical, declared-precision amplitude encoding — the hash input."""
    return _canon([_round_c(c, precision) for c in sv])


def fnv1a64(s: str) -> int:
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def state_hash(sv, precision=PRECISION) -> str:
    """fnv1a-64 over the canonical rounded encoding (WAL convention)."""
    return "0x%016x" % fnv1a64(state_digest(sv, precision))


def _superpose(x, y):
    return [R2 * (x[j] + y[j]) for j in range(2)], [R2 * (x[j] - y[j]) for j in range(2)]


def _turn(x, y, theta):
    theta = float(theta)
    from math import cos, sin
    return ([x[0] * cos(theta / 2) + y[1] * sin(theta / 2),
             x[1] * cos(theta / 2) - y[0] * sin(theta / 2)],
            [y[0] * cos(theta / 2) + x[1] * sin(theta / 2),
             y[1] * cos(theta / 2) - x[0] * sin(theta / 2)])


def _phaseturn(x, y, theta):
    theta = float(theta)
    from math import cos, sin
    return ([x[0] * cos(theta / 2) - x[1] * sin(-theta / 2),
             x[1] * cos(theta / 2) + x[0] * sin(-theta / 2)],
            [y[0] * cos(theta / 2) - y[1] * sin(+theta / 2),
             y[1] * cos(theta / 2) + y[0] * sin(+theta / 2)])


def _qubits_of(gate) -> set:
    op = gate[0]
    if op == "init":
        return set()  # handled as its own layer seed, claims no qubit
    if op == "m":
        return set()  # record, not a moment (CELL-MAPPING.md)
    if op in ("x", "h", "rx", "rz"):
        return {gate[-1]}
    if op in ("cx", "swap"):
        return {gate[1], gate[2]}
    if op == "crx":
        return {gate[2], gate[3]}
    raise ValueError("unknown executable op %r" % op)


def layers(qc: QuantumCircuit) -> list:
    """Partition qc.data into qubit-disjoint moments (greedy, in order).

    Measurement ops are records, not moments (CELL-MAPPING.md), and are
    excluded from partitioning.
    """
    groups, cur, used = [], [], set()
    for gate in qc.data:
        if gate[0] in SUGAR:
            raise ValueError(
                "sugar op %r must never reach a ledger (CELL-MAPPING.md)" % gate[0])
        if gate[0] == "m":
            continue
        qs = _qubits_of(gate)
        if qs & used:
            groups.append(cur)
            cur, used = [], set()
        cur.append(gate)
        used |= qs
    if cur:
        groups.append(cur)
    return groups


def _apply(k, gate, n: int) -> None:
    """One gate, simulate()'s exact kernels and loop bounds (port rule 8)."""
    if gate[0] == "init":
        payload = gate[1]
        if isinstance(payload[0], list):
            k[:] = [list(e) for e in payload]
        else:
            k[:] = [[e, 0] for e in payload]
        return
    if gate[0] in ("x", "h", "rx", "rz"):
        j = gate[-1]
        for i0 in range(2 ** j):
            for i1 in range(2 ** (n - j - 1)):
                b0 = i0 + 2 ** (j + 1) * i1
                b1 = b0 + 2 ** j
                if gate[0] == "x":
                    k[b0], k[b1] = k[b1], k[b0]
                elif gate[0] == "h":
                    k[b0], k[b1] = _superpose(k[b0], k[b1])
                elif gate[0] == "rx":
                    k[b0], k[b1] = _turn(k[b0], k[b1], gate[1])
                else:
                    k[b0], k[b1] = _phaseturn(k[b0], k[b1], gate[1])
        return
    if gate[0] in ("cx", "crx", "swap"):
        if gate[0] in ("cx", "swap"):
            s, t = gate[1], gate[2]
            theta = None
        else:
            theta = gate[1]
            s, t = gate[2], gate[3]
        l, h = sorted([s, t])
        for i0 in range(2 ** l):
            for i1 in range(2 ** (h - l - 1)):
                for i2 in range(2 ** (n - h - 1)):
                    b00 = i0 + 2 ** (l + 1) * i1 + 2 ** (h + 1) * i2
                    b01 = b00 + 2 ** t
                    b10 = b00 + 2 ** s
                    b11 = b10 + 2 ** t
                    if gate[0] == "cx":
                        k[b10], k[b11] = k[b11], k[b10]
                    elif gate[0] == "crx":
                        k[b10], k[b11] = _turn(k[b10], k[b11], theta)
                    else:
                        k[b01], k[b10] = k[b10], k[b01]
        return
    raise ValueError("unknown executable op %r" % gate[0])


def tick_witnesses(qc: QuantumCircuit, proof_at=None, precision=PRECISION) -> dict:
    """Execute the circuit moment by moment, minting TICK cells; at
    proof_at (a TICK index, or -1 for the last), mint a PROOF cell
    pinning the rounded statevector's sha256. Verify by replay."""
    if proof_at is not None and proof_at < -1:
        raise ValueError("proof_at must be a TICK index, -1 (last), or None")
    moms = layers(qc)
    link = _cell("LINK", GENESIS, {
        "circuit": "micro-moth:%s" % _baseline_version(),
        "num_qubits": qc.num_qubits,
        "witness": "tick-proof v1",
        "precision": precision,
    })
    cells = [link]
    prev = link["id"]
    k = [[0, 0] for _ in range(2 ** qc.num_qubits)]
    k[0] = [1.0, 0.0]
    n_ticks = 0
    proof_done = False
    for mi, moment in enumerate(moms):
        for gate in moment:
            _apply(k, gate, qc.num_qubits)
        n_ticks += 1
        sh = state_hash(k, precision)
        c = _cell("TICK", prev, {"ticker": n_ticks, "moment": mi,
                                 "qubits": sorted(set().union(*[_qubits_of(g) for g in moment])),
                                 "gates": len(moment), "state_hash": sh})
        cells.append(c)
        prev = c["id"]
        target = (len(moms) - 1) if proof_at == -1 else proof_at
        if proof_at is not None and not proof_done and mi == target:
            digest = hashlib.sha256(state_digest(k, precision).encode()).hexdigest()
            p = _cell("PROOF", prev, {"tick": n_ticks, "precision": precision,
                                      "state_sha256": digest,
                                      "encoding": "canonical-rounded-pairs"})
            cells.append(p)
            prev = p["id"]
            proof_done = True
    return {
        "dialect": "micro-moth/state-witness v1",
        "micromoth_version": _baseline_version(),
        "precision": precision,
        "depth": n_ticks,
        "proof": proof_done,
        "cells": cells,
        "final_state_hash": ([c for c in cells if c["op"] == "TICK"][-1]["args"]["state_hash"]
                             if any(c["op"] == "TICK" for c in cells) else None),
    }


def verify(receipt: dict, qc: QuantumCircuit = None) -> dict:
    """Re-derive every cell id; recompute the witness and compare.
    Tamper -> named failure. Never fake green."""
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
        proof_at = None
        for c in cells:
            if c["op"] == "PROOF":
                proof_at = c["args"]["tick"] - 1
        rerun = tick_witnesses(qc, proof_at=proof_at, precision=receipt.get("precision", PRECISION))
        if [c["id"] for c in rerun["cells"]] != [c["id"] for c in cells]:
            return {"ok": False, "why": "replay_divergence"}
        ticks = [c for c in cells if c["op"] == "TICK"]
        rticks = [c for c in rerun["cells"] if c["op"] == "TICK"]
        for a, b in zip(ticks, rticks):
            if a["args"]["state_hash"] != b["args"]["state_hash"]:
                return {"ok": False, "why": "state_divergence@tick%d" % a["args"]["ticker"]}
    return {"ok": True, "why": "ok"}


if __name__ == "__main__":
    qc = QuantumCircuit(4, 0)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    r = tick_witnesses(qc, proof_at=-1)
    print(_canon({"proof": r["proof"], "depth": r["depth"],
                  "cells": len(r["cells"]),
                  "final_state_hash": r["final_state_hash"],
                  "verify": verify(r, qc)}))
