#!/usr/bin/env python3
"""cell_receipts.py — WORLD seeded-counts witness + micromoth_emit v1.

Implements the "Smallest first build" clauses of docs/CELL-MAPPING.md
against the import baseline (micromoth.py):

- WORLD: the adopted "predict what happens next" op. Counts live in a
  WORLD witness cell {op: WORLD, args: {seed, shots, histogram}} — a
  named prediction, not a VIEW purity violation (the determinism hole:
  simulate(get='counts'|'memory') reads the unseeded module-global
  random). The seed is part of the cell's identity: two cells differing
  only in seed are different predictions, and both may be kept.
  WORLD refuses an unseeded call (ValueError) — unseeded counts stay
  the NAMED hole, never laundered into a receipt.
- micromoth_emit v1 (the git-agent quilt_emit analog, CELL-MAPPING.md):
  one JSONL ledger per run — LINK boundary, BIND the program cell
  (payload sha256-pinned, never inlined as a loose claim), TICK the
  gate chain moment by moment with per-TICK state hashes (verbatim
  kernels via state_witness), PROOF the final state, WORLD(seed, shots)
  the histogram. Verify by replay, not by trust; tamper is named.
- FORGET (CELL-MAPPING.md adopted opcode, the erasure unit): shot-level
  collapse EFFECT cells are journaled per shot after the WORLD witness;
  forget() exercises the "right to be erased" by REPLACING a named shot's
  EFFECT cell with a FORGET cell in place. The chain continues (every
  downstream id moves — the tamper-evidence property working FOR
  erasure: the erasure event is itself on-chain, never silent), the
  FORGET cell's args carry the erased cell's original id + reason so an
  auditor holding an unforgotten copy can diff exactly what went away,
  and the WORLD histogram (aggregate counts) is retained per the design
  ("counts may be retained while individual collapse records are
  FORGET-table").

Cell algebra (canonical source: SuperInstance/AI-Writings algebra.md):
five opcodes BIND / LINK / EFFECT / VIEW / TICK (+ adopted WORLD, PROOF),
fnv1a-64 over the canonical cell encoding, genesis prev = 0x0000000000000000.

Honest limits (kept from CELL-MAPPING.md):
- sugar ops never reach a ledger (state_witness refuses them).
- noise_model is out of scope here; WORLD pins the raw seeded sample.
- the ledger is cheap, the VIEW is not; PROOF witnesses are the
  mitigation, not a license to simulate big.

Run: python3 tools/cell_receipts.py   (self-check: Bell emit + verify)
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit, simulate  # noqa: E402  (baseline authority)

# collapse_ledger.py owns the canonical cell encoding + fnv1a-64 + the
# seed-plumbing precedent; state_witness.py owns the verbatim kernels.
sys.path.insert(0, str(LAB / "tools"))
from collapse_ledger import GENESIS, SUGAR, _baseline_version, _canon, _cell, _gate_args  # noqa: E402
import state_witness  # noqa: E402

DIALECT = "micro-moth/cell-receipts v1"


def _canon_statevector_pairs():
    """state_witness.PRECISION is the declared amplitude precision."""
    return state_witness.PRECISION


def seeded_counts(qc: QuantumCircuit, shots: int, seed: int) -> dict:
    """WORLD entrypoint: the only public sampling op the WORLD witness
    ever needs (CELL-MAPPING.md smallest-build step 1).

    Seeds the module-global RNG (the documented plumbing — simulate()
    accepts no seed argument on the import baseline), samples counts,
    restores the caller's RNG state. Sealed-only by construction: an
    unseeded prediction is refused, not faked.
    """
    if seed is None:
        raise ValueError(
            "WORLD refuses unseeded sampling: unseeded counts are the "
            "named determinism hole (CELL-MAPPING.md), never a receipt")
    if isinstance(seed, float) or (isinstance(seed, int) and seed < 0):
        raise ValueError("seed must be a non-negative int")
    if not isinstance(shots, int) or shots <= 0:
        raise ValueError("shots must be a positive int")
    state = random.getstate()
    try:
        random.seed(seed)
        counts = simulate(qc, shots=shots, get="counts")
    finally:
        random.setstate(state)
    histogram = {bit: int(n) for bit, n in counts.items()}
    return {"histogram": histogram, "seed": seed, "shots": shots}


def _program(qc: QuantumCircuit) -> list:
    prog = [_gate_args(g) for g in qc.data]
    for g in prog:
        if g.get("op") in SUGAR:
            raise ValueError("sugar op %r never ledgers (CELL-MAPPING.md)" % g["op"])
    return prog


def emit(qc: QuantumCircuit, shots: int = 256, seed: int = 42,
         proof_at=-1, name: str = "circuit") -> dict:
    """micromoth_emit v1: BIND -> TICK* -> PROOF(final) -> WORLD, one chain.

    proof_at follows state_witness.tick_witnesses (-1 = last moment).
    The WORLD cell closes the chain: its args carry seed + shots + the
    histogram, so its id moves when the prediction moves.
    """
    prog = _program(qc)
    link = _cell("LINK", GENESIS, {
        "circuit": "micro-moth:%s" % _baseline_version(),
        "num_qubits": qc.num_qubits,
        "num_clbits": qc.num_clbits,
        "shots_plan": shots,
        "emitter": "micromoth_emit v1",
    })
    bind = _cell("BIND", link["id"], {
        "kind": "qc-program",
        "name": name,
        "num_qubits": qc.num_qubits,
        "num_clbits": qc.num_clbits,
        "program": prog,
        "program_sha256": hashlib.sha256(_canon(prog).encode()).hexdigest(),
    })
    # TICK* + PROOF via the verbatim-kernel witness; strip its own LINK
    # and re-chain onto our BIND (welding pattern: witness_collapse_seam).
    w = state_witness.tick_witnesses(qc, proof_at=proof_at)
    welded = []
    prev = bind["id"]
    for c in w["cells"]:
        if c["op"] == "LINK":
            continue
        c = _cell(c["op"], prev, c["args"])
        welded.append(c)
        prev = c["id"]
    world_args = seeded_counts(qc, shots, seed)
    world = _cell("WORLD", prev, world_args)
    cells = [link, bind] + welded + [world]
    prev = world["id"]
    # Shot-level collapse EFFECT cells (FORGET's erasure unit,
    # CELL-MAPPING.md): one EFFECT per shot, outcomes from the seeded
    # memory sample — same seed, so replay re-derives them exactly.
    for shot, outcome in enumerate(_shot_outcomes(qc, shots, seed)):
        c = _cell("EFFECT", prev, {
            "kind": "collapse", "shot": shot, "outcome": outcome, "seed": seed,
        })
        cells.append(c)
        prev = c["id"]
    return {
        "dialect": DIALECT,
        "micromoth_version": _baseline_version(),
        "name": name,
        "depth": w["depth"],
        "shots": shots,
        "seed": seed,
        "histogram": world_args["histogram"],
        "cells": cells,
    }


def _shot_outcomes(qc: QuantumCircuit, shots: int, seed: int) -> list:
    """Seeded per-shot memory sample — the collapse EFFECT payloads.
    Same seed-plumbing contract as seeded_counts: restore caller RNG."""
    state = random.getstate()
    try:
        random.seed(seed)
        memory = simulate(qc, shots=shots, get="memory")
    finally:
        random.setstate(state)
    return [str(bit) for bit in memory]


def forget(receipt: dict, shots, reason: str) -> dict:
    """Exercise the right to be erased (CELL-MAPPING.md FORGET clause).

    Replaces each named shot's collapse EFFECT cell with a FORGET cell
    IN PLACE: same chain position, args carry {shot, reason,
    erased_id} — the erased cell's original id, so erasure is receipted
    and diffable against any unforgotten copy. Refused, not faked:
    unknown shot, already-forgotten shot, empty reason, or a shot with
    no EFFECT cell (nothing to erase). The WORLD histogram (aggregate
    counts) is retained per design; verify() still passes on the
    result — nothing was silently changed, the erasure is ON the chain.
    """
    if not reason or not reason.strip():
        raise ValueError("FORGET refuses an empty reason: erasure must say why")
    if isinstance(shots, int):
        shots = [shots]
    shots = list(shots)
    by_shot = {}
    for c in receipt["cells"]:
        if c["op"] == "EFFECT" and c["args"].get("kind") == "collapse":
            by_shot[c["args"]["shot"]] = c
        if c["op"] == "FORGET":
            by_shot[c["args"]["shot"]] = None  # already erased
    cells = []
    forgotten = set()
    prev = None  # None until the first erasure; then the re-derive cursor
    for orig in receipt["cells"]:
        target = (orig["op"] == "EFFECT"
                  and orig["args"].get("kind") == "collapse"
                  and orig["args"]["shot"] in shots)
        if target:
            shot = orig["args"]["shot"]
            if shot in forgotten:
                raise ValueError("shot %r appears twice in ledger" % shot)
            forgotten.add(shot)
            # erased_id = the id this cell carried in the INPUT receipt,
            # so an auditor diffs against the ledger as handed over; the
            # chain position follows the re-derive cursor when earlier
            # erasures already moved the chain
            f = _cell("FORGET", prev if prev is not None else orig["prev"], {
                "shot": shot,
                "reason": reason.strip(),
                "erased_id": orig["id"],
                "erased_kind": "collapse",
            })
            cells.append(f)
            prev = f["id"]
            continue
        # non-target: semantics byte-identical; id re-derived iff it sits
        # downstream of an erasure (tamper-evidence working FOR erasure)
        c = _cell(orig["op"], prev, orig["args"]) if prev is not None else orig
        cells.append(c)
        if prev is not None:
            prev = c["id"]
    for shot in shots:
        if shot not in forgotten:
            if shot in by_shot and by_shot[shot] is None:
                raise ValueError("shot %r already forgotten" % shot)
            raise ValueError("shot %r has no collapse EFFECT cell to erase" % shot)
    out = dict(receipt)
    out["cells"] = cells
    out["forgotten_shots"] = sorted(
        set(receipt.get("forgotten_shots", [])) | set(forgotten))
    return out


def verify(receipt: dict, qc: QuantumCircuit = None) -> dict:
    """Re-derive every cell id; re-run the prediction; compare. Tamper
    is named; never fake green."""
    cells = receipt["cells"]
    prev = GENESIS
    for i, c in enumerate(cells):
        body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
        want = "0x%016x" % state_witness.fnv1a64(_canon(body))
        if c["op"] == "FORGET":
            # Erasure is receipted, not silent: a FORGET cell must name
            # the shot, why, and the erased cell's original id.
            for k in ("shot", "reason", "erased_id", "erased_kind"):
                if k not in c["args"]:
                    return {"ok": False, "why": "forget_args_incomplete@%d" % i}
            if not str(c["args"]["reason"]).strip():
                return {"ok": False, "why": "forget_reason_empty@%d" % i}
            if c["args"].get("erased_kind") != "collapse":
                return {"ok": False, "why": "forget_target_not_collapse@%d" % i}
        if c["op"] == "WORLD":
            h = c["args"]["histogram"]
            if sum(h.values()) != c["args"]["shots"]:
                return {"ok": False, "why": "world_histogram_sums_wrong@%d" % i}
        if c["id"] != want:
            return {"ok": False, "why": "id_mismatch@%d" % i}
        if c["prev"] != prev:
            return {"ok": False, "why": "chain_break@%d" % i}
        prev = c["id"]
    if not any(c["op"] == "WORLD" for c in cells):
        return {"ok": False, "why": "world_absent"}
    if not any(c["op"] == "BIND" for c in cells):
        return {"ok": False, "why": "bind_absent"}
    if qc is not None:
        world = [c for c in cells if c["op"] == "WORLD"][-1]
        rerun = seeded_counts(qc, world["args"]["shots"], world["args"]["seed"])
        if rerun["histogram"] != world["args"]["histogram"]:
            return {"ok": False, "why": "world_divergence"}
        ticks = [c for c in cells if c["op"] == "TICK"]
        w = state_witness.tick_witnesses(qc, proof_at=-1)
        rticks = [c for c in w["cells"] if c["op"] == "TICK"]
        if [t["args"]["state_hash"] for t in ticks] != [t["args"]["state_hash"] for t in rticks]:
            return {"ok": False, "why": "tick_state_divergence"}
    return {"ok": True, "why": "ok"}


def _selfcheck() -> None:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    r = emit(qc, shots=256, seed=42, name="bell")
    v = verify(r, qc)
    print("verify:", v)
    r2 = forget(r, [0, 3], "demo erasure (self-check)")
    print("verify after forget:", verify(r2, qc))
    for c in r2["cells"]:
        print(json.dumps(c, sort_keys=True))


if __name__ == "__main__":
    _selfcheck()
