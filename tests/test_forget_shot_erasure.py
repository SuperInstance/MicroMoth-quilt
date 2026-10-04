"""Pins for tools/cell_receipts.py forget() — the FORGET clause of
docs/CELL-MAPPING.md (adopted opcode): shot-level EFFECT cells are the
erasure unit; counts may be retained while individual collapse records
are FORGET-table, with the FORGET itself receipted.

FAIL-first: these pins import-die on pristine main (forget and the
per-shot EFFECT journal do not exist there — verified depth-1).
"""

import random
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit  # noqa: E402
import cell_receipts  # noqa: E402
from collapse_ledger import GENESIS  # noqa: E402


def _bell(shots=16, seed=42):
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return cell_receipts.emit(qc, shots=shots, seed=seed, name="bell"), qc


class TestForgetShotErasure(unittest.TestCase):
    def test_emit_journals_per_shot_effect_cells(self):
        r, _ = _bell()
        fx = [c for c in r["cells"] if c["op"] == "EFFECT"]
        self.assertEqual(len(fx), 16, "one collapse EFFECT per shot")
        self.assertEqual([c["args"]["shot"] for c in fx], list(range(16)))
        self.assertTrue(all(c["args"]["seed"] == 42 for c in fx))
        # outcomes are real memory-sample bitstrings, replay-stable
        qc = r  # silence linters
        del qc
        r2, _ = _bell()
        self.assertEqual(
            [c["args"]["outcome"] for c in fx],
            [c["args"]["outcome"] for c in r2["cells"] if c["op"] == "EFFECT"],
        )

    def test_forget_replaces_in_place_and_chain_continues(self):
        r, qc = _bell()
        before = [c["id"] for c in r["cells"]]
        out = cell_receipts.forget(r, [0, 3], "subject exercised erasure right")
        self.assertEqual(len(out["cells"]), len(r["cells"]), "in-place, no rows dropped")
        fg = [c for c in out["cells"] if c["op"] == "FORGET"]
        self.assertEqual([c["args"]["shot"] for c in fg], [0, 3])
        self.assertEqual(fg[0]["prev"], r["cells"][-16]["prev"],
                         "FORGET keeps the erased cell's chain position")
        self.assertEqual(fg[0]["args"]["erased_id"], before[-16],
                         "erased original id is receipted (diffable)")
        self.assertEqual(fg[0]["args"]["reason"], "subject exercised erasure right")
        # every downstream id moved: erasure is visible, not silent
        self.assertNotEqual(out["cells"][-1]["id"], before[-1])
        self.assertEqual(cell_receipts.verify(out, qc), {"ok": True, "why": "ok"})

    def test_histogram_retained_while_records_erased(self):
        r, _ = _bell()
        out = cell_receipts.forget(r, list(range(16)), "erase all shots")
        self.assertEqual(out["histogram"], r["histogram"],
                         "aggregate counts retained per CELL-MAPPING design")
        self.assertEqual(out["forgotten_shots"], list(range(16)))
        self.assertEqual(
            cell_receipts.verify(out)["why"], "ok")

    def test_refusals_not_faked(self):
        r, _ = _bell()
        with self.assertRaises(ValueError):
            cell_receipts.forget(r, [0], "")            # empty reason
        with self.assertRaises(ValueError):
            cell_receipts.forget(r, [99], "no such shot")
        once = cell_receipts.forget(r, [0], "first pass")
        with self.assertRaises(ValueError):
            cell_receipts.forget(once, [0], "double erase")
        # refusals never mutated the original; re-forgetting the SAME
        # input is legitimate (independent derived ledger, ids differ)
        self.assertEqual(len([c for c in r["cells"] if c["op"] == "FORGET"]), 0)
        twice = cell_receipts.forget(r, [0], "independent pass")
        self.assertNotEqual(once["cells"][-1]["id"], twice["cells"][-1]["id"])

    def test_tamper_with_erased_id_is_named(self):
        r, qc = _bell()
        out = cell_receipts.forget(r, [5], "legit")
        bad = dict(out)
        bad["cells"] = [dict(c) for c in out["cells"]]
        fg = [c for c in bad["cells"] if c["op"] == "FORGET"][0]
        fg["args"] = dict(fg["args"])
        fg["args"]["erased_id"] = "0xdeadbeef"  # rewrite the erasure record
        self.assertFalse(cell_receipts.verify(bad, qc)["ok"])

    def test_forget_cell_without_reason_fails_verify(self):
        r, _ = _bell()
        out = cell_receipts.forget(r, [2], "x")
        bad = dict(out)
        bad["cells"] = [dict(c) for c in out["cells"]]
        fg = [c for c in bad["cells"] if c["op"] == "FORGET"][0]
        fg["args"] = dict(fg["args"])
        fg["args"]["reason"] = "   "  # laundered into silence
        v = cell_receipts.verify(bad)
        self.assertFalse(v["ok"])
        self.assertIn("forget_reason_empty", v["why"])

    def test_unseeded_still_refused(self):
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)
        with self.assertRaises(ValueError):
            cell_receipts.seeded_counts(qc, 8, None)


if __name__ == "__main__":
    unittest.main()
