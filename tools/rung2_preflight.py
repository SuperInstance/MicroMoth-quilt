#!/usr/bin/env python3
"""rung2_preflight.py — IonQ ladder rung 2, SIMULATOR pre-flight.

Pre-flight step docs/IONQ-RECON.md §4 mandates before rung 2 spends
hardware credits: execute the weight-algebra discriminators on the
seeded MicroMoth simulator and verify they land exactly where the
ideal-state math puts them.

Rung 2 claim under test (qm_* weight algebra): act composes linearly
through chained deliveries — clamp01(w1*a + w2*a) with weights in
[0,1]. Quantum amplitudes compose differently:
  - additivity:  crx(pi/3); crx(pi/3)  -> transfer sin^2(pi/3) = 0.75
                 accumulator:          -> clamp01(1/4 + 1/4) = 0.50
  - cancellation: crx(pi/3); crx(-pi/3) -> transfer 0 (amplitudes
                 annihilate); the contract has no negative weight, so
                 its best imitation is "one pi/3 link then nothing"
                 predicting 0.25.

Circuits (qubit 0 = R the source, qubit 1 = A the cell):
  calibration:   X(R); crx(theta, R, A); measure R, A for
                 theta in {pi/6, pi/3, pi/2, 2pi/3, pi}
                 transfer w = sin^2(theta/2) pins the SPECULATIVE
                 bridge constant named in IONQ-RECON §2.
  additivity:    X(R); crx(pi/3, R, A); crx(pi/3, R, A); measure
  cancellation:  X(R); crx(pi/3, R, A); crx(-pi/3, R, A); measure

Conventions: counts keys are clbit strings, leftmost char = highest
clbit (micromoth sampler), so key[0] = A, key[1] = R. X(R) makes the
source deterministically active — the calibration isolates the link
channel exactly as qm_effect's "delivered only if dst hears src"
clause reads it.

Run: python3 tools/rung2_preflight.py   (self-check, prints a receipt)
"""

import math
import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit, simulate  # noqa: E402  (baseline authority)

# Pinned experiment parameters (receipts cite these; change = new receipt).
SEED = 42
SHOTS = 200_000
THETAS = (math.pi / 6, math.pi / 3, math.pi / 2, 2 * math.pi / 3, math.pi)
ADD_THETA = math.pi / 3
# 6-sigma binomial band at SHOTS for p=0.75 (the widest sweep point):
# 6*sqrt(.75*.25/200000) ~ 0.0058; p=0.25 band is 0.0026 (rung-1 pin).
TOL = 0.006
COHERENT_ADD = 0.75        # sin^2(pi/3): amplitudes composed
ACCUMULATOR_ADD = 0.50     # clamp01(1/4 + 1/4): scalar accumulator
COHERENT_CANCEL = 0.0      # exact amplitude annihilation
ACCUMULATOR_CANCEL = 0.25  # best imitation: one pi/3 link, then nothing


def circuit_calibration(theta):
    """X(R); crx(theta, R->A); measure both. P(A=1) = sin^2(theta/2)."""
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.crx(theta, 0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def circuit_additivity():
    """X(R); crx(pi/3); crx(pi/3). Coherent 0.75 vs accumulator 0.50."""
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.crx(ADD_THETA, 0, 1)
    qc.crx(ADD_THETA, 0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def circuit_cancellation():
    """X(R); crx(pi/3); crx(-pi/3). Coherent 0.0; imitation predicts 0.25."""
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.crx(ADD_THETA, 0, 1)
    qc.crx(-ADD_THETA, 0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def accumulator_counts(theta_a, theta_b, shots):
    """The qm_* accumulator model itself: with the source active and the
    link present, each delivery lands deterministically at weight
    w = sin^2(theta/2) (the rung-2 bridge constant), and act composes by
    clamped scalar addition. crx(-theta) has no negative-weight
    expression — the model's best imitation is no delivery at all
    (theta_b = 0 -> w = 0)."""
    act = min(1.0, math.sin(theta_a / 2) ** 2 + math.sin(theta_b / 2) ** 2)
    n1 = round(shots * act)
    # Two-char keys, circuit convention: key[0] = A (the cell), key[1] = R.
    # The source is deterministically active in the model, so R = '1'.
    return {"11": n1, "01": shots - n1}


def transfer_a1(counts):
    """P(A=1): leftmost key char is the highest clbit = A."""
    total = sum(counts.values())
    hit = counts.get("10", 0) + counts.get("11", 0)
    return hit / total if total else 0.0


def preflight(seed=SEED, shots=SHOTS):
    """Run the calibration sweep + both discriminators; return a receipt.

    Verdicts are PASS/FAIL against the IONQ-RECON predictions, not
    hardware claims. Sim-only, seeded, replay-exact.
    """
    rng = random.Random(seed)

    sweep = {}
    calibration_ok = True
    for theta in THETAS:
        c = simulate(circuit_calibration(theta), shots=shots,
                     get="counts", rng=rng)
        w = transfer_a1(c)
        predicted = math.sin(theta / 2) ** 2
        sweep[f"theta={theta:.6f}"] = {
            "measured_transfer": round(w, 6),
            "predicted_sin2": round(predicted, 6),
        }
        if predicted in (0.0, 1.0):
            calibration_ok = calibration_ok and w == predicted
        else:
            calibration_ok = calibration_ok and abs(w - predicted) <= TOL

    counts_add = simulate(circuit_additivity(), shots=shots,
                          get="counts", rng=rng)
    counts_can = simulate(circuit_cancellation(), shots=shots,
                          get="counts", rng=rng)
    m_add = accumulator_counts(ADD_THETA, ADD_THETA, shots)
    m_can = accumulator_counts(ADD_THETA, 0.0, shots)

    add_meas = transfer_a1(counts_add)
    can_meas = transfer_a1(counts_can)
    add_model = transfer_a1(m_add)
    can_model = transfer_a1(m_can)

    add_ok = abs(add_meas - COHERENT_ADD) <= TOL
    can_ok = can_meas == COHERENT_CANCEL
    add_model_flagged = abs(add_model - ACCUMULATOR_ADD) <= TOL
    can_model_flagged = abs(can_model - ACCUMULATOR_CANCEL) <= TOL
    passed = all((calibration_ok, add_ok, can_ok,
                  add_model_flagged, can_model_flagged))

    return {
        "schema": "micromoth-quilt/rung2-preflight@v1",
        "source": "docs/IONQ-RECON.md rung 2 (sim pre-flight, no hardware)",
        "seed": seed,
        "shots": shots,
        "calibration_sweep": sweep,
        "additivity": {
            "circuit_counts": counts_add,
            "measured_transfer": round(add_meas, 6),
            "coherent_prediction": COHERENT_ADD,
            "accumulator_prediction": ACCUMULATOR_ADD,
        },
        "cancellation": {
            "circuit_counts": counts_can,
            "measured_transfer": round(can_meas, 6),
            "coherent_prediction": COHERENT_CANCEL,
            "accumulator_best_imitation": ACCUMULATOR_CANCEL,
        },
        "accumulator_model": {
            "additivity_transfer": round(add_model, 6),
            "cancellation_transfer": round(can_model, 6),
        },
        "checks": {
            "calibration_matches_sin2_bridge": calibration_ok,
            "additivity_meets_coherent_prediction": add_ok,
            "cancellation_exact_zero": can_ok,
            "accumulator_additivity_flagged": add_model_flagged,
            "accumulator_cancellation_flagged": can_model_flagged,
        },
        "verdict": "PREFLIGHT-PASS" if passed else "PREFLIGHT-FAIL",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(preflight(), indent=2, sort_keys=True))
