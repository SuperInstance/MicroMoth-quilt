#!/usr/bin/env python3
"""test_grader_blindspots.py — repair pins for the three 0.00 shapes.

Round-11 finding (exp015/selfplay-d1): the mutation battery scored 0.72
overall but exactly 0.00 on three shapes — `phase_sign_flip`,
`noise_mixing_swap`, `comparison_flip`. The 0.00s are not instrument
noise: each mutation is a REAL defect that every pin in the battery was
blind to, for a different structural reason. These three pins close the
holes. Each one is FAIL-first against its mutation (evidence in the
repair receipt) and GREEN on the pristine imported kernel.

Shape-by-shape rationale (root cause -> pin):

1. phase_sign_flip — the mutation conjugates the |0> branch of the rz
   phase rotation, turning a RELATIVE phase into (at least on |0>) a
   GLOBAL one. Every magnitude observable the battery pins (counts,
   probabilities_dict, balance) is phase-insensitive, and no statevector
   pin exercises rz. Pin: assert the exact complex amplitude e^{-iθ/2}
   on rz|0>, where the sign of the imaginary part is the observable.

2. noise_mixing_swap — the mutation swaps the two mixing weights, which
   is exactly a per-qubit re-LABELLING of the output bit (probs[b0] <->
   probs[b1]). The battery's only noise pin runs a Bell state, whose
   distribution is symmetric under the relabel. Pin: an ASYMMETRIC
   single-qubit distribution, where the two branches are not
   interchangeable, asserted against the analytic (1-p)*p0 + p*p1.

3. comparison_flip — r<cumu -> r<=cumu changes behaviour only when the
   draw lands exactly on a cumulative boundary, an event of probability
   zero for a continuous RNG; the battery never injects that draw. Pin:
   drive the sampler with a draw equal to the exact cumulative partial
   sum (read live from probabilities_dict, not hard-coded) and require
   the boundary draw to fall through to the next outcome (strict <).

Run: python3 tests/test_grader_blindspots.py
"""
from __future__ import annotations

import sys
import unittest
from math import cos, sin
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

import micromoth  # noqa: E402
from micromoth import QuantumCircuit, simulate  # noqa: E402


def bell() -> "QuantumCircuit":
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


class TestPhaseIsRelativeNotGlobal(unittest.TestCase):
    """Blind spot 1: rz's phase sign was unobservable to every pin."""

    def test_rz_on_zero_keeps_the_analytic_imaginary_sign(self):
        theta = 0.7
        qc = QuantumCircuit(1)
        qc.rz(theta, 0)
        sv = simulate(qc, get="statevector")

        # e^{-i theta/2}|0> = [cos(theta/2), -sin(theta/2)]
        self.assertAlmostEqual(sv[0][0], cos(theta / 2), places=12)
        self.assertAlmostEqual(
            sv[0][1], -sin(theta / 2), places=12,
            msg="rz phase sign flipped: the imaginary part of the |0> "
                "branch must be -sin(theta/2) (relative phase), not "
                "+sin(theta/2) (which would make rz a global phase).",
        )
        # And it is a phase on the |0> branch only: the |1> branch is |0> here.
        self.assertEqual(sv[1], [0, 0])


class TestMeasurementErrorIsLabelled(unittest.TestCase):
    """Blind spot 2: a bit-relabelling of the noise mixing is invisible
    to every symmetric (Bell/balance) pin."""

    def test_asymmetric_distribution_pins_the_mixing_orientation(self):
        p_meas = 0.1
        qc = QuantumCircuit(1, 1)
        qc.rx(0.6, 0)
        qc.measure(0, 0)

        clean = simulate(qc, get="probabilities_dict")  # deterministic
        p0, p1 = clean["0"], clean["1"]
        self.assertGreater(p0, p1, "pin premise: distribution must be asymmetric")

        noisy = simulate(qc, get="probabilities_dict", noise_model=[p_meas])
        self.assertAlmostEqual(noisy["0"], (1 - p_meas) * p0 + p_meas * p1, places=12)
        self.assertAlmostEqual(noisy["1"], (1 - p_meas) * p1 + p_meas * p0, places=12)
        # The orientation is the observable: the majority branch stays majority.
        self.assertGreater(noisy["0"], noisy["1"],
                           "measurement-error mixing inverted: the noisy "
                           "majority branch flipped to the minority outcome "
                           "(a per-qubit relabelling of the readout).")


class TestSamplingBoundaryIsStrict(unittest.TestCase):
    """Blind spot 3: the acceptance comparison is only exercised at a
    measure-zero boundary event; no pin injected one."""

    def test_boundary_draw_falls_through_under_strict_comparison(self):
        qc = bell()
        probs = simulate(qc, get="probabilities_dict")
        boundary = probs["00"]  # exact cumulative partial sum at index 0

        real_random = micromoth.random.random
        try:
            micromoth.random.random = lambda: boundary
            mem = simulate(qc, shots=1, get="memory")
        finally:
            micromoth.random.random = real_random

        self.assertEqual(
            mem, ["11"],
            msg="a draw exactly equal to a cumulative boundary must NOT be "
                "accepted at that index under strict r<cumu; it falls "
                "through to the next outcome. r<=cumu double-counts the "
                "boundary (comparison_flip).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
