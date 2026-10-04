#!/usr/bin/env python3
"""Pins for the emit JSONL artifact driver (tools/cell_receipts.py).

FAIL-first contract: write_artifact / read_artifact do not exist on the
carrying branch's base — every pin here is RED there and on pristine
main. Run: python3 -m pytest tests/test_emit_artifact.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit  # noqa: E402

import cell_receipts  # noqa: E402


def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


@pytest.fixture()
def receipt():
    return cell_receipts.emit(bell(), shots=64, seed=7, name="bell")


def test_driver_exists_fail_first():
    # RED anywhere the driver is absent (pristine main included).
    assert hasattr(cell_receipts, "write_artifact")
    assert hasattr(cell_receipts, "read_artifact")
    assert cell_receipts.ARTIFACT_KIND == "micromoth-emit-artifact"


def test_round_trip_byte_identical(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    back = cell_receipts.read_artifact(p)
    assert back["cells"] == receipt["cells"]
    for k in ("dialect", "micromoth_version", "name", "seed",
              "shots", "histogram", "depth"):
        assert back[k] == receipt[k]


def test_file_order_is_chain_order(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    lines = p.read_text().splitlines()
    # swap two adjacent cell lines -> the chain must break by name
    lines[3], lines[4] = lines[4], lines[3]
    p.write_text("\n".join(lines) + "\n")
    back = cell_receipts.read_artifact(p)  # parse OK; the lie is on-chain
    v = cell_receipts.verify(back)
    assert not v["ok"]
    assert "chain_break" in v["why"] or "id_mismatch" in v["why"]


def test_tampered_cell_args_named(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    lines = p.read_text().splitlines()
    cell = json.loads(lines[2])
    cell["args"] = dict(cell["args"])
    for k, val in cell["args"].items():
        if isinstance(val, int):
            cell["args"][k] = val + 1
            break
    lines[2] = json.dumps(cell, sort_keys=True)
    p.write_text("\n".join(lines) + "\n")
    back = cell_receipts.read_artifact(p)
    v = cell_receipts.verify(back)
    assert not v["ok"]
    assert "id_mismatch" in v["why"]


def test_dropped_line_refused(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    lines = p.read_text().splitlines()
    p.write_text("\n".join(lines[:-1]) + "\n")  # drop last cell
    with pytest.raises(ValueError, match="counts"):
        cell_receipts.read_artifact(p)


def test_trailing_garbage_refused(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    with p.open("a") as f:
        f.write('{"not":"a cell"}\n')
    with pytest.raises(ValueError, match="not a cell"):
        cell_receipts.read_artifact(p)


def test_header_outvoting_world_refused(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    lines = p.read_text().splitlines()
    header = json.loads(lines[0])
    header["seed"] = header["seed"] + 999  # header lies about the run
    lines[0] = json.dumps(header, sort_keys=True)
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="outvotes"):
        cell_receipts.read_artifact(p)


def test_unknown_kind_refused(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    lines = p.read_text().splitlines()
    header = json.loads(lines[0])
    header["artifact"] = "something-else"
    lines[0] = json.dumps(header, sort_keys=True)
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="kind"):
        cell_receipts.read_artifact(p)


def test_verify_accepts_artifact_with_qc(tmp_path, receipt):
    p = cell_receipts.write_artifact(receipt, tmp_path / "a.jsonl")
    back = cell_receipts.read_artifact(p)
    v = cell_receipts.verify(back, bell())
    assert v == {"ok": True, "why": "ok"}
