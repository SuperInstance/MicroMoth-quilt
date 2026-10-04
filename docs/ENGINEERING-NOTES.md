# MicroMoth-quilt — Engineering Notes

## Architecture

Two layers, deliberately decoupled:

```
                 +--------------------------------------------------+
                 | micromoth.py  (import baseline, sealed)          |
                 |                                                  |
  user code ---> |  QuantumCircuit  --data: [(op, ...), ...]        |
                 |      |  builder methods (sugar decomposes here)  |
                 |      v                                           |
                 |  simulate(qc, shots, get, noise_model)           |
                 |    dense statevector k[2**n] = [re, im] pairs    |
                 |    helpers: superpose / turn / phaseturn         |
                 |    dispatch: init m x h rx rz | cx crx swap      |
                 |    outputs: statevector | probabilities_dict     |
                 |             | counts | memory                    |
                 +--------------------------------------------------+
                        ^ sealed sha256 pin (import-baseline.json)
                        | observed, never modified
                 +--------------------------------------------------+
                 | receipt lane (fleet additions)                   |
                 |                                                  |
                 | tools/collapse_ledger.py                         |
                 |   seed -> global RNG -> simulate -> restore      |
                 |   LINK cell -> BIND cells (gates) -> EFFECT      |
                 |     cells (per-shot collapses), fnv1a-64 chain   |
                 |   verify(): re-derive ids + live re-execution    |
                 |                                                  |
                 | tools/import_manifest.py  (repo-wide seal)       |
                 | tools/selfplay.py         (bug-injection field)  |
                 | receipts/ + tests/       (claims + pins)         |
                 +--------------------------------------------------+

                 quantum-wow/  (browser: micromoth.js + QuantumWow
                                adapter; simulated | real-BYO-key)
```

Data flow for a sealed run: circuit built by methods (sugar already
decomposed) → `collapse_receipt` mints a LINK cell (circuit identity,
baseline version, shots) → one BIND cell per gate, each hashing the previous
cell's id → the wrapper seeds the global RNG, calls stock `simulate(...,
get='memory')`, restores the RNG → one EFFECT cell per shot outcome, each
naming the seed → receipt JSON. `verify()` walks the chain recomputing every
fnv1a-64 id and, given the circuit, re-executes the whole run and compares
cell-id lists. The simulator never knows the ledger exists.

## Invariants

1. **Nine executable ops, no more, no fewer.** Enforced by
   `tests/test_cell_mapping.py` (parses the CELL-MAPPING op table and
   compares to the `simulate()` dispatch). A silent op addition is a
   semantics change and must fail the suite.
2. **Sugar never reaches a ledger.** `tools/collapse_ledger.py` raises
   `ValueError` on y/z/ry in `qc.data` (they are impossible via the builder
   methods, so their presence means a hand-built chain).
3. **Sealed means re-executable.** `verify()` on a sealed receipt must
   reproduce every cell id from the circuit + seed + shots + noise; any
   divergence is a named failure, never a silent pass. Unsealed receipts are
   labeled `EFFECT/UNSEALED` and refuse re-execution
   (`unsealed_not_reexecutable`).
4. **The baseline is pinned.** `receipts/import-baseline.json` holds sha256
   per tracked file; `tests/test_import_baseline.py` and
   `tools/import_manifest.py --check` (exit 1, named report) plus the
   pre-push hook and CI seal-check enforce regeneration. The manifest never
   hashes itself (documented self-digest fixed-point exclusion).
5. **Immutability of sealed receipts.** Experiment receipts are append-only
   history; amendments live in AUDIT.md prose (e.g. the canonical-home
   note), not in edited receipts.
6. **The engine is unmodified.** Receipts record micromoth.py's sha256
   (`bbd10ac2…`, matching the baseline manifest); the receipt lane observes
   the simulator through its public surface and the global RNG only.

## Failure modes & blast radius

- **Manifest drift (present today):** tracked files added/edited without
  re-seal → the pin and `--check` fail loudly with the exact rows. Blast
  radius: one test; no runtime path consults the manifest. Remedy: regenerate
  and commit.
- **Unseeded sampling:** two runs of the same circuit legitimately differ.
  Contained by the design: unseeded results cannot be sealed; the
  cell-mapping tripwire fails if anyone auto-seeds silently.
- **Guard seam in the measure check:** the "no gates after measure" assert
  only arms for `('m', j, j)`; a measure to a different clbit does not arm
  it, so a post-measure gate could pass unnoticed (code-read; no dedicated
  pin). Blast radius: potentially wrong counts in an edge-case circuit;
  mitigation is convention (`measure(q,q)` / `measure_all()`), and a pin
  would be a welcome addition.
- **Statevector blowup:** 2^n amplitude pairs in Python lists; ~n=25+ is
  impractical (memory) — fails with MemoryError, contained by user scope.
- **Receipt tamper:** any byte flipped in a receipt → `id_mismatch@i` or
  `chain_break@i` naming the first violated row; the exp pins re-derive
  chains so tampered seals trip RED in CI.
- **quantum-wow real mode:** network failure, CORS block, missing scope, or
  extractor zero-byte outcome all degrade to simulated with
  `degraded: true` + `error`; the widget surfaces it. No key is ever stored
  or logged by the adapter.

## Performance & cost envelope

- Simulated cost is O(2^n) per gate layer with pure-Python constant factors;
  the pinned Bell suite (255 tests) runs in ~0.7 s wall on the workspace
  checkout (measured this wave). The collapse-ledger self-check (21 cells)
  is instantaneous.
- The selfplay battery was budgeted at 25 min for 60 rounds
  (experiments/selfplay/PIN.md); its report is sealed in SUMMARY.md
  (58/60 caught, 0.97; canaries 12/12; harness crashes 0).
- No compute services, no workers, no cloud: everything is local CPU.
  Free-tier posture is trivially perfect — $0 external spend is recorded
  across the receipt series.
- Estimate (not receipted): simulating n=20 costs ~1M amplitude pairs ≈
  tens of MB of Python objects and seconds per gate pass; n=25+ is beyond
  the design envelope.

## Operations

- **Local run:** the four commands in ONBOARDING.md are the entire ops
  surface (simulator smoke, pin suite, receipt self-check, drift check).
- **CI:** `.github/workflows/build.yml` came from the upstream import
  (RECORDED in AUDIT.md); a `seal.yml` workflow plus
  `tools/hooks/pre-push` (install via `tools/install_hooks.sh`) guard the
  manifest. Note: `seal.yml` is one of the four files the manifest's seal
  does not yet cover — the standing RED.
- **Credentials model:** none required. The only credential-shaped surface
  is the BYO Moth Quantum key for quantum-wow real mode, supplied at runtime
  (`setApiKey` / server-side `keyProvider`), never committed, never logged
  by the adapter. Env var names only (e.g. a server would inject
  MOTH_QUANTUM_KEY from its own secrets store).
- **Journal:** fleet work happens under Task IDs in
  SuperInstance/superinstance-lab → worklog.md; grep 'MicroMoth-quilt'.

## Design decisions & why

1. **Fork upstream instead of wrapping Qiskit.** The value is a ~289-line
   readable template with nine ops; Qiskit's surface cannot be receipted
   op-by-op by a stranger. Tradeoff: no tensor networks, no GPU, no
   transpilation — accepted, since the lane studies honesty and search
   dynamics, not scale.
2. **Seed plumbing instead of changing `simulate()`.** The CELL-MAPPING
   design named the determinism hole; `tools/collapse_ledger.py` plumbs a
   seed through the documented global-RNG seam and restores state, keeping
   micromoth.py byte-identical to its sealed sha256. Tradeoff: the wrapper
   must be delegated to a future native-seed `simulate()` (pinned as
   `test_plumbing_documented`) — but the baseline never moves under a lane
   that promised not to move it.
3. **Receipts for collapse, not for state.** Collapse is an event, not a
   state, so EFFECT cells are per-shot outcomes; VIEWs (counts/statevector)
   are recorded as which view was taken. Tradeoff: receipts can be long
   (one cell per shot); FORGET is specced as the erasure unit.
4. **Doc-first with executable pins.** CELL-MAPPING was sealed as DESIGN
   with tests that parse the doc before any implementation existed; the
   sibling repo `quilt-qcells` later implemented the same premise inside the
   quilt engine (1418 rows, 16/16 replay-verified — wave 49). This repo
   coordinates rather than duplicates (README "sibling-port gate").
5. **The unsealed/SEALED split.** Rather than banning unseeded runs, the
   ledger marks them `EFFECT/UNSEALED` (seed: null). Tradeoff: two receipt
   statuses to understand; gain: no honest observation is ever discarded,
   and none is laundered.
6. **Self-governing provenance.** The declared upstream `moth-quantum/
   MicroMoth` returned 404 at import, so AUDIT.md's sealed baseline is the
   authority and every claim is tagged VERIFIED or RECORDED. Tradeoff: the
   fork cannot diff against a live parent; gain: provenance that survives
   upstream disappearance (which then actually happened).
