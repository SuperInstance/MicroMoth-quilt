# IONQ-RUNG1-PREFLIGHT — rung 1 executed against the seeded simulator

Status: **SIM PRE-FLIGHT PASS — no hardware claim.** This doc records the
mandatory pre-flight step from `docs/IONQ-RECON.md` §4 ("pre-flight
everything on IonQ's simulator and/or moth Atlas `emu` (free) before
spending credits") executed against this repo's own seeded MicroMoth
simulator. Rung 1's *hardware* rung remains unexecuted and gated.

## What ran

`tools/rung1_preflight.py` (self-check: `python3 tools/rung1_preflight.py`),
pinned parameters: seed 42, 200,000 shots, tolerance ±0.0026 (6-sigma
binomial band at p=0.25).

| Circuit | Prediction (IONQ-RECON) | Measured (seeded) |
|---|---|---|
| L: `H(R); cx(R→A); H(R); measure R,A` | four outcomes 25% each; P(01)+P(10) = **0.50** | 50079 / 49725 / 49905 / 50291; forbidden sum **0.49815** |
| U: `H(R); H(R); measure R` (control) | \|0⟩ with probability 1 | `{"0": 200000}` — exact |
| L minus closing `H(R)` (dephased imitation / witness tamper) | 00/11 only, forbidden sum **0** | 00/11 only, forbidden sum **0.0** — flagged |
| qm_* accumulator model sampled directly | forbidden outcomes algebraically impossible | 00/11 only, forbidden sum **0.0** — flagged |

Verdict: **PREFLIGHT-PASS** — the classical-contract discriminator
behaves exactly as the ideal-state math predicts on the simulator, and
it has teeth: both the dephased mixture and the qm_* clamped-addition
model itself are flagged at forbidden sum 0.0, ~500 sigma from the
coherent value.

## Honest limits

- Simulator-only. MicroMoth's noise surface is readout-error-only and
  strictly smaller than IonQ's (IONQ-RECON §3.4); rung 1's stated
  failure mode ("hardware too noisy to test cell logic at 2 qubits")
  cannot be assessed here.
- HARDWARE receipts, if this ladder ever fires, must be
  `EFFECT/HARDWARE` (job id + calibration snapshot + statistical
  verification), never replay-verified `EFFECT/SEALED` (IONQ-RECON §3.3)
  — the sealed-receipt doctrine breaks at the silicon boundary and this
  pre-flight claims nothing that would launder it.
- 8 pins in `tests/test_rung1_preflight.py`, including the swapped
  cx control→target tamper (collapses L to |00⟩; discriminator moves).

Sealed as SIM-PREFLIGHT by the quantum lane, 2026-10-05.
