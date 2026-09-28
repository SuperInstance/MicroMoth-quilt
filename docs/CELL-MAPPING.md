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
