#!/usr/bin/env python3
"""witness_collapse_seam.py — close a TICK at the collapse EFFECT boundary.

The witness lane (state_witness.py) mints TICK cells over unitary
moments and stops where measurement begins being interesting; the
collapse lane (collapse_ledger.py) mints seeded EFFECT cells for
measurement outcomes but BINDs only gate records — the collapse chain
never commits to the pre-collapse state. This seam is the honest weld:

    LINK -> TICK* (witnessed moments) [-> PROOF] -> SEAM -> EFFECT*

The SEAM cell's prev is the last witness cell's id, so the collapse
outcomes are hash-chained to the witnessed boundary state — tamper
with either side and the chain names it. SEAM args pin the boundary
state hash, the measurement record set, shots, and the seed (the seed
IS the EFFECT parameter, as in collapse_ledger); outcomes are sampled
once, seeded, and replayed by verify() — never trusted.

Honest limits (kept, documented):
- noise_model is NOT a seam v1 parameter: the seam composes two
  verifiers and refuses silent parameter surfaces; ask collapse_ledger
  directly if you need noise.
- circuits with no measurement ops are refused: plain tick_witnesses
  already covers them honestly; a seam with nothing to collapse would
  be ceremony.
- seed must be a non-negative int: an unsealed seam would launder
  EFFECT/UNSEALED behind a witnessed boundary. Refused.
- measurement ops remain records, not moments (CELL-MAPPING.md); the
  boundary state is the state AFTER the last unitary moment, which is
  the state collapse_ledger samples from.

Run: python3 tools/witness_collapse_seam.py   (self-check, prints a receipt)
"""

from __future__ import annotations

import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit  # noqa: E402  (baseline authority)

sys.path.insert(0, str(LAB / "tools"))
# Same-package private imports, the established pattern (state_witness
# imports collapse_ledger's cell encoder; the seam composes both lanes).
from collapse_ledger import _baseline_version, _canon, _cell, _gate_args, _sample_seeded  # noqa: E402
from state_witness import PRECISION, tick_witnesses, verify as _verify_witness  # noqa: E402

DIALECT = "micro-moth/witness-collapse-seam v1"


def seam_receipt(qc: QuantumCircuit, shots: int, seed: int,
                 proof_at=None, precision: int = PRECISION) -> dict:
    """Mint the welded witness+collapse chain. See module docstring."""
    if seed is None or isinstance(seed, float) or \
            (isinstance(seed, int) and seed < 0):
        raise ValueError(
            "seam v1 requires a sealed collapse (seed: non-negative int); "
            "EFFECT/UNSEALED must not hide behind a witnessed boundary")
    ms = [g for g in qc.data if g[0] == "m"]
    if not ms:
        raise ValueError(
            "circuit has no measurement ops — tick_witnesses covers it "
            "honestly; a seam with nothing to collapse is ceremony")
    w = tick_witnesses(qc, proof_at=proof_at, precision=precision)
    outcomes = _sample_seeded(qc, shots, seed, [])
    seam = _cell("SEAM", w["cells"][-1]["id"], {
        "boundary_state_hash": w["final_state_hash"],
        "measurements": [_gate_args(g) for g in ms],
        "shots": shots,
        "seed": seed,
        "collapse_dialect": "micro-moth/collapse-ledger v1",
    })
    cells = list(w["cells"]) + [seam]
    prev = seam["id"]
    for i, out in enumerate(outcomes):
        c = _cell("EFFECT", prev,
                  {"kind": "collapse", "shot": i, "outcome": out, "seed": seed})
        cells.append(c)
        prev = c["id"]
    return {
        "dialect": DIALECT,
        "witness_dialect": w["dialect"],
        "collapse_dialect": "micro-moth/collapse-ledger v1",
        "micromoth_version": _baseline_version(),
        "precision": precision,
        "shots": shots,
        "outcomes": outcomes,
        "boundary_state_hash": w["final_state_hash"],
        "cells": cells,
    }


def verify(receipt: dict, qc: QuantumCircuit = None) -> dict:
    """Chain integrity + witness replay + seeded collapse re-sample.

    Tamper -> named failure, never fake green."""
    cells = receipt["cells"]
    from collapse_ledger import GENESIS, fnv1a64  # local: keeps top import small
    prev = GENESIS
    seams = []
    for i, c in enumerate(cells):
        body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
        want = "0x%016x" % fnv1a64(_canon(body))
        if c["id"] != want:
            return {"ok": False, "why": "id_mismatch@%d" % i}
        if c["prev"] != prev:
            return {"ok": False, "why": "chain_break@%d" % i}
        prev = c["id"]
        if c["op"] == "SEAM":
            seams.append((i, c))
    if len(seams) != 1:
        return {"ok": False, "why": "seam_count_%d" % len(seams)}
    si, seam = seams[0]
    if not any(c["op"] == "EFFECT" for c in cells[si + 1:]):
        return {"ok": False, "why": "seam_without_effect"}
    witness_cells = cells[:si]
    if witness_cells[-1]["id"] != seam["prev"]:
        return {"ok": False, "why": "seam_not_welded"}
    if qc is not None:
        w = {"cells": witness_cells, "precision": receipt.get("precision", PRECISION)}
        wr = _verify_witness(w, qc)
        if not wr["ok"]:
            return {"ok": False, "why": "witness_" + wr["why"]}
        ticks = [c for c in witness_cells if c["op"] == "TICK"]
        if seam["args"]["boundary_state_hash"] != ticks[-1]["args"]["state_hash"]:
            return {"ok": False, "why": "boundary_state_mismatch"}
        ms = [g for g in qc.data if g[0] == "m"]
        if seam["args"]["measurements"] != [_gate_args(g) for g in ms]:
            return {"ok": False, "why": "measurement_record_divergence"}
        rerun = _sample_seeded(qc, seam["args"]["shots"], seam["args"]["seed"], [])
        effects = [c for c in cells[si + 1:] if c["op"] == "EFFECT"]
        if len(effects) != len(rerun):
            return {"ok": False, "why": "effect_count_divergence"}
        for c, out in zip(effects, rerun):
            if c["args"]["outcome"] != out:
                return {"ok": False,
                        "why": "outcome_divergence@shot%d" % c["args"]["shot"]}
    return {"ok": True, "why": "ok"}


if __name__ == "__main__":
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    r = seam_receipt(qc, 16, seed=42, proof_at=-1)
    print(_canon({"dialect": r["dialect"], "cells": len(r["cells"]),
                  "boundary_state_hash": r["boundary_state_hash"],
                  "verify": verify(r, qc)}))
