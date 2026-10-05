#!/usr/bin/env python3
"""tests/test_rung2_preflight.py — pins for the IonQ rung-2 sim pre-flight.

FAIL-first provenance: on pristine main (without tools/rung2_preflight.py)
this module's import dies at collection — verified RED on a pristine
depth-1 clone before green, same class as test_rung1_preflight.py.
"""

import math
import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit, simulate  # noqa: E402

from rung2_preflight import (  # noqa: E402
    ACCUMULATOR_ADD,
    ACCUMULATOR_CANCEL,
    ADD_THETA,
    COHERENT_ADD,
    COHERENT_CANCEL,
    SEED,
    SHOTS,
    THETAS,
    TOL,
    accumulator_counts,
    circuit_additivity,
    circuit_calibration,
    circuit_cancellation,
    preflight,
    transfer_a1,
)


def test_receipt_passes_and_is_seeded_replayable():
    r1 = preflight()
    r2 = preflight()
    assert r1["verdict"] == "PREFLIGHT-PASS"
    assert r1["schema"] == "micromoth-quilt/rung2-preflight@v1"
    # Same seed, same everything: the run is replay-exact.
    assert r1 == r2


def test_calibration_sweep_matches_sin2_bridge():
    rng = random.Random(SEED)
    for theta in THETAS:
        counts = simulate(circuit_calibration(theta), shots=SHOTS,
                          get="counts", rng=rng)
        w = transfer_a1(counts)
        predicted = math.sin(theta / 2) ** 2
        if predicted in (0.0, 1.0):
            assert w == predicted, theta
        else:
            assert abs(w - predicted) <= TOL, theta


def test_additivity_discriminator_meets_coherent_prediction():
    counts = simulate(circuit_additivity(), shots=SHOTS, get="counts",
                      rng=random.Random(SEED))
    w = transfer_a1(counts)
    # 0.7494 vs 0.75 coherent — and ~150 sigma from the accumulator's 0.50.
    assert abs(w - COHERENT_ADD) <= TOL
    assert w > 0.7
    assert abs(w - ACCUMULATOR_ADD) > 10 * TOL


def test_cancellation_is_exact_zero():
    counts = simulate(circuit_cancellation(), shots=SHOTS, get="counts",
                      rng=random.Random(SEED))
    # Amplitudes annihilate exactly: not one A=1 hit in 200k shots, while
    # the contract's best imitation predicts 0.25.
    assert transfer_a1(counts) == COHERENT_CANCEL
    assert counts.get("10", 0) + counts.get("11", 0) == 0
    assert ACCUMULATOR_CANCEL == 0.25


def test_accumulator_model_itself_is_flagged():
    # The qm_* clamped-addition model, run as numbers: additivity
    # 0.50 and cancellation-imitation 0.25 — both separated from the
    # coherent values by the discriminators above.
    add = accumulator_counts(ADD_THETA, ADD_THETA, SHOTS)
    can = accumulator_counts(ADD_THETA, 0.0, SHOTS)
    assert abs(transfer_a1(add) - ACCUMULATOR_ADD) <= TOL
    assert abs(transfer_a1(can) - ACCUMULATOR_CANCEL) <= TOL


def test_swapped_control_target_is_not_silent():
    # Cheap tamper catch: crx(A->R) instead of crx(R->A) leaves A in |0>
    # (X(R) excites the route register, not the cell) — the additivity
    # discriminator must move off the coherent value.
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.crx(ADD_THETA, 1, 0)
    qc.crx(ADD_THETA, 1, 0)
    qc.measure(0, 0)
    qc.measure(1, 1)
    counts = simulate(qc, shots=SHOTS, get="counts",
                      rng=random.Random(SEED))
    assert transfer_a1(counts) == 0.0
    assert transfer_a1(counts) != COHERENT_ADD


def test_all_checks_true_in_receipt():
    r = preflight()
    assert all(r["checks"].values()), r["checks"]
    assert r["seed"] == SEED and r["shots"] == SHOTS
    assert r["additivity"]["coherent_prediction"] == COHERENT_ADD
    assert r["additivity"]["accumulator_prediction"] == ACCUMULATOR_ADD
    assert r["cancellation"]["coherent_prediction"] == COHERENT_CANCEL
    assert r["cancellation"]["accumulator_best_imitation"] == ACCUMULATOR_CANCEL
