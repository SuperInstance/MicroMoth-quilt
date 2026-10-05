#!/usr/bin/env python3
"""rung1_preflight.py — IonQ ladder rung 1, SIMULATOR pre-flight.

Implements the pre-flight step docs/IONQ-RECON.md §4 mandates before any
hardware credit is spent: run rung 1's two circuits on the seeded
MicroMoth simulator and verify the classical-contract discriminator
behaves exactly as the ideal-state math predicts.

Rung 1 claim under test (qm_* effect algebra): delivery is non-negative
clamped accumulation, so cross-history outcomes 01/10 are FORBIDDEN
(P = 0) for any stochastic mixture of routing histories. Coherent
quantum gives P(01)+P(10) = 0.50.

Circuits (qubit 0 = R route register, qubit 1 = A the cell):
  L (linked):    H(R); cx(R->A); H(R); measure R, A   -> all four ~25%
  U (unlinked):  H(R); H(R); measure R                 -> |00> 100%
  L-dephased:    L without the closing H(R) — the exact
                 mixture/dephased imitation (00/11 only)

Conventions: counts keys are clbit strings, leftmost char = highest
clbit (micromoth sampler). Forbidden sum P(01)+P(10) is symmetric in
bit order, so the discriminator is convention-insensitive.

Run: python3 tools/rung1_preflight.py   (self-check, prints a receipt)
"""

import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit, simulate  # noqa: E402  (baseline authority)

# Pinned experiment parameters (receipts cite these; change = new receipt).
SEED = 42
SHOTS = 200_000
IDEAL_FORBIDDEN = 0.50        # coherent prediction for P(01)+P(10)
MIXTURE_FORBIDDEN = 0.0       # classical accumulator prediction
# 6-sigma binomial band at SHOTS for p=0.25: 0.25 +/- 6*sqrt(.25*.75/200000)
TOL = 0.0026


def circuit_linked():
    """L: H(R); cx(R->A); H(R); measure both. Ideal: 25% each outcome."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.h(0)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def circuit_unlinked():
    """U: H(R); H(R); measure R. Ideal: |0> with probability 1 (sanity)."""
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.h(0)
    qc.measure(0, 0)
    return qc


def circuit_dephased_imitation():
    """L minus the closing H(R): the dephased/mixture imitation.

    This is the circuit a witness-integrity tamper produces (drop the
    interference-closing gate) AND the prediction of any stochastic
    mixture model. Ideal: 00/11 only -> forbidden sum exactly 0.
    """
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def mixture_counts(shots, rng):
    """The qm_* accumulator model itself, sampled: route R is a classical
    coin; R=0 history delivers nothing (00), R=1 history delivers (11).
    Every other outcome is algebraically forbidden by clamp01 addition."""
    counts = {}
    for _ in range(shots):
        out = '11' if rng.random() < 0.5 else '00'
        counts[out] = counts.get(out, 0) + 1
    return counts


def forbidden_sum(counts):
    """P(01)+P(10) — outcomes the classical accumulator forbids."""
    total = sum(counts.values())
    cross = counts.get('01', 0) + counts.get('10', 0)
    return cross / total if total else 0.0


def outcome_share(counts, key):
    total = sum(counts.values())
    return counts.get(key, 0) / total if total else 0.0


def preflight(seed=SEED, shots=SHOTS):
    """Run all three circuits + the analytic mixture; return a receipt.

    Verdicts are PASS/FAIL against the IONQ-RECON predictions, not
    hardware claims. Sim-only, seeded, replay-exact.
    """
    rng = random.Random(seed)
    counts_l = simulate(circuit_linked(), shots=shots, get='counts', rng=rng)
    counts_u = simulate(circuit_unlinked(), shots=shots, get='counts', rng=rng)
    counts_d = simulate(circuit_dephased_imitation(), shots=shots,
                        get='counts', rng=rng)
    counts_m = mixture_counts(shots, rng)

    f_l, f_d, f_m = (forbidden_sum(c) for c in (counts_l, counts_d, counts_m))
    u_clean = outcome_share(counts_u, '0')

    ideal_ok = all(abs(outcome_share(counts_l, k) - 0.25) <= TOL
                   for k in ('00', '01', '10', '11'))
    coherent_ok = abs(f_l - IDEAL_FORBIDDEN) <= TOL
    control_ok = u_clean == 1.0
    dephased_flagged = f_d == MIXTURE_FORBIDDEN
    mixture_flagged = f_m == MIXTURE_FORBIDDEN
    passed = all((ideal_ok, coherent_ok, control_ok,
                  dephased_flagged, mixture_flagged))

    return {
        'schema': 'micromoth-quilt/rung1-preflight@v1',
        'source': 'docs/IONQ-RECON.md rung 1 (sim pre-flight, no hardware)',
        'seed': seed,
        'shots': shots,
        'circuit_L_counts': counts_l,
        'circuit_L_forbidden_sum': round(f_l, 6),
        'circuit_U_counts': counts_u,
        'dephased_imitation_counts': counts_d,
        'accumulator_mixture_counts': counts_m,
        'predictions': {
            'coherent_forbidden_sum': IDEAL_FORBIDDEN,
            'mixture_forbidden_sum': MIXTURE_FORBIDDEN,
        },
        'checks': {
            'L_four_way_flat': ideal_ok,
            'L_coherent_discriminator': coherent_ok,
            'U_control_deterministic': control_ok,
            'dephased_tamper_flagged': dephased_flagged,
            'accumulator_model_flagged': mixture_flagged,
        },
        'verdict': 'PREFLIGHT-PASS' if passed else 'PREFLIGHT-FAIL',
    }


if __name__ == '__main__':
    import json
    print(json.dumps(preflight(), indent=2, sort_keys=True))
