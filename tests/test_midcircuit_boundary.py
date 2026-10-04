#!/usr/bin/env python3
"""FAIL-first pins for the mid-circuit boundary close (tools/midcircuit_boundary.py).

Every pin fails on pristine main (module absent -> ImportError) and
passes only when the boundary tool actually witnesses a mid-circuit
collapse: seeded outcome, projected state, post-boundary ticks replayed
from the collapsed state.
"""

import copy
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit  # noqa: E402

import hashlib  # noqa: E402

from midcircuit_boundary import (  # noqa: E402
    DIALECT, PROB_DIGITS, _collapse, _qubit_prob, _run_moments, _zero_state,
    midcircuit_receipt, verify,
)
from state_witness import PRECISION, state_digest  # noqa: E402


def ghz_boundary(seed=42):
    """h(0); cx(0,1); m(0); x(1) — boundary on qubit 0, one gate after."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.x(1)
    return qc, midcircuit_receipt(qc, boundary=2, seed=seed)


class TestMidcircuitBoundary(unittest.TestCase):
    def test_chain_verifies_and_shape(self):
        qc, r = ghz_boundary()
        self.assertEqual(r["dialect"], DIALECT)
        self.assertEqual(verify(r, qc), {"ok": True, "why": "ok"})
        ops = [c["op"] for c in r["cells"]]
        self.assertEqual(ops[0], "LINK")
        self.assertEqual(ops.count("EFFECT"), 1)
        self.assertEqual(ops.count("INIT-STATE"), 1)
        ei, ii = ops.index("EFFECT"), ops.index("INIT-STATE")
        self.assertEqual(ii, ei + 1)
        self.assertTrue(any(o == "PROOF" for o in ops[:ei]))
        self.assertEqual(ops[-1], "PROOF")
        # ticker continuity across the boundary
        ticks = [c["args"]["ticker"] for c in r["cells"] if c["op"] == "TICK"]
        self.assertEqual(ticks, list(range(1, len(ticks) + 1)))

    def test_outcome_0_is_exact_and_post_boundary_applies_to_it(self):
        # Force the 0-branch by seeding until outcome '0' (P=0.5; scan a
        # few seeds deterministically rather than hard-coding one).
        found = None
        for seed in range(50):
            qc, r = ghz_boundary(seed=seed)
            if r["outcome"] == "0":
                found = (qc, r, seed)
                break
        self.assertIsNotNone(found, "no seed in 50 draws yielded outcome 0")
        qc, r, seed = found
        self.assertEqual(verify(r, qc), {"ok": True, "why": "ok"})
        # collapsed state after outcome 0 is |00> (GHZ projected: q0=0
        # keeps index 0 only), then x(1) flips qubit 1 -> index 2 = |10>.
        expect = [[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [0.0, 0.0]]
        want = "0x%016x" % __import__("state_witness").fnv1a64(
            state_digest(expect, PRECISION))
        self.assertEqual(r["final_state_hash"], want)

    def test_outcome_1_final_state_is_11(self):
        found = None
        for seed in range(50):
            qc, r = ghz_boundary(seed=seed)
            if r["outcome"] == "1":
                found = (qc, r)
                break
        self.assertIsNotNone(found)
        qc, r = found
        # outcome 1 projects GHZ onto index 3 (q1=1,q0=1); x(1) flips
        # qubit 1 -> index 1.
        expect = [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        want = "0x%016x" % __import__("state_witness").fnv1a64(
            state_digest(expect, PRECISION))
        self.assertEqual(r["final_state_hash"], want)

    def test_seeded_reproducibility(self):
        qc1, r1 = ghz_boundary(seed=7)
        qc2, r2 = ghz_boundary(seed=7)
        self.assertEqual(r1["outcome"], r2["outcome"])
        self.assertEqual([c["id"] for c in r1["cells"]],
                         [c["id"] for c in r2["cells"]])

    def test_effect_pins_sampled_probability(self):
        qc, r = ghz_boundary()
        eff = [c for c in r["cells"] if c["op"] == "EFFECT"][0]
        # GHZ boundary: P(outcome) = 0.5 either way
        self.assertEqual(eff["args"]["prob"], round(0.5, PROB_DIGITS))
        self.assertEqual(eff["args"]["seed"], 42)
        self.assertEqual(eff["args"]["qubit"], 0)

    def test_tampered_outcome_names_itself(self):
        qc, r = ghz_boundary()
        bad = copy.deepcopy(r)
        for c in reversed(bad["cells"]):
            if c["op"] == "EFFECT":
                c["args"]["outcome"] = "1" if c["args"]["outcome"] == "0" else "0"
                break
        v = verify(bad, qc)
        self.assertFalse(v["ok"])
        self.assertIn("id_mismatch", v["why"])

    def test_tampered_collapsed_state_names_itself(self):
        qc, r = ghz_boundary()
        bad = copy.deepcopy(r)
        for c in bad["cells"]:
            if c["op"] == "INIT-STATE":
                c["args"]["state_sha256"] = "0" * 64
        v = verify(bad, qc)
        self.assertFalse(v["ok"])
        self.assertIn("id_mismatch", v["why"])

    def test_wrong_circuit_replay_detected(self):
        qc, r = ghz_boundary()
        other = QuantumCircuit(2, 2)
        other.h(0)
        other.measure(0, 0)
        other.x(1)
        v = verify(r, other)
        self.assertFalse(v["ok"])

    def test_unseeded_refused(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.measure(0, 0)
        qc.x(1)
        for bad_seed in (None, -1, 1.5):
            with self.assertRaises(ValueError):
                midcircuit_receipt(qc, boundary=1, seed=bad_seed)

    def test_non_measurement_boundary_refused(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(0, 0)
        with self.assertRaises(ValueError):
            midcircuit_receipt(qc, boundary=1, seed=1)  # cx, not 'm'

    def test_second_measurement_refused(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(0, 0)
        qc.x(1)
        qc.measure(1, 1)
        with self.assertRaises(ValueError):
            midcircuit_receipt(qc, boundary=2, seed=1)

    def test_no_executable_op_after_boundary_refused(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.measure(0, 0)  # end-of-circuit: the seam's territory
        with self.assertRaises(ValueError):
            midcircuit_receipt(qc, boundary=1, seed=1)

    def test_degenerate_boundary_refused(self):
        qc = QuantumCircuit(1, 1)
        qc.x(0)          # |1> with certainty
        qc.measure(0, 0)
        qc.x(0)
        with self.assertRaises(ValueError):
            midcircuit_receipt(qc, boundary=1, seed=1)

    def test_collapse_math_projection_and_renorm(self):
        # (|00>+|11>)/sqrt(2), measure qubit 1... use explicit kernel:
        n = 2
        k = [[0.0, 0.0]] * 4
        k[0] = [2 ** -0.5, 0.0]
        k[3] = [2 ** -0.5, 0.0]
        collapsed, p = _collapse([list(e) for e in k], n, 1, "1", PRECISION)
        self.assertAlmostEqual(p, 0.5)
        # outcome 1 on qubit 1 keeps index 3 only; renormalized to |11>
        self.assertAlmostEqual(collapsed[3][0], 1.0)
        for i in (0, 1, 2):
            self.assertEqual(collapsed[i], [0.0, 0.0])
        self.assertAlmostEqual(sum(c[0] ** 2 + c[1] ** 2 for c in collapsed), 1.0)

    def test_verify_without_circuit_checks_chain_only(self):
        qc, r = ghz_boundary()
        self.assertEqual(verify(r), {"ok": True, "why": "ok"})
        bad = copy.deepcopy(r)
        bad["cells"][3]["args"]["state_hash"] = "0xdeadbeef"
        v = verify(bad)
        self.assertFalse(v["ok"])
        self.assertIn("id_mismatch", v["why"])


if __name__ == "__main__":
    unittest.main()
