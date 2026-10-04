#!/usr/bin/env python3
"""Pins for tools/cell_receipts.py — WORLD seeded-counts witness + micromoth_emit v1.

FAIL-first contract: this module (and tools/cell_receipts.py) does not
exist on main — every pin here is RED on a pristine main checkout and
green only on the carrying branch. Run: python3 -m pytest tests/test_cell_receipts.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit  # noqa: E402

import cell_receipts  # noqa: E402
from collapse_ledger import GENESIS, _canon  # noqa: E402
import state_witness  # noqa: E402


def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def test_world_refuses_unseeded():
    # The determinism hole stays NAMED: unseeded counts are refused,
    # never laundered into a WORLD receipt (CELL-MAPPING.md).
    with pytest.raises(ValueError):
        cell_receipts.seeded_counts(bell(), 64, None)


def test_world_rejects_bad_seed_and_shots():
    with pytest.raises(ValueError):
        cell_receipts.seeded_counts(bell(), 64, -1)
    with pytest.raises(ValueError):
        cell_receipts.seeded_counts(bell(), 0, 42)


def test_seeded_counts_deterministic_and_sums():
    qc = bell()
    a = cell_receipts.seeded_counts(qc, 256, 42)
    b = cell_receipts.seeded_counts(qc, 256, 42)
    assert a == b  # byte-identical prediction at the same seed
    assert sum(a["histogram"].values()) == 256
    assert set(a["histogram"]) <= {"00", "01", "10", "11"}
    # caller's RNG state is restored (plumbing, not a side effect)
    random.seed(1234)
    before = random.getstate()
    cell_receipts.seeded_counts(qc, 8, 7)
    assert random.getstate() == before


def test_world_seed_is_cell_identity():
    # Two cells differing only in seed are different predictions; the
    # circuit chain (LINK/BIND/TICK/PROOF ids) is seed-independent.
    qc = bell()
    r1 = cell_receipts.emit(qc, shots=128, seed=1)
    r2 = cell_receipts.emit(qc, shots=128, seed=2)
    ops = lambda r, op: [c for c in r["cells"] if c["op"] == op]
    assert [c["id"] for c in ops(r1, "TICK")] == [c["id"] for c in ops(r2, "TICK")]
    assert ops(r1, "WORLD")[0]["id"] != ops(r2, "WORLD")[0]["id"]
    assert r1["histogram"] != r2["histogram"]  # different predictions differ


def test_emit_chain_derivable_and_genesis():
    r = cell_receipts.emit(bell(), shots=64, seed=42)
    cells = r["cells"]
    assert cells[0]["prev"] == GENESIS
    prev = GENESIS
    for i, c in enumerate(cells):
        body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
        want = "0x%016x" % state_witness.fnv1a64(_canon(body))
        assert c["id"] == want, "id re-derivation failed at cell %d" % i
        assert c["prev"] == prev, "chain break at cell %d" % i
        prev = c["id"]


def test_bind_pins_program_bytes():
    qc = bell()
    r = cell_receipts.emit(qc, shots=64, seed=42)
    bind = [c for c in r["cells"] if c["op"] == "BIND"][0]
    prog = bind["args"]["program"]
    assert prog == json.loads(_canon(prog))  # canonical encoding round-trips
    want = hashlib.sha256(_canon(prog).encode()).hexdigest()
    assert bind["args"]["program_sha256"] == want
    # program matches the executable chain, gate for gate
    assert [g["op"] for g in prog] == [g[0] for g in qc.data]


def test_tick_parity_with_state_witness():
    # TICK cells are welded from state_witness verbatim kernels: same
    # ids as a standalone tick_witnesses run (porting rule 8 parity).
    qc = bell()
    r = cell_receipts.emit(qc, shots=64, seed=42)
    w = state_witness.tick_witnesses(qc, proof_at=-1)
    a = [c["args"]["state_hash"] for c in r["cells"] if c["op"] == "TICK"]
    b = [c["args"]["state_hash"] for c in w["cells"] if c["op"] == "TICK"]
    assert a == b
    assert r["depth"] == w["depth"]


def test_verify_ok_and_tamper_named():
    qc = bell()
    r = cell_receipts.emit(qc, shots=256, seed=42)
    assert cell_receipts.verify(r, qc) == {"ok": True, "why": "ok"}
    # tamper the WORLD histogram -> id moves
    bad = json.loads(json.dumps(r))
    world = [c for c in bad["cells"] if c["op"] == "WORLD"][-1]
    key = sorted(world["args"]["histogram"])[0]
    world["args"]["histogram"][key] += 1
    v = cell_receipts.verify(bad, qc)
    assert not v["ok"] and v["why"].startswith("world_histogram_sums_wrong")
    # tamper a TICK state hash -> replay divergence is named (re-stitch
    # the whole tail so only the replay comparison can catch it)
    bad2 = json.loads(json.dumps(r))
    tick = [c for c in bad2["cells"] if c["op"] == "TICK"][0]
    tick["args"]["state_hash"] = "0xdeadbeefdeadbeef"
    idx = bad2["cells"].index(tick)
    prev = tick["prev"]
    for c in bad2["cells"][idx:]:
        c["prev"] = prev
        body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
        c["id"] = "0x%016x" % state_witness.fnv1a64(_canon(body))
        prev = c["id"]
    v2 = cell_receipts.verify(bad2, qc)
    assert not v2["ok"] and v2["why"] == "tick_state_divergence"


def test_world_histogram_sum_guard():
    # a histogram that does not sum to its shots is named, even if the
    # attacker re-derives the id (honesty guard before id check)
    r = cell_receipts.emit(bell(), shots=64, seed=42)
    bad = json.loads(json.dumps(r))
    world = [c for c in bad["cells"] if c["op"] == "WORLD"][-1]
    world["args"]["histogram"]["00"] += 1
    world["args"]["shots"] += 1  # sums again, but...
    v = cell_receipts.verify(bad)
    # id re-derivation still trips: the cell id covers args as minted
    assert not v["ok"]
