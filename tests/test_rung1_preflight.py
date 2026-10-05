#!/usr/bin/env python3
"""tests/test_rung1_preflight.py — pins for the IonQ rung-1 sim pre-flight.

FAIL-first provenance: on pristine main (commit 1067050^.. without this
branch) tools/rung1_preflight.py does not exist and this module's import
dies at collection — verified RED on a pristine depth-1 clone before
green.
"""

import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit, simulate  # noqa: E402

from rung1_preflight import (  # noqa: E402
    IDEAL_FORBIDDEN,
    MIXTURE_FORBIDDEN,
    SEED,
    SHOTS,
    TOL,
    circuit_dephased_imitation,
    circuit_linked,
    circuit_unlinked,
    forbidden_sum,
    mixture_counts,
    outcome_share,
    preflight,
)


def test_receipt_passes_and_is_seeded_replayable():
    r1 = preflight()
    r2 = preflight()
    assert r1["verdict"] == "PREFLIGHT-PASS"
    assert r1["schema"] == "micromoth-quilt/rung1-preflight@v1"
    # Same seed, same everything: the run is replay-exact.
    assert r1 == r2


def test_circuit_L_four_way_flat_within_band():
    counts = simulate(circuit_linked(), shots=SHOTS, get="counts",
                      rng=random.Random(SEED))
    for key in ("00", "01", "10", "11"):
        assert abs(outcome_share(counts, key) - 0.25) <= TOL, key


def test_discriminator_meets_coherent_prediction():
    counts = simulate(circuit_linked(), shots=SHOTS, get="counts",
                      rng=random.Random(SEED))
    f = forbidden_sum(counts)
    assert abs(f - IDEAL_FORBIDDEN) <= TOL
    # Teeth at the pinned shot count: the observed forbidden mass is
    # ~500 sigma from the accumulator's 0.0 claim.
    assert f > 0.4


def test_unlinked_control_is_deterministic():
    counts = simulate(circuit_unlinked(), shots=1024, get="counts",
                      rng=random.Random(SEED))
    assert counts == {"0": 1024}


def test_dephased_tamper_is_flagged():
    # Dropping the closing H(R) is exactly the dephased/mixture model —
    # the witness-integrity failure mode named in IONQ-RECON rung 1.
    counts = simulate(circuit_dephased_imitation(), shots=SHOTS,
                      get="counts", rng=random.Random(SEED))
    assert forbidden_sum(counts) == MIXTURE_FORBIDDEN
    assert outcome_share(counts, "01") == 0.0
    assert outcome_share(counts, "10") == 0.0


def test_accumulator_model_itself_is_flagged():
    # The qm_* clamped-addition model, sampled directly: forbidden
    # outcomes are algebraically impossible, and the discriminator says so.
    rng = random.Random(SEED)
    counts = mixture_counts(SHOTS, rng)
    assert set(counts) == {"00", "11"}
    assert forbidden_sum(counts) == MIXTURE_FORBIDDEN


def test_swapped_control_target_is_not_silent():
    # Cheap tamper catch: cx(A->R) instead of cx(R->A) collapses L to
    # |00> — the discriminator must move off the coherent value.
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(1, 0)
    qc.h(0)
    qc.measure(0, 0)
    qc.measure(1, 1)
    counts = simulate(qc, shots=SHOTS, get="counts",
                      rng=random.Random(SEED))
    assert outcome_share(counts, "00") > 0.99
    assert forbidden_sum(counts) != IDEAL_FORBIDDEN


def test_all_checks_true_in_receipt():
    r = preflight()
    assert all(r["checks"].values()), r["checks"]
    assert r["seed"] == SEED and r["shots"] == SHOTS
    assert r["predictions"] == {
        "coherent_forbidden_sum": IDEAL_FORBIDDEN,
        "mixture_forbidden_sum": MIXTURE_FORBIDDEN,
    }
