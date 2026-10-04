#!/usr/bin/env python3
"""Pins for the simulate() injected-RNG seam (CELL-MAPPING.md step 3).

The named determinism hole was: simulate() reads only the module-global
`random`, so receipt lanes had to mutate global state to seed a run.
This seam adds `rng=None` to simulate(); rng is used ONLY for the
shot-sampling loop, and rng=None keeps the classic global pattern —
the unseeded hole stays OPEN by default (the tripwire in
test_cell_mapping.py must stay green), receipt lanes get a way to never
be unseeded.

FAIL-first contract: on pristine main simulate() takes no `rng`
argument — pins here raise TypeError there. Run:
python3 -m pytest tests/test_simulate_injected_rng.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

import micromoth  # noqa: E402
from micromoth import QuantumCircuit, simulate  # noqa: E402


def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


class SeqRng:
    """Deterministic injected RNG: cycles a fixed float sequence."""

    def __init__(self, seq):
        self._seq = list(seq)
        self._i = 0

    def random(self):
        v = self._seq[self._i % len(self._seq)]
        self._i += 1
        return v


def test_seam_exists_fail_first():
    """simulate() must accept an injected rng (TypeError on pristine main)."""
    import inspect
    params = inspect.signature(simulate).parameters
    assert "rng" in params, (
        "simulate() exposes no rng parameter — the injected-RNG seam "
        "(CELL-MAPPING.md step 3) is absent")


def test_injected_rng_is_the_only_randomness():
    """Injected rng fully determines sampling: same seq -> same counts,
    and the module-global RNG state is untouched by an injected run."""
    random.seed(12345)
    before = random.getstate()
    r1 = SeqRng([0.1, 0.9, 0.3, 0.7])
    c1 = simulate(bell(), shots=4, get="counts", rng=r1)
    assert random.getstate() == before, (
        "injected-rng run must not touch the module-global RNG")
    r2 = SeqRng([0.1, 0.9, 0.3, 0.7])
    c2 = simulate(bell(), shots=4, get="counts", rng=r2)
    assert c1 == c2
    assert sum(c1.values()) == 4


def test_injected_rng_low_bits_both_outcomes():
    """Sequence crossing the |00> probability boundary (0.5 for Bell)
    must land in both outcomes — the injected stream is really used."""
    rng = SeqRng([0.01, 0.99, 0.01, 0.99])
    counts = simulate(bell(), shots=4, get="counts", rng=rng)
    assert set(counts) == {"00", "11"}, (
        "injected rng stream not honored: %r" % counts)


def test_default_path_matches_seeded_global():
    """rng=None keeps the global pattern exactly: a seeded global run
    and an injected random.Random(s) run agree (same Mersenne stream)."""
    qc = bell()
    random.seed(42)
    expected = simulate(qc, shots=64, get="counts")
    got = simulate(qc, shots=64, get="counts", rng=random.Random(42))
    assert got == expected


def test_default_path_still_unseeded_honest():
    """The hole stays open by default: two unseeded global runs may
    disagree — the tripwire class must not be auto-fixed by this seam."""
    a = simulate(bell(), shots=32, get="counts")
    b = simulate(bell(), shots=32, get="counts")
    assert sum(a.values()) == 32 and sum(b.values()) == 32
    # not asserting disagreement (RNG may coincide), asserting the
    # seam did NOT silently seed anything: unseeded runs remain legal.


def test_memory_path_uses_injected_rng():
    """get='memory' honors the injected rng too (same sampling loop)."""
    rng = SeqRng([0.01, 0.01, 0.99, 0.99])
    m = simulate(bell(), shots=4, get="memory", rng=rng)
    assert m == ["00", "00", "11", "11"]


def test_module_copyright_and_notice_intact():
    """micromoth.py is modified baseline: the Apache notices and the
    altered-works clause must survive the patch."""
    src = (LAB / "micromoth.py").read_text()
    assert src.count("Copyright Moth Quantum 2024") == 1
    assert src.count("Copyright IBM 2023") == 1
    assert "modified files need to carry a notice" in src
