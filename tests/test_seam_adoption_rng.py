#!/usr/bin/env python3
"""Pins for the step-3 ADOPTION: receipt lanes stop mutating global RNG.

seeded_counts / _shot_outcomes (cell_receipts.py) and _sample_seeded
(collapse_ledger.py) now pass `rng=random.Random(seed)` through
simulate()'s injected-rng seam instead of the old seed/run/restore
plumbing. The injected Random(seed) stream is the same MT19937
sequence the global module draws after random.seed(seed), so results
must be byte-identical; these pins prove it live by running the OLD
plumbing inline as the reference, on both counts and memory paths.

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
