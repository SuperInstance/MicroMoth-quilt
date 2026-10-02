#!/usr/bin/env python3
"""test_widening_pins.py — widening pins for the selfplay battery.

Follow-up to tests/test_grader_blindspots.py (PR#30 repair). The repair
closed each 0.00 blind spot once; this file widens the coverage so the
same defect CLASSES cannot regress through a sibling path. Each pin is
FAIL-first against its booked mutation (evidence: experiments/selfplay/
SUMMARY.md after the seal-pin widening run) and GREEN on the pristine
imported kernel.

1. phase on the |1> branch — the repair pin asserts rz|0>. A mutation on
   the |1> branch of phaseturn (sin(+theta/2) -> sin(-theta/2)) makes rz
   e^{-i theta/2} on BOTH branches — a GLOBAL phase no counts/
   probability/balance observable can see. Pin: the exact complex
   amplitude of the |1> branch after x·rz(theta); its imaginary part
   +sin(theta/2) is the global-vs-relative discriminator (the flipped
   kernel gives -sin(theta/2), a distance of 2·sin(theta/2) ~ 0.64).

2. per-qubit noise orientation — the repair pin exercises qubit 0 of a
   1-qubit circuit. A kernel break that mis-indexes the noise model
   (noise_model[j] -> noise_model[0]) is invisible to every uniform-noise
   pin (float noise_model broadcasts) and to every Bell pin (a per-qubit
   relabel of a symmetric distribution is a fixpoint). Pin: a 2-qubit
   ASYMMETRIC circuit with DISTINCT per-qubit error rates, asserted
   against the analytic 4-outcome distribution in kernel order (qubit 0
   mixed first, then qubit 1).

3. boundary-draw canary — the repair pin injects r == first partial sum.
   The sampler walks n cumulative boundaries; strict r<cumu must hold at
   EVERY boundary, not just the first. Pins: a draw equal to an INTERIOR
   partial sum (must fall through to the NEXT outcome) and a draw equal
   to the TOTAL cumulative sum (accepted by no index; the shot is
   dropped — the strict-< contract at the last boundary; r<=cumu would
   accept it at the last index).

Run: python3 tests/test_widening_pins.py
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


def asymmetric_2q() -> "QuantumCircuit":
    """Two-qubit circuit with a fully asymmetric clean distribution."""
    qc = QuantumCircuit(2, 2)
    qc.rx(0.6, 0)
    qc.rx(1.1, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def mix_once(probs: dict, qubit: int, p: float) -> dict:
    """One kernel-semantic readout-flip pass on `qubit` (0 = LSB): every
    (b0: bit=0, b1: bit=1) pair becomes (1-p)*p0 + p*p1 / (1-p)*p1 + p*p0,
    with both reads taken before either write (kernel order)."""
    out = dict(probs)
    width = len(next(iter(probs)))
    for key, val in probs.items():
        idx = int(key, 2)
        if (idx >> qubit) & 1:
            continue  # visit each pair once, from the 0-side
        partner = format(idx | (1 << qubit), f"0{width}b")
        p0, p1 = val, probs[partner]
        out[key] = (1 - p) * p0 + p * p1
        out[partner] = (1 - p) * p1 + p * p0
    return out


class TestPhaseOnOneBranch(unittest.TestCase):
    """Widening 1: rz's |1> branch must stay a RELATIVE phase."""

    def test_rz_on_one_keeps_the_analytic_imaginary_sign(self):
        theta = 0.7
        qc = QuantumCircuit(1)
        qc.x(0)
        qc.rz(theta, 0)
        sv = simulate(qc, get="statevector")

        self.assertEqual(sv[0], [0, 0])
        # e^{+i theta/2}|1> = [cos(theta/2), +sin(theta/2)]
        self.assertAlmostEqual(sv[1][0], cos(theta / 2), places=12)
        self.assertAlmostEqual(
            sv[1][1], +sin(theta / 2), places=12,
            msg="rz |1>-branch phase flipped: the imaginary part of the |1> "
                "amplitude must be +sin(theta/2). With the flipped sign rz "
                "degenerates to a GLOBAL phase (e^{-i theta/2} on both "
                "branches) — invisible to every magnitude observable; only "
                "this amplitude pin can see it.",
        )


class TestNoiseIsPerQubit(unittest.TestCase):
    """Widening 2: the mixing orientation must hold per qubit, not just
    on qubit 0 of a 1-qubit circuit."""

    def test_two_qubit_asymmetric_pins_the_per_qubit_mixing(self):
        p_err = [0.05, 0.15]  # DISTINCT per-qubit rates: uniform-blind breaks show
        clean = simulate(asymmetric_2q(), get="probabilities_dict")

        values = list(clean.values())
        self.assertTrue(all(v > 0 for v in values),
                        "pin premise: all four outcomes must be populated")
        self.assertGreater(values[0] + values[1], values[2] + values[3],
                           "pin premise: distribution must be qubit-asymmetric")

        # Analytic reference in kernel order: qubit 0 first, then qubit 1.
        expected = mix_once(clean, 0, p_err[0])
        expected = mix_once(expected, 1, p_err[1])

        noisy = simulate(asymmetric_2q(), get="probabilities_dict",
                         noise_model=p_err)
        for key in sorted(expected):
            self.assertAlmostEqual(
                noisy[key], expected[key], places=12,
                msg=f"per-qubit noise mixing broke at outcome {key}: the "
                    f"kernel must read noise_model[j] for qubit j and mix "
                    f"(1-p)*p0 + p*p1 / (1-p)*p1 + p*p0 per qubit, qubit 0 "
                    f"first. A mis-index (noise_model[0] for every qubit) or "
                    f"a swapped branch shows up here and nowhere else — "
                    f"uniform-noise and Bell pins cannot see it.",
            )


class TestBoundaryDrawCanary(unittest.TestCase):
    """Widening 3: strict r<cumu must hold at EVERY cumulative boundary."""

    def _memory_with_draw(self, qc, r: float) -> list:
        real_random = micromoth.random.random
        try:
            micromoth.random.random = lambda: r
            return simulate(qc, shots=1, get="memory")
        finally:
            micromoth.random.random = real_random

    def test_interior_boundary_draw_falls_to_the_next_outcome(self):
        qc = asymmetric_2q()
        probs = simulate(qc, get="probabilities_dict")
        keys = list(probs)  # insertion order == sampler index order
        boundary = probs[keys[0]] + probs[keys[1]]  # cumu right after index 1

        mem = self._memory_with_draw(qc, boundary)
        self.assertEqual(
            mem, [keys[2]],
            msg="a draw exactly equal to the cumulative sum AFTER index 1 "
                "must NOT be accepted at index 1 under strict r<cumu; it "
                "falls through to the NEXT outcome. r<=cumu double-counts "
                "the boundary (comparison_flip at an interior boundary — "
                "the repair pin only guards the first).",
        )

    def test_total_boundary_draw_is_dropped(self):
        qc = bell()
        probs = simulate(qc, get="probabilities_dict")
        total = sum(probs.values())  # sequential sum == sampler accumulation

        mem = self._memory_with_draw(qc, total)
        self.assertEqual(
            mem, [],
            msg="a draw exactly equal to the TOTAL cumulative sum must not "
                "be accepted by ANY index under strict r<cumu — the shot "
                "falls through the last boundary and is dropped. r<=cumu "
                "accepts it at the last index (comparison_flip at the "
                "total boundary).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
