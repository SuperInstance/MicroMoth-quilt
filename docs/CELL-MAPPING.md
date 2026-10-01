# CELL-MAPPING — quantum ops as quilt cells (DESIGN receipt)

Status: **DESIGN ONLY** — no quilt-native code lands in this repo until a
future PR implements against these pins. This note is the design receipt
the waking lane reads first. Template: `AUDIT.md` (manifest = the audit
pattern; `tests/` extension = the pin pattern).

Provenance (the weight law applies — nothing here is VERIFIED currency):

| Field | Value |
|---|---|
| Circuit op source of truth | `micromoth.py` `simulate()` dispatch (this repo, import baseline) |
| Upstream circuit semantics | `moth-quantum/MicroMoth` (fork parent) |
| Cell algebra (canonical) | `SuperInstance/AI-Writings` `algebra.md` — the five opcodes `BIND / LINK / EFFECT / VIEW / TICK` (+ adopted `FORGET`, `PROOF`) |
| Hash convention | fnv1a-64 over the canonical cell encoding (fleet WAL convention, genesis `prev = 0x0000000000000000`) |

## Op inventory (parsed from `simulate()`, baseline 491e881 lineages)

Primitive ops the simulator dispatch recognizes — the ledger records
**primitives, not sugar**: `y`, `z`, `ry` decompose into `rx`/`rz`/`x`
at append time (`micromoth.py` QuantumCircuit methods), so a circuit
cell chain never contains them.

| Op | Arity | Params | Dispatch class |
|---|---|---|---|
| `init` | n-qubit | statevector pairs | initialization |
| `m` | 1q → 1c | qubit, clbit | measurement record |
| `x` | 1q | qubit | single-qubit |
| `h` | 1q | qubit | single-qubit |
| `rx` | 1q | theta, qubit | single-qubit |
| `rz` | 1q | theta, qubit | single-qubit |
| `cx` | 2q | source, target | two-qubit |
| `crx` | 2q | theta, source, target | two-qubit |
| `swap` | 2q | a, b | two-qubit |

## The mapping

One `QuantumCircuit.data` list **is** a cell ledger. Concretely:

- **BIND** — every gate application becomes a BIND cell:
  `{kind: "gate", args: {op, qubits: [...], theta?}}`. "I'm here."
  The first gate's `prev` is the genesis constant; every later gate's
  `prev` is the fnv1a-64 of the preceding gate cell. The circuit is
  therefore a hash chain — edit one gate and every downstream id moves,
  which is exactly the tamper-evidence property the import manifest
  already pins repo-wide.
- **LINK** — the `prev` chain above *is* LINK ("we are neighbors"),
  plus one explicit LINK cell per circuit boundary: (circuit, simulator
  version `__version__`, shots plan). Circuit↔circuit references
  (future: subroutines) also LINK; there is no other wiring.
- **EFFECT** — collapses and noise: each shot outcome is an EFFECT cell
  `{kind: "collapse", shot: i, outcome: bitstring, seed}` and each
  `noise_model[j]` entry is an EFFECT parameter, not a silent edit to
  the circuit chain. "Something happened" — measurement is an event,
  never a mutation of gate cells.
- **VIEW** — `simulate(qc, shots, get=...)` is literally a VIEW cell:
  `{args: {shots, get}}` over the circuit cell. `counts`,
  `statevector`, `probabilities_dict` are three views of the *same*
  circuit chain; the ledger records which view was taken, so "we looked
  at counts" is itself receipted and re-derivable.
- **TICK** — circuit moments: partition the gate chain into
  qubit-disjoint layers; a TICK cell closes each layer ("advance by one
  moment"). Depth = number of TICKs. TICK gives the ledger a
  coarse-grained time without touching gate order.

Adopted opcodes, used sparingly:

- **PROOF** — a statevector witness at a chosen TICK: amplitude pairs
  `[re, im]` rounded to a declared precision, sha256-pinned exactly like
  `receipts/import-baseline.json` pins file digests. Verify by replay,
  not by trust.
- **FORGET** — shot-level EFFECT cells are the erasure unit: counts may
  be retained while individual collapse records are FORGET-table
  ("right to be erased"), with the FORGET itself receipted.

## Collapse receipts, re-executable

The re-execution contract the sleeping lane wanted, stated honestly:

1. The ledger pins `seed` and `shots` as EFFECT parameters.
2. Re-running `simulate()` with the same circuit chain + same seed must
   reproduce the same collapse EFFECT chain, byte for byte.
3. **Honest limit (baseline truth):** `simulate()` today takes **no
   seed argument** — its shot sampling is unseeded. Until a wrapper
   plumbs a seed, collapse EFFECT cells minted from live runs are
   receipted `EFFECT/UNSEALED` (seed: null), and only seeded replays may
   mint sealed collapse receipts. Design does not launder unseeded
   randomness into reproducibility.

## Honest limits (read before implementing)

- `y`, `z`, `ry` never appear in a ledger (sugar decomposes at append).
- `noise_model` is measurement-error probabilities only; any richer
  noise class is out of baseline scope.
- Statevector cost is `2**num_qubits` amplitude pairs — the ledger is
  cheap, the VIEW is not; PROOF witnesses are the mitigation, not a
  license to simulate big.
- `init` payloads embed full statevectors; they are hash-pinned
  (sha256, manifest pattern), never inlined into VIEW receipts.

Sealed as DESIGN by the snowball fleet session, 2026-09-28
(Asia/Shanghai). Pins: `tests/test_cell_mapping.py`.
# CELL-MAPPING — MicroMoth operations on the five-opcode quilt cell model

Status: design receipt with executable pins (docs-first, per the waking-lane
plan). Companion to `AUDIT.md` (import baseline). Claim tags: **VERIFIED**
(run this date, outputs below are real), **INFERRED** (proposed, not built).

## Source pins

- Canonical algebra: SuperInstance/AI-Writings `algebra.md` — git blob
  `74b2a7002113eae54e1582aa0099cca47918d566`, sha256 of fetched bytes
  `207db2de37406664023f24eb4be9b5fbae6719dc78ea26bb5490c91289b26e66`.
  Five opcodes BIND · LINK · EFFECT · VIEW · TICK (+ six adopted, of which
  WORLD and PROOF turn out load-bearing below). Do not add opcodes.
- Canonical producer precedent: SuperInstance/git-agent `quilt_emit`
  (git-agent#1); ledger-sealing precedent: SuperInstance/quilt-gpu-lab
  receipt manifest (quilt-gpu-lab#1, doctrine provenance quilt-gpu-lab#2).
- Subject: `micromoth.py` @ this repo's HEAD, 289 lines, read in full.

## What micromoth actually is (VERIFIED, probed live)

Two arities of "operation," and the mapping treats them differently:

**Program arity** — what `QuantumCircuit.data` holds after the builder
methods run. The builder expands derived gates at circuit-construction
time, so the program arity is larger than the executable arity. Probed:

```
qc.ry(0.5,0); qc.z(0); qc.t(0); qc.y(0)
→ [('rx',π/2,0), ('rz',0.5,0), ('rx',-π/2,0),
   ('rz',π,0), ('rz',π/4,0), ('rz',π,0), ('x',0)]
```

**Executable arity** — what `simulate()`'s dispatch recognizes: exactly
`{init, m, x, h, rx, rz, cx, crx, swap}` — nine ops. Everything else in a
program is sugar over these nine. (Corrections welcome; `crx` and `swap`
were MicroMoth additions over upstream MicroQiskit.)

Outputs: `statevector` (2ⁿ complex pairs), `probabilities_dict`,
`memory`/`counts` (shot sampling via the global `random` module).

## The five-opcode choreography (INFERRED where marked)

The mapping obeys the algebra's laws rather than forcing fit; where a law
and the physics disagree, the receipt says so.

| Opcode | Quantum role | Law respected | Notes |
|---|---|---|---|
| BIND | Assert the circuit cell: `(kind:"qc-program", payload:{n, m, name, program[]})`; cell id = hash of the program bytes (algebra: id = hash(kind, payload, parents)) | BIND idempotent — rebinding the same program is a no-op | The import-baseline seal (#1) was the lane's first BIND: 260 files → `receipts/import-baseline.json` |
| EFFECT | One witness row per gate application during execution: `{op:"EFFECT", params:{gate, qubits, theta?}, hash, prev_hash}` | EFFECT associative — the bound program itself is the merged event stream (law 3), so per-gate witnesses are a *projection*, not extra state | Per-gate witnesses give re-execution its comparison points (state hash after each TICK) |
| TICK | Advance `ticker` once per executed gate; witness records `(ticker, gate, state_hash)` | TICK monotonic — see the x·x nuance below | The *clock* is monotonic even when the *state* is not |
| VIEW | Return `statevector` or `probabilities_dict` only | VIEW pure (law 4) — VERIFIED: `probabilities_dict` identical across repeated calls (probed: Bell → `{'00':0.5,'01':0.0,'10':0.0,'11':0.5}` twice) | counts/memory are NOT VIEW-safe (see the hole) |
| WORLD | The adopted "predict what happens next" op: seeded shot-sampling. `WORLD(cell-with-seed)` → witness `{seed, shots, histogram}` | — (adopted op, no law) | The honest home for counts: a named prediction, not a purity violation |
| PROOF | The witness log's own hash chain — `prev_hash` linkage over EFFECT/TICK/WORLD rows | — | Same fnv1a-64 family as the rest of the fleet ledgers |

### The determinism hole (the receipt's sharp edge, VERIFIED)

`simulate(get='counts'|'memory')` samples with the global, unseeded
`random.random()`. Probed on pristine HEAD: two unseeded Bell runs at
256 shots returned `{'00':146,'11':110}` and `{'11':133,'00':123}` —
**different receipts for the same cell.** A naive `VIEW(circuit) → counts`
therefore violates law 4 (VIEW purity), and an unseeded counts receipt is
not replayable — it fails the fleet's replay-over-trust doctrine outright.

Resolution, no new opcodes: counts live in WORLD witnesses with the seed
in the params (`{op:"WORLD", params:{seed, shots}}`). Seeded sampling is
deterministic — probed: `random.seed(42)` twice → identical histograms
(`{'11':127,'00':129}`). The seed is part of the cell's identity for
sampling purposes; two cells differing only in seed are different
predictions, and both may be kept.

### The x·x nuance (why TICK lives in the witness, not the payload)

Probed: a one-qubit circuit `x;x` returns the statevector to |0⟩
(`[[1,0],[0,0]]`). State is unitary and can come home; the algebra's
monotonicity law cannot mean "payload never repeats." It means the
*ticker and witness log never retreat*: TICKⁿ(c) advances the clock and
appends rows even when the statevector rounds back to its start. The
mapping keeps law 5 by placing monotonicity in the log, where it is
actually true — and the per-TICK state_hash witness makes the round trip
visible instead of invisible.

## Proposed cell kinds (INFERRED)

`qc-program` (bound circuit), `qc-state` (statevector witness after a
TICK), `qc-sample` (WORLD histogram witness). Twenty-six kinds exist in
the algebra; these three extend none and collide with none known. Kinds
are operational, not categorical — a `qc-sample` is a prediction record,
not "knowledge."

## Edges named (weight law: specificity × verification)

- `mm-quantum-cells → aw-quint-opcode` — this doc names AI-Writings
  `algebra.md` (blob + sha256 above) as the canonical opcode source. On
  merge the edge mints per the fleet weight law.
- `mm-quantum-cells → gl-ledgers` — quilt-gpu-lab#2 proved a lane can
  seal ledgers fleet-doctrine-style and cite the algebra by name; this
  receipt applies the same provenance pattern.
- Producer precedent named: git-agent `quilt_emit` (git-agent#1) — the
  eventual `micromoth_emit` (below) is its quantum analog.

## Smallest first build (one evening, INFERRED)

1. `tools/cell_receipts.py::seeded_counts(qc, shots, seed)` — seeds the
   global RNG, samples, returns `{histogram, seed, shots}`; the only
   public entrypoint the WORLD witness ever needs.
2. A Bell-run witness emitter: BIND the program cell → TICK the four
   gates with per-TICK state hashes → WORLD(42, 256) → PROOF the chain;
   output one JSONL ledger. This is `micromoth_emit` v1, the git-agent
   `quilt_emit` analog.
3. Only after 1–2 land: consider a `simulate()` patch accepting an
   injected RNG (keeps the global-module pattern for beginners, removes
   the hole for receipt lanes). Until then, the hole is *named*, which
   is worth more than a silent fix.

## Executable pins

`tests/test_cell_mapping.py` carries this receipt's claims as test law:
exact executable arity (guards against silent op additions), program-arity
expansion (documents the sugar), VIEW purity, the hole-is-real tripwire
(eight unseeded runs must not all agree — turns RED if anyone "fixes"
sampling by auto-seeding, which would silently change honesty semantics),
seeded determinism, and the x·x state-return. FAIL-first demonstrated for
the tripwire by monkeypatching an auto-seeding `simulate` (pins RED,
restored). Suite runs green on pristine HEAD.
