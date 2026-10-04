#!/usr/bin/env python3
"""Pins for tools/view_receipt.py — the VIEW clause of CELL-MAPPING.md.

"so 'we looked at counts' is itself receipted and re-derivable."

FAIL-first law: every source pin below is RED on a pristine checkout
without the tool (import dies — verified by fresh-audit on the base
branch), GREEN on the branch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit  # noqa: E402

import cell_receipts  # noqa: E402  (chain siblings; VIEW welds onto emit)
import state_witness  # noqa: E402
import view_receipt  # noqa: E402  (import dies on pristine main — FAIL-first)


def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def test_views_mint_and_verify_by_replay():
    qc = bell()
    for view, kw in (("counts", {"shots": 64, "seed": 42}),
                     ("statevector", {}),
                     ("probabilities_dict", {})):
        cell = view_receipt.view_cell(qc, view, **kw)
        assert cell["op"] == "VIEW"
        assert cell["args"]["view"] == view
        assert cell["args"]["num_qubits"] == 2
        v = view_receipt.verify_cell(cell, qc)
        assert v["ok"], v


def test_counts_histogram_is_the_live_seeded_prediction():
    qc = bell()
    cell = view_receipt.view_cell(qc, "counts", shots=64, seed=42)
    # same prediction cell_receipts.WORLD seals — one sampling doctrine
    assert cell["args"]["histogram"] == cell_receipts.seeded_counts(qc, 64, 42)["histogram"]
    assert sum(cell["args"]["histogram"].values()) == 64


def test_unseeded_counts_refused_not_faked():
    qc = bell()
    for bad in (dict(shots=None, seed=42), dict(shots=64, seed=None)):
        try:
            view_receipt.view_cell(qc, "counts", **bad)
        except ValueError:
            pass
        else:
            raise AssertionError("unseeded counts laundered into a receipt: %r" % bad)
    # deterministic views need no seed: the hole doctrine stays scoped
    # to sampling, not stretched into a ceremony
    assert view_receipt.verify_cell(
        view_receipt.view_cell(qc, "statevector"), qc)["ok"]


def test_statevector_payload_digest_pinned_never_inlined():
    qc = bell()
    cell = view_receipt.view_cell(qc, "statevector")
    args = cell["args"]
    assert args["num_amplitudes"] == 4
    assert args["precision"] == state_witness.PRECISION
    assert len(args["state_sha256"]) == 64
    body = json.dumps(args)
    assert "0.7071" not in body  # no amplitude leaks into the ledger


def test_cell_id_covers_args_rewriting_view_is_named():
    qc = bell()
    cell = view_receipt.view_cell(qc, "probabilities_dict")
    bad = json.loads(json.dumps(cell))
    bad["args"]["view"] = "counts"  # rewrite which view was taken
    v = view_receipt.verify_cell(bad, qc)
    assert not v["ok"] and v["why"] == "id_mismatch"


def test_tampered_digest_named_on_replay():
    qc = bell()
    cell = view_receipt.view_cell(qc, "statevector")
    bad = json.loads(json.dumps(cell))
    bad["args"]["state_sha256"] = "0" * 64
    bad["id"] = cell["id"]  # lazy attacker: keep minted id
    v = view_receipt.verify_cell(bad, qc)
    assert not v["ok"] and v["why"] == "id_mismatch"
    # patient attacker re-derives the id — replay still names the lie
    import collapse_ledger
    body = {"op": "VIEW", "prev": bad["prev"], "args": bad["args"]}
    bad["id"] = "0x%016x" % state_witness.fnv1a64(collapse_ledger._canon(body))
    v = view_receipt.verify_cell(bad, qc)
    assert not v["ok"] and v["why"] == "state_digest_divergence"


def test_chain_welds_onto_emit_world():
    # VIEW records an observation over the SAME circuit the emit receipt
    # witnessed: it welds onto the emitted chain, prev = WORLD id
    qc = bell()
    receipt = cell_receipts.emit(qc, shots=32, seed=7)
    world = [c for c in receipt["cells"] if c["op"] == "WORLD"][-1]
    cell = view_receipt.view_cell(qc, "probabilities_dict", prev=world["id"])
    assert cell["prev"] == world["id"]
    v = view_receipt.verify_cell(cell, qc)
    assert v["ok"], v


def test_unknown_view_refused():
    qc = bell()
    try:
        view_receipt.view_cell(qc, "blobs")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown view minted — the observation unnamed")
    bad = view_receipt.view_cell(qc, "statevector")
    bad["args"]["view"] = "blobs"
    import collapse_ledger
    body = {"op": "VIEW", "prev": bad["prev"], "args": bad["args"]}
    bad["id"] = "0x%016x" % state_witness.fnv1a64(collapse_ledger._canon(body))
    v = view_receipt.verify_cell(bad, qc)
    assert not v["ok"] and v["why"] == "unknown_view"


def test_determinism_views_replay_byte_identical():
    qc = bell()
    a = view_receipt.view_cell(qc, "probabilities_dict")
    b = view_receipt.view_cell(qc, "probabilities_dict")
    assert a == b  # digest layer: re-mint is byte-identical, ids stable
