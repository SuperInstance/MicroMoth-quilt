# IONQ-RUNG2-PREFLIGHT — rung 2 (weight algebra) executed against the seeded simulator

Status: **SIM PRE-FLIGHT PASS — no hardware claim.** Same doctrine as
`docs/IONQ-RUNG1-PREFLIGHT.md`: this is the mandatory pre-flight step
from `docs/IONQ-RECON.md` §4 ("pre-flight everything on IonQ's simulator
… before spending credits"), executed against this repo's own seeded
MicroMoth simulator. Rung 2's *hardware* rung remains unexecuted and
gated.

## What ran

`tools/rung2_preflight.py` (self-check: `python3 tools/rung2_preflight.py`),
pinned parameters: seed 42, 200,000 shots, tolerance ±0.006 (6-sigma
binomial band at p=0.75, the widest sweep point). Circuits: qubit 0 = R
(source), qubit 1 = A (the cell); `X(R)` makes the source deterministically
active so the link channel is isolated exactly as qm_effect's "delivered
only if dst hears src" clause reads it.

**Calibration sweep** (`crx(θ)` for θ ∈ {π/6, π/3, π/2, 2π/3, π}; transfer
= P(A=1)):

| θ | predicted w = sin²(θ/2) | measured (seeded) |
|---|---|---|
| π/6 | 0.066987 | 0.067575 |
| π/3 | 0.250000 | 0.249465 |
| π/2 | 0.500000 | 0.499775 |
| 2π/3 | 0.750000 | 0.751135 |
| π | 1.000000 | **1.0 — exact** |

The SPECULATIVE bridge constant from IONQ-RECON §2 (`crx(θ)` = a
literally weighted link, w = sin²(θ/2)) is now pinned on the simulator
across the full [0,1] weight range.

**Additivity discriminator** (`crx(π/3); crx(π/3)`, same control→target):

| model | transfer prediction | measured |
|---|---|---|
| coherent quantum (amplitudes compose) | sin²(π/3) = **0.75** | **0.749435** |
| qm_* accumulator (`clamp01(¼+¼)`) | **0.50** | model run as numbers: 0.50 — flagged |

**Cancellation discriminator** (`crx(π/3); crx(−π/3)` — the algebraic
hole from IONQ-RECON §3.1 made physical):

| model | transfer prediction | measured |
|---|---|---|
| coherent quantum (amplitudes annihilate) | **0** | **0.0 — zero A=1 hits in 200,000 shots** |
| contract's best imitation (no negative weight exists; "one π/3 link then nothing") | **0.25** | model run as numbers: 0.25 — flagged |

Verdict: **PREFLIGHT-PASS** — both discriminators land exactly where the
ideal-state math puts them, and the qm_* accumulator model is flagged on
both counts: 0.50 sits ~150 sigma from the measured 0.7494, and 0.25 is
separated from an exact-zero cancellation by construction.

## Honest limits

- Simulator-only, same noise-surface caveat as rung 1 (readout-error-only,
  strictly smaller than IonQ's; IONQ-RECON §3.4). IonQ gate fidelity on
  native GPI/GPI2/ZZ is what makes hardware 0 vs 0.25 the expensive
  question — this pre-flight buys confidence that the *experiment design*
  separates the models, nothing about the hardware.
- The accumulator model here is run as numbers (its act arithmetic is
  deterministic given an active source), not sampled — rung 1's routing
  randomness does not exist in these circuits.
- HARDWARE receipts, if this ladder ever fires, must be
  `EFFECT/HARDWARE` (job id + calibration snapshot + statistical
  verification), never replay-verified `EFFECT/SEALED` (IONQ-RECON §3.3).
- 7 pins in `tests/test_rung2_preflight.py`, including the swapped
  control→target tamper (A never gets excited; additivity discriminator
  reads exactly 0.0, moving off the coherent value).

Sealed as SIM-PREFLIGHT by the quantum lane, 2026-10-05.
