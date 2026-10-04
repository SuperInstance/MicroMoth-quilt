# IONQ-RECON — MicroMoth cells vs the quilt cell contract, and what ions could falsify first

Status: **RECON / DESIGN — research-only, no silicon harmed.** This is
handoff H3 (quilt-i2i `docs/HANDOFFS.md`), the clean re-fire after an
LLM timeout killed the first dispatch. It extends — does not replace —
the 2026-09-29 H3 draft (quilt-i2i `docs/H3-micromoth-ionq-recon.md`),
which mapped the *upstream* MicroMoth fork. This pass maps what PRs
#33–42 actually landed in this repo (`docs/CELL-MAPPING.md`,
`tools/state_witness.py`, `tools/cell_receipts.py`,
`tools/collapse_ledger.py`, `tools/witness_collapse_seam.py`,
`tools/midcircuit_boundary.py`) against the **qm_\* cell contract**, and
drafts the falsification ladder.

Provenance (weight law applies — nothing here is VERIFIED-on-hardware
currency; tags below: **GROUNDED** = pinned in repo code/tests, **INFERRED**
= proposed, **SPECULATIVE** = honest guess):

| Field | Value |
|---|---|
| qm_\* contract source of truth | `quilt-gpu-lab/scratch/dogfood/luau2/brief_r1.txt` (AUTHORITATIVE SEMANTICS) + `tests/cell_api_test.lua` mirror; canonical fleet API `qm_bind / qm_link / qm_effect / qm_view / qm_tick` |
| Ledger opcode source | SuperInstance/AI-Writings `algebra.md` (five opcodes + adopted WORLD/PROOF/FORGET), via `docs/CELL-MAPPING.md` blob pins |
| Quantum carrier | `micromoth.py` import baseline (executable arity: `init, m, x, h, rx, rz, cx, crx, swap`) |
| Prior art | quilt-quant `lab/` (moth-quantum graph-v1 ZZ tomography, entanglement veto), quilt-i2i H3 draft 2026-09-29 |

---

## 1. Two contracts share one name — say which one you mean

"Quilt cell contract" is load-bearing twice in the fleet, and the
distinction decides the whole mapping:

- **The qm_\* live registry** (`qm_bind/qm_link/qm_effect/qm_view/qm_tick`)
  — a *dynamic* contract: cells hold mutable state (16 dials in [0,1],
  hearer-owned weighted edges, activation `act` in [0,1]); effects
  deliver `act += w·applied` with clamping; ticks leak everything
  geometrically. **State is stored IN the cells.**
- **The WAL ledger opcodes** (`BIND/LINK/EFFECT/VIEW/TICK` + adopted
  `WORLD/PROOF/FORGET`) — a *witness* contract: cells are append-only
  hash-chained records; nothing mutable, nothing stored except the chain.
  **State is stored NOWHERE — it is re-derived by replay.**

This repo (PRs #33–42) maps MicroMoth onto the **ledger** family. The
qm_\* registry is the *other* twin — and it is the one whose
**relational-logic** (link-before-effect, weighted delivery, leak)
quantum hardware can actually stress. Section 2 maps both at once,
because MicroMoth's cells turn out to sit between them.

## 2. The mapping (qm_\* → MicroMoth carrier)

| qm_\* semantics (verbatim from the brief) | MicroMoth carrier | Alignment verdict |
|---|---|---|
| `qm_bind(reg, name)` — idempotent register-by-name; fresh sequential id; 16 zero dials; `act=0` | `QuantumCircuit(n, m)` constructor + `LINK` boundary cell + `BIND` gate cells (`collapse_ledger.circuit_cells`); cell id = fnv1a-64 of content | **Diverges on identity**: registry ids are *positional* (nextId), ledger ids are *content-addressed* (rebinding the same program is a no-op because it hashes identically — BIND-idempotence is stronger than register-by-name). GROUNDED |
| `qm_link(src, dst, w?)` — hearer-owned edge ON dst ("dst can hear src"); w ∈ [0,1], default 0.5, clamp; find-or-update; EDGE_CAP 8, evict coldest | `cx(s,t)` = w 1; **`crx(θ, s, t)` = a literally weighted link, w = sin²(θ/2)** (SPECULATIVE bridge constant, calibratable — rung 2); `swap` = mutual hearing | **The surprise**: the continuous weight channel already exists in the executable arity and is unused by any ledger lane. Direction asymmetry maps cleanly (control→target ≈ src→dst "hearer"). EDGE_CAP-8 + coldest eviction is *classical memory policy* — ions have all-to-all connectivity, so the quantum constraint is not topology but *readout cost* (every edge inspection costs shots). INFERRED |
| `qm_effect(src, dst, a)` — delivered ONLY if dst hears src; `dst.act = clamp01(act + w·applied)`; weight NOT changed by effect | Gate application (unitary kernels, `state_witness._apply`) and collapse sampling (`collapse_ledger` EFFECT cells, seeded); midcircuit: post-boundary gates replay from the collapsed state (`midcircuit_boundary`) | **The core divergence** — see §3.1. One clean alignment though: "effect does not mutate the link" holds on both sides (gate parameters are fixed at append; the coupling is not edited by delivery). GROUNDED on the classical side |
| `qm_view(reg, id, kind)` — kind 0: `act`; kind 1: wsum (Σ edge weights, clamped); kind 2: dial | `simulate(get=...)`: `statevector`, `probabilities_dict` (pure VIEW, GROUNDED), counts/memory (WORLD, seeded — the determinism hole, honestly named and kept) | kind 0 ≈ marginal P(q=1); **kind 1 ≈ Σ\|⟨ZZ⟩\| per-edge correlators — exactly what quilt-quant's entanglement veto reads via moth graph-v1 tomography** (alignment discovered in the field, GROUNDED there); kind 2 (dial) has **no passive quantum analog** — a qubit has no basis-free scalar property; every hardware read is basis-chosen and destructive. INFERRED |
| `qm_tick(cell, leak?)` — every edge weight AND act ×(1−leak), leak default 0.1, clamp [0,1] | `state_witness.layers()`: partition gate chain into qubit-disjoint moments; each closes with a TICK cell + state hash; depth = #TICKs | **No unitary leak exists** — decoherence is the physical leak and it is basis-dependent and exponential-in-time, not uniform-geometric-per-tick. Bonus alignment: qubit-disjoint moments ARE the parallelism the registry lacks (qm effects are pairwise-sequential). GROUNDED (witness) / INFERRED (leak↔decoherence, rung 3) |

## 3. Where the formats diverge (sharpest first)

### 3.1 The effect algebra: clamped addition vs amplitude addition — THE edge

`qm_effect` accumulates non-negative scalars: `act = clamp01(act + w·a)`
with `w, a ∈ [0,1]`. Deliveries can add or saturate. They can **never
cancel, never go negative, never depend on history**.

Quantum deliveries add as **complex amplitudes**. Two routing histories
of the same delivery can arrive out of phase and annihilate (`x·x` = the
CELL-MAPPING's own probed round-trip — state returns to |0⟩). The
registry's weight space `[0,1]` cannot even *express* the cancellation
circuit (`crx(θ)` followed by `crx(−θ)` needs the sign the contract
lacks). This is not an implementation gap; it is an algebraic hole, and
it is the thing rung 1 attacks.

### 3.2 Where state lives — three ontologies of "cell state"

| | qm_\* registry | MicroMoth ledger (this repo) | IonQ hardware |
|---|---|---|---|
| State storage | IN cells (dials, weights, act), mutable, last-write-wins; eviction silently loses history | NOWHERE — fnv1a-64 chain of op records; statevector re-derived by replay; PROOF pins only its sha256 | IN the ions — physical amplitudes |
| Read cost | free (view is passive) | free (recomputation) | **destructive**: measurement collapses; every view costs shots |
| Tamper evidence | none (in-place mutation) | total (edit one gate → every downstream id moves) | none in the classical sense — but job ids + calibration snapshots are attestable |
| Replay | deterministic | sealed (seeded WORLD) — byte-identical | **impossible** — see 3.3 |

### 3.3 The sealed-receipt doctrine breaks at the silicon boundary

PRs #39–41 built exactly the right honesty machinery for a simulator:
seed IS the EFFECT parameter, unseeded runs mint `EFFECT/UNSEALED`,
verify-by-replay is exact. A QPU's randomness is **irreducibly
unseedable** — no seed exists that reproduces a hardware shot sequence.
Consequences (INFERRED, proposed for the bridge):

- Hardware collapse receipts cannot be `EFFECT/SEALED`; they should be a
  new honest status — **`EFFECT/HARDWARE`**: {job id, calibration
  snapshot id, shots, raw histogram, error bars}, verified *statistically*
  (confidence interval vs predicted distribution), never by replay.
- The CELL-MAPPING honesty rule generalizes cleanly: *refuse to launder
  hardware randomness into reproducibility*, exactly as unseeded counts
  were refused.

### 3.4 Smaller honest divergences

- **Tick**: ledger tick = qubit-disjoint moment (structural); qm_tick =
  decay event (dynamic). Quantum has no per-tick uniform decay; rung 3
  measures what it does have.
- **Identity**: sequential ids vs content hashes (§2 row 1).
- **Edge cap**: EDGE_CAP 8 with coldest-edge eviction is a memory policy,
  not physics — ions are all-to-all; the scarce resource is measurement,
  not wiring.
- **Noise**: `noise_model` is readout-error-only (measurement-error
  probabilities); IonQ adds gate error, dephasing, crosstalk — the
  simulator's noise surface is strictly smaller than the target's.

## 4. The three-rung IonQ ladder — cheapest falsification first

Framing: each rung asks hardware to say **NO** to one claim of the
classical cell relational-logic. Rung 1 is the cheapest experiment whose
outcome the classical contract *forbids* — if ions produce it anyway,
the accumulator algebra is falsified at 2 qubits.

Access path (from H3 draft, unchanged): `qiskit-ionq` provider → IonQ
Cloud; native gates GPI/GPI2/ZZ (transpiled automatically); all-to-all
connectivity; free signup credits; **pre-flight everything on IonQ's
simulator and/or moth Atlas `emu` (free) before spending credits; stop
at any paywall.**

### Rung 1 — forbidden outcomes: interference between routing histories (2 qubits, 2 circuits, ~1 job)

**Claim under test (from qm_\* semantics):** effect delivery is a
non-negative clamped accumulation — a cell that receives deliveries
along superposed routing histories behaves like *some* stochastic
mixture of those histories. Mixture ⇒ cross-history outcomes have
probability **zero**.

**Circuit L (linked):** R (route register), A (the cell). `H(R); cx(R→A); H(R); measure R, A`.

Ideal state after: ¼(|00⟩ + |10⟩ + |01⟩ − |11⟩) — every outcome 25%.
**Circuit U (unlinked control):** `H(R); H(R); measure` → |00⟩ 100%.

| outcome | classical accumulator / any dephased model | coherent quantum |
|---|---|---|
| 00 | 50% | 25% |
| 11 | 50% | 25% |
| **01, 10** | **0% — forbidden** | **25% each** |

(The |11⟩ amplitude minus sign is the interference signature; the
*observable* discriminator is P(01)+P(10): classically 0, quantum 50%.)

**Corollary (the hint's "superposition-over-interpretations"):** runs
with R=1, A=0 — 25% of all runs — learn **the link exists with zero
effect delivered** (Elitzur–Vaidman structure). The registry has no such
channel: its only dynamic readouts (act, wsum) are effect-driven or
structural metadata.

**What failure looks like:** IonQ returns ~0% on 01/10 for circuit L ⇒
interference died in transpile/dephasing — the accumulator is *not*
falsifiable this cheaply; escalate or error-mitigate, and the rung
verdict is "hardware too noisy to test cell logic at 2 qubits," which is
itself a finding. Nonzero 01/10 on circuit **U** ⇒ crosstalk/systematic
— witness untrustworthy, fix before reading anything.

### Rung 2 — the weight algebra: amplitudes compose, accumulators add (2 qubits, ~8 circuits, 1 batched job)

**Claim under test:** `act` composes linearly through chained deliveries
(`clamp01(w₁·a + w₂·a)`), and weights live in [0,1].

- **Calibration sweep:** `crx(θ)` for θ ∈ {π/6, π/3, π/2, 2π/3, π};
  measure P(A=1); fit w = sin²(θ/2). This *pins the bridge constant*
  between qm_link's weight space and the gate's angle — rung 2 pays for
  itself as calibration even if nothing fails.
- **Additivity discriminator:** `crx(π/3); crx(π/3)` (same control→target).
  Quantum: transfer sin²(π/3) = **0.75**. Accumulator: clamp01(¼+¼) =
  **0.50**. Separated by 25 points — visible at 1024 shots over readout
  noise.
- **Cancellation discriminator (the algebraic hole made physical):**
  `crx(π/3); crx(−π/3)` → quantum transfer **0** (amplitudes annihilate);
  the contract cannot express it — clamp01 forbids negative weight — so
  its *best imitation* is "weight-π/3 link then nothing," predicting
  0.25. 0 vs 0.25, cleanly separated.

**What failure looks like:** measured composition matches the linear
accumulator within error bars (it won't, if rung 1 held) ⇒ the sin²
bridge is wrong and every downstream mapping re-pins.

### Rung 3 — registry scale: wsum vs entanglement structure, leak vs decoherence (4–7 qubits, the spend rung)

Only if rungs 1–2 survive. Two sub-experiments:

- **3a — qm_view(kind 1) as total coupling.** Bind a k-cell chain, link
  neighbors with weighted `crx(θ)` links; read per-edge ⟨ZZ⟩ and global
  parity oscillation (GHZ-style witness; quilt-quant's graph-v1 ZZ
  tomography is the emu precedent). The classical wsum view *superadds*
  — Σwᵢ over k full links predicts aggregate couplings > 1, which is
  illegal as probability; quantum correlators compose through
  interference and stay bounded. If hardware tracks the quantum bound
  (it will, per rungs 1–2), the scalar wsum view is falsified as a
  "total coupling" measure and qm_view needs a correlator-based
  definition at quantum scale.
- **3b — qm_tick leak vs physical decay.** Idle the linked pair/chain
  for swept delays; measure link correlation vs delay. qm_tick predicts
  geometric ×(1−leak) per tick (uniform across edges and act); hardware
  gives basis-dependent, approximately exponential-in-time dephasing.
  Fit both; if geometric-per-tick survives as a discretization of the
  measured decay (choose tick = fixed wall time), `leak` gains a
  physical calibration table; if not, qm_tick's uniform-leak law is
  falsified for quantum-held weights.

## 5. Honest limits

- Everything in §4 is **unexecuted** — predictions are ideal-state math
  plus IonQ's published noise behavior; no credits spent, no accounts
  created. Rung ordering is by qubit/gate count, not dollar cost
  (unknown until a plan is chosen).
- The w = sin²(θ/2) bridge is the rung-2 *hypothesis*, not a fact.
- This doc maps the **qm_\* registry** contract; the WAL-ledger side of
  MicroMoth (already receipted in CELL-MAPPING) needs no ladder — its
  claims are classical and already testable by replay.
- quilt-quant cross-link: its `lab/README.md` §5 (graph-v1 ZZ reads,
  entanglement veto) is the emu-era precedent for rungs 2–3's
  correlator reads; the ladder above is those reads promoted from
  "poetry with receipts" to falsification-or-bust on real ions.

Sealed as RECON (research-only) by the H3 re-fire lane, 2026-10-04.
No claim in this doc is hardware-verified. Nothing here lands on silicon
without a separate go.
