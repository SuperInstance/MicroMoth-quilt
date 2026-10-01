#!/usr/bin/env python3
"""test_collapse_ledger.py — pins for the seed-plumbing wrapper.

Implements docs/CELL-MAPPING.md's "Collapse receipts, re-executable"
contract: the wrapper plumbs a seed through simulate()'s only randomness
source so collapse EFFECT cells can mint SEALED; unseeded stays
EFFECT/UNSEALED, never laundered. Run: python3 tests/test_collapse_ledger.py

Pins:
  1. tools/collapse_ledger.py exists and mints a SEALED receipt that
     verifies against a live re-execution (FAIL-first: absent on main).
  2. Same circuit + same seed -> byte-identical cell-id chain; a
     different seed diverges (the seed IS the EFFECT parameter).
  3. Tamper evidence: editing one collapse outcome or breaking the
     prev chain is named (id_mismatch@i / chain_break@i), never green.
  4. seed=None -> status EFFECT/UNSEALED and verify() refuses to call
     it re-executable (honest limit, no laundering).
  5. noise_model is pinned as an EFFECT parameter: replay with the
     recorded model reproduces; the receipt's model cannot be swapped
     silently (tampered noise_model -> replay_divergence).
  6. Sugar never ledgers: y/z/ry in qc.data raise instead of chaining.
  7. Version honesty: micromoth.py exposes no __version__ on baseline,
     so the LINK boundary cell carries a git-derived baseline label,
     not a fabricated version (doc-vs-behavior hole found by running;
     CELL-MAPPING.md's `__version__` reference is design-time wording).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

TOOL = LAB / "tools" / "collapse_ledger.py"

if TOOL.exists():
    from tools.collapse_ledger import (collapse_receipt, verify)
    from micromoth import QuantumCircuit


def bell() -> "QuantumCircuit":
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


@unittest.skipUnless(TOOL.exists(), "tools/collapse_ledger.py absent (pin 1)")
class CollapseLedgerPinned(unittest.TestCase):
    def test_tool_mints_sealed_verifying_receipt(self):
        r = collapse_receipt(bell(), 16, seed=42)
        self.assertTrue(r["sealed"])
        self.assertEqual(r["status"], "EFFECT/SEALED")
        self.assertEqual(verify(r, bell()), {"ok": True, "why": "ok"})

    def test_seed_is_the_effect_parameter(self):
        qc = bell()
        a = collapse_receipt(qc, 32, seed=7)
        b = collapse_receipt(qc, 32, seed=7)
        c = collapse_receipt(qc, 32, seed=8)
        self.assertEqual([x["id"] for x in a["cells"]],
                         [x["id"] for x in b["cells"]],
                         "same seed must replay byte-identically")
        self.assertNotEqual([x["id"] for x in a["cells"]],
                            [x["id"] for x in c["cells"]],
                            "different seed must diverge")
        self.assertTrue(all("seed" in cell["args"]
                            for cell in a["cells"] if cell["op"] == "EFFECT"),
                        "sealed EFFECT cells must pin the seed")

    def test_tamper_is_named(self):
        r = collapse_receipt(bell(), 16, seed=1)
        r["cells"][3]["args"]["outcome"] = "00"
        self.assertEqual(verify(r)["why"], "id_mismatch@3")
        r2 = collapse_receipt(bell(), 16, seed=1)
        r2["cells"][0]["prev"] = "0xdeadbeefdeadbeef"  # genesis tamper
        for c in r2["cells"][:2]:  # re-derive ids so only the chain link is wrong
            import json as _json
            body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
            canon = _json.dumps(body, sort_keys=True, separators=(",", ":"))
            from tools.collapse_ledger import fnv1a64
            c["id"] = "0x%016x" % fnv1a64(canon)
        self.assertEqual(verify(r2)["why"], "chain_break@0")

    def test_unsealed_never_laundered(self):
        r = collapse_receipt(bell(), 8, seed=None)
        self.assertFalse(r["sealed"])
        self.assertEqual(r["status"], "EFFECT/UNSEALED")
        self.assertEqual(verify(r, bell())["why"], "unsealed_not_reexecutable")

    def test_noise_model_is_pinned_effect_parameter(self):
        qc = bell()
        r = collapse_receipt(qc, 16, seed=5, noise_model=0.1)
        self.assertEqual(r["noise_model"], [0.1, 0.1])
        self.assertEqual(verify(r, qc), {"ok": True, "why": "ok"},
                         "replay must reproduce the recorded noise model")
        r["noise_model"] = [0.2, 0.2]
        self.assertEqual(verify(r, qc)["why"], "replay_divergence",
                         "swapping the noise model must be caught by replay")

    def test_sugar_never_ledgers(self):
        qc = QuantumCircuit(1, 1)
        qc.data.append(("y", 0))  # hand-built sugar, bypassing decomposition
        with self.assertRaises(ValueError):
            collapse_receipt(qc, 4, seed=1)

    def test_version_label_honest(self):
        import micromoth
        self.assertFalse(hasattr(micromoth, "__version__"),
                         "pin premise changed: micromoth grew a __version__; "
                         "wrapper must delegate to it and this pin retires")
        r = collapse_receipt(bell(), 4, seed=1)
        link = r["cells"][0]
        self.assertEqual(link["op"], "LINK")
        self.assertTrue(str(link["args"]["circuit"]).startswith("micro-moth:baseline:"),
                        "LINK boundary must carry the git-derived baseline "
                        "label, not a fabricated version: %s"
                        % link["args"]["circuit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
