#!/usr/bin/env python3
"""Pins for the step-3 ADOPTION: receipt lanes stop mutating global RNG.

seeded_counts / _shot_outcomes (cell_receipts.py), _sample_seeded
(collapse_ledger.py), and _sample_outcome (midcircuit_boundary.py) now
pass `rng=random.Random(seed)` / draw from an injected Random(seed)
instead of the old seed/run/restore plumbing. The injected Random(seed)
stream is the same MT19937 sequence the global module draws after
random.seed(seed), so results must be byte-identical; these pins prove
it live by running the OLD plumbing inline as the reference.

FAIL-first contract: on the pre-adoption tip the plumbing sites still
call random.getstate/setstate around a global reseed — the source pin
trips there; the byte-identity pins also trip there only if behavior
changed (they should not — adoption is a no-op on outcomes).

Run: python3 -m pytest tests/test_seam_adoption_rng.py
"""

from __future__ import annotations

import inspect
import random
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit, simulate  # noqa: E402
import cell_receipts  # noqa: E402
import collapse_ledger  # noqa: E402
import midcircuit_boundary  # noqa: E402


def old_single_draw(seed):
    """The retired plumbing for _sample_outcome, kept inline as the live
    reference: reseed the module-global RNG, draw once, restore."""
    state = random.getstate()
    try:
        random.seed(seed)
        return random.random()
    finally:
        random.setstate(state)


def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def old_plumbing(qc, shots, get):
    """The retired plumbing, kept inline as the live reference."""
    state = random.getstate()
    try:
        random.seed(1234)
        return simulate(qc, shots=shots, get=get)
    finally:
        random.setstate(state)


# --- source pins: plumbing sites must not touch global RNG state -------


def test_seeded_counts_has_no_global_restore():
    src = inspect.getsource(cell_receipts.seeded_counts)
    assert "getstate" not in src and "setstate" not in src, \
        "seeded_counts still seeds/restores the module-global RNG"


def test_shot_outcomes_has_no_global_restore():
    src = inspect.getsource(cell_receipts._shot_outcomes)
    assert "getstate" not in src and "setstate" not in src, \
        "_shot_outcomes still seeds/restores the module-global RNG"


def test_sample_seeded_has_no_global_restore():
    src = inspect.getsource(collapse_ledger._sample_seeded)
    assert "getstate" not in src and "setstate" not in src, \
        "_sample_seeded still seeds/restores the module-global RNG"


def test_adoption_uses_injected_seam():
    src = inspect.getsource(cell_receipts.seeded_counts)
    assert "rng=" in src, "seeded_counts must route through simulate's rng seam"
    src = inspect.getsource(collapse_ledger._sample_seeded)
    assert "rng=" in src, "_sample_seeded must route through simulate's rng seam"


# --- behavior pins: byte-identical to the old plumbing -----------------


def test_counts_byte_identical_to_old_plumbing():
    qc = bell()
    adopted = cell_receipts.seeded_counts(qc, 512, 1234)["histogram"]
    reference = old_plumbing(qc, 512, "counts")
    assert adopted == reference


def test_shot_outcomes_byte_identical_to_old_plumbing():
    qc = bell()
    adopted = cell_receipts._shot_outcomes(qc, 256, 1234)
    reference = [str(b) for b in old_plumbing(qc, 256, "memory")]
    assert adopted == reference


def test_sample_seeded_byte_identical_to_old_plumbing():
    qc = bell()
    adopted = collapse_ledger._sample_seeded(qc, 256, 1234, [])
    reference = old_plumbing(qc, 256, "memory")
    assert adopted == reference


# --- honesty pin: global RNG untouched, even under a mid-call check ----


def test_global_rng_untouched_by_concurrent_draw():
    """A draw interleaved between two seeded calls must not change
    either call's result — impossible if the global RNG were the
    sampling source (old plumbing made this an accident of restore)."""
    qc = bell()
    random.seed(999)  # dirty global state on purpose
    a = cell_receipts.seeded_counts(qc, 128, 77)["histogram"]
    random.random()  # concurrent, unrelated draw
    b = cell_receipts.seeded_counts(qc, 128, 77)["histogram"]
    assert a == b
    c = collapse_ledger._sample_seeded(qc, 128, 77, [])
    random.random()
    d = collapse_ledger._sample_seeded(qc, 128, 77, [])
    assert c == d


# --- midcircuit_boundary._sample_outcome adoption (last plumbing site) --


def test_sample_outcome_has_no_global_restore():
    src = inspect.getsource(midcircuit_boundary._sample_outcome)
    assert "getstate" not in src and "setstate" not in src, \
        "_sample_outcome still seeds/restores the module-global RNG"


def test_sample_outcome_uses_injected_rng():
    src = inspect.getsource(midcircuit_boundary._sample_outcome)
    assert "random.Random(seed)" in src, \
        "_sample_outcome must draw from an injected random.Random(seed)"


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 1234, 2**31 - 1])
def test_sample_outcome_byte_identical_to_old_plumbing(seed):
    """Fresh Random(seed) first-draw == old global reseed first-draw."""
    p_zero = 0.371  # arbitrary interior point, exercises the compare
    adopted = midcircuit_boundary._sample_outcome(p_zero, seed)
    draw = old_single_draw(seed)
    reference = "0" if draw < p_zero else "1"
    assert adopted == reference


def test_global_rng_untouched_by_midcircuit_sample():
    """Interleaved global draws cannot perturb a seeded boundary outcome,
    and the global RNG state is byte-for-byte untouched by the call."""
    random.seed(31337)
    before = random.getstate()
    a = midcircuit_boundary._sample_outcome(0.5, 42)
    mid = random.getstate()
    assert mid == before, "_sample_outcome perturbed the module-global RNG"
    random.random()  # concurrent, unrelated draw
    b = midcircuit_boundary._sample_outcome(0.5, 42)
    assert a == b
    assert random.getstate() != before  # sanity: the interleaved draw landed


def test_midcircuit_receipt_stable_under_global_noise():
    """Full receipt path: same seed, dirty vs clean global RNG, same
    boundary outcome cell — the receipt lane is now independent of
    whatever else is drawing from module-global random."""
    from micromoth import QuantumCircuit
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.x(1)
    random.seed(1)
    clean = midcircuit_boundary.midcircuit_receipt(qc, boundary=2, seed=42)
    random.seed(987654)  # hostile global state
    for _ in range(5):
        random.random()
    noisy = midcircuit_boundary.midcircuit_receipt(qc, boundary=2, seed=42)
    eff = [c for c in clean["cells"] if c["op"] == "EFFECT"][0]
    eff_n = [c for c in noisy["cells"] if c["op"] == "EFFECT"][0]
    assert eff["args"]["outcome"] == eff_n["args"]["outcome"]
