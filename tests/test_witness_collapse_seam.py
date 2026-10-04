#!/usr/bin/env python3
"""FAIL-first pins for the witness+collapse seam (tools/witness_collapse_seam.py).

Every pin fails on pristine main (module absent -> ImportError) and
passes only when the seam actually welds a witnessed boundary state to
seeded collapse outcomes.
"""

import copy
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit  # noqa: E402

from witness_collapse_seam import seam_receipt, verify  # noqa: E402


def ghz_measured(n=2, shots_seed=42, shots=16):
    qc = QuantumCircuit(n, n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    for i in range(n):
        qc.measure(i, i)
    return qc, seam_receipt(qc, shots, seed=shots_seed, proof_at=-1)


class TestSeam(unittest.TestCase):
    def test_welded_chain_verifies(self):
        qc, r = ghz_measured()
        self.assertEqual(verify(r, qc), {"ok": True, "why": "ok"})
        # weld shape: witness cells, exactly one SEAM, EFFECT tail
        ops = [c["op"] for c in r["cells"]]
        self.assertEqual(ops.count("SEAM"), 1)
        self.assertGreater(ops.count("TICK"), 0)
        si = ops.index("SEAM")
        self.assertTrue(all(o == "EFFECT" for o in ops[si + 1:]))
        self.assertGreater(len(ops[si + 1:]), 0)

    def test_seam_prev_is_last_witness_cell(self):
        qc, r = ghz_measured()
        ops = [c["op"] for c in r["cells"]]
        si = ops.index("SEAM")
        self.assertEqual(r["cells"][si]["prev"], r["cells"][si - 1]["id"])
        self.assertEqual(r["cells"][si]["args"]["boundary_state_hash"],
                         r["final_state_hash"] if "final_state_hash" in r
                         else r["boundary_state_hash"])

    def test_seeded_outcomes_replay(self):
        qc, r = ghz_measured(shots=32, shots_seed=7)
        again, r2 = ghz_measured(shots=32, shots_seed=7)
        self.assertEqual(r["outcomes"], r2["outcomes"])
        self.assertEqual([c["id"] for c in r["cells"]],
                         [c["id"] for c in r2["cells"]])
        self.assertEqual(verify(r2, again), {"ok": True, "why": "ok"})

    def test_tampered_outcome_names_itself(self):
        qc, r = ghz_measured()
        bad = copy.deepcopy(r)
        for c in reversed(bad["cells"]):
            if c["op"] == "EFFECT":
                c["args"]["outcome"] = ("1" if c["args"]["outcome"] == "0" else "0")
                break
        v = verify(bad, qc)
        self.assertFalse(v["ok"])
        self.assertIn("id_mismatch", v["why"])

    def test_wrong_circuit_replay_divergence(self):
        qc, r = ghz_measured()
        other = QuantumCircuit(2, 2)
        other.h(0)
        other.measure(0, 0)
        other.measure(1, 1)
        v = verify(r, other)
        self.assertFalse(v["ok"])

    def test_no_measurement_refused(self):
        qc = QuantumCircuit(2, 0)
        qc.h(0)
        qc.cx(0, 1)
        with self.assertRaises(ValueError):
            seam_receipt(qc, 8, seed=1)

    def test_unsealed_refused(self):
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)
        with self.assertRaises(ValueError):
            seam_receipt(qc, 8, seed=None)

    def test_ghz4_depth_and_proof(self):
        qc = QuantumCircuit(4, 4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        for i in range(4):
            qc.measure(i, i)
        r = seam_receipt(qc, 8, seed=3, proof_at=-1)
        self.assertEqual(verify(r, qc), {"ok": True, "why": "ok"})
        ops = [c["op"] for c in r["cells"]]
        self.assertEqual(ops.count("TICK"), 4)  # h + 3 cx moments
        self.assertEqual(ops.count("PROOF"), 1)


if __name__ == "__main__":
    unittest.main()
