# MicroMoth-quilt — Developer Guide

## Code layout

The paths that matter, file by file:

| Path | What it is |
|---|---|
| `micromoth.py` | The whole framework (289 lines, stdlib only): `QuantumCircuit` + `simulate()`. The canonical template the ports are built from. |
| `receipts/import-baseline.json` | The sealed import baseline: sha256 per tracked file, self-exclusion recorded. Regenerate with `tools/import_manifest.py`; never hand-edit. |
| `AUDIT.md` | The audit receipt: provenance (upstream 404'd → self-governing), live checks at seal, per-receipt summaries for exp001–exp007, canonical-home amendment. |
| `docs/CELL-MAPPING.md` | DESIGN receipt (two stacked layers): op inventory, five-opcode mapping, determinism hole, x·x nuance, executable pins list. |
| `tools/import_manifest.py` | Manifest builder/checker: sha256 per `git ls-files` entry, excludes itself by name, `--check` mode exits 1 with a named drift report. |
| `tools/collapse_ledger.py` | Seed-plumbing receipt tool: `circuit_cells`, `collapse_receipt`, `verify`, fnv1a-64 chaining, SEALED vs EFFECT/UNSEALED policy. |
| `tools/selfplay.py` | exp015 bug-injection instrument (12 mutation shapes against `tests/`, delta-based catching, temp-copy only). |
| `tools/build_exp016_receipt.py` | One-shot sealer for `receipts/exp016-hybrid.json` (results-kind receipt): rebuilds it from the sealed artifacts in `receipts/exp016-hybrid/` with a byte-for-byte sha256 integrity table. |
| `tests/` | 28 pin files: `test_import_baseline.py`, `test_cell_mapping.py`, `test_collapse_ledger.py`, `test_exp001..022_receipt.py` (one per receipt), `test_grader_blindspots.py`, `test_widening_pins.py`, `test_lab_home_citation.py`. |
| `receipts/` | exp001–exp022 sealed receipts (`micromoth-quilt/exp-receipt@v1`); larger experiments have subdirectories with `*.telemetry.*.jsonl`, `*.results.json`, and the generating `*.py` script kept next to the outputs. |
| `experiments/selfplay/` | PIN.md (pre-registration), SHAPES.md (mutation vocabulary), SUMMARY.md (catch-rate report), `rounds/` (61 per-round receipts). |
| `quantum-wow/` | `micromoth.js` (faithful ES-module JS port) + `quantum-wow.js` (QuantumWow adapter, widget) + `index.html` demo. |
| `versions/` | Upstream ports: `Python/`, `Lua/`, `Arduino/`, `Csharp/`, `JavaScript/`, plus `update_required/` (legacy MicroQiskit ports awaiting upgrade). The receipt lane targets only the root `micromoth.py` template. |
| `docs/index.rst`, `docs/micropython.rst`, `docs/lua.rst`, `docs/conf.py` | Pre-existing Sphinx docs skeleton from upstream (readthedocs). |

## Core concepts

Named as the code and receipts name them:

1. **Program arity vs executable arity.** `QuantumCircuit.data` holds the
   *program* (sugar already decomposed: `ry`/`z`/`t`/`y` expand at append
   time). `simulate()`'s dispatch recognizes exactly nine *executable* ops:
   `init, m, x, h, rx, rz, cx, crx, swap`. `tests/test_cell_mapping.py` pins
   both lists — adding a tenth op turns the suite RED.
2. **The simulator core.** A dense statevector `k` of `2**n` complex pairs
   `[re, im]`. Three inner helpers do all the math: `superpose` (Hadamard
   pairs: `(x±y)/sqrt(2)`), `turn` (rx-style rotation by theta/2),
   `phaseturn` (rz-style phase e^{∓iθ/2}). Single-qubit gates walk
   bit-pair indices (`b0`, `b0+2**j`); two-qubit gates walk the four
   b00/b01/b10/b11 indices for sorted (low, high) control/target.
3. **Measurement as record-then-sample.** During the gate pass, `'m'` only
   records `outputnum_clbitsap[clbit] = qubit` (no collapse — the state is
   untouched). After the gate pass, probabilities are computed
   (`re²+im²`), the optional noise model mixes flip probabilities per qubit,
   and shots are sampled by cumulative walk over one `random.random()` draw
   per shot. Output bitstring = n-bit index remapped through the measure map
   into m clbits (big-endian; unmeasured clbits stay '0').
4. **The cell ledger (CELL-MAPPING).** One circuit IS a hash chain:
   LINK boundary cell (circuit + version + shots) → one BIND cell per gate →
   EFFECT cells per seeded collapse shot. Opcodes from the fleet algebra:
   BIND (assert a cell), LINK (prev-chain), EFFECT (collapse/noise events),
   VIEW (counts/statevector views), TICK (qubit-disjoint depth layers),
   adopted FORGET (receipted erasure) and PROOF (statevector witness).
   Hash = fnv1a-64 (offset `0xCBF29CE484222325`, prime `0x100000001B3`)
   over canonical JSON (`sort_keys=True, separators=(",",":")`), genesis
   prev `0x0000000000000000`.
5. **Sealed vs unsealed.** A receipt with an int seed is `EFFECT/SEALED`
   (re-executable byte for byte); `seed=None` mints `EFFECT/UNSEALED`,
   honestly marked, never laundered into sealed. `verify()` re-derives every
   cell id, checks prev-chain integrity with named failures
   (`id_mismatch@i`, `chain_break@i`), and — given a circuit — re-executes
   and compares full cell-id lists (`replay_divergence`).
6. **Receipts and pins.** Every claim in `receipts/` is load-bearing: a
   matching `tests/test_expNNN_receipt.py` re-derives the fnv1a-64 chain
   in-repo, re-executes sealed champions, and trips on tamper. The doctrine:
   claims ride on receipts; pins make receipts immortal.

## How to extend

### Add a gate (the full checklist, because the pins fight back)

1. Add the method to `QuantumCircuit` in `micromoth.py`. If the gate is
   expressible by existing primitives, make it sugar (decompose in the
   method, like `ry` does). Only add to `simulate()`'s dispatch if it is
   truly primitive.
2. Update `docs/CELL-MAPPING.md` op table — `tests/test_cell_mapping.py`
   parses the doc's op inventory and compares it to the dispatch, so a
   code change without a doc change fails the suite (this is intentional).
3. Extend `tools/collapse_ledger.py::_gate_args` with the new op's canonical
   args (else receipts raise on circuits using it).
4. Add a receipt pin: build the gate in a tiny circuit, seal a receipt,
   re-derive the chain in a test (copy the pattern from
   `tests/test_exp001_receipt.py`).
5. Run `python3 tools/import_manifest.py` and commit the refreshed manifest
   WITH your change (the pre-push hook and CI seal-check enforce this).

### Add an experiment receipt

1. Write the pre-registration first (see `experiments/selfplay/PIN.md` for
   the shape: claim under test, confirming/refuting conditions, budget,
   honest-negative policy).
2. Run against named seeds (the series' convention: root 7 / train 101 /
   verify 202, 512 shots; later experiments salt streams as
   `31000+k`).
3. Seal `receipts/expNNN-name.json` with schema
   `micromoth-quilt/exp-receipt@v1`: engine sha256, seeds block, results,
   witness-ledger rows, PROOF head, and an honest-limits block.
4. Add `tests/test_expNNN_receipt.py` that re-derives the chain and
   re-executes the sealed champion. FAIL-first evidence belongs in the PR
   body (tamper something in memory, show the pin RED, restore).

### Extend the JS side

`quantum-wow/micromoth.js` mirrors the Python template gate-for-gate (plus a
`crz` extension wired in like `crx`). Keep the two files
(`micromoth.js` + `quantum-wow.js`) self-contained as a pair; the public
contract is `quantumSeed/quantumCoin/quantumField/setApiKey/mountWidget`
with `{mode, degraded, error}` honesty fields on every result. Never read a
key from config; keys arrive at runtime via `setApiKey` or a server-side
`keyProvider`.

## Testing

```bash
python3 -m pytest tests/ -q
```

Green means: 256 passing pins — import baseline structure, cell-mapping
doc≡dispatch equivalence, collapse-ledger id re-derivation + tamper naming +
live re-execution, all 22 experiment receipts, grader-blindspot and widening
pins. The import-baseline pin (`test_import_baseline.py::
test_manifest_exists_and_matches`) was a pre-existing, by-design RED until
the wave-69 re-seal; it re-trips RED on any drift, and
`python3 tools/import_manifest.py --check` names the rows. The
selfplay instrument's own report (experiments/selfplay/SUMMARY.md) was
generated from a baseline of "255 passed / 1 pre-existing failed" — treat
any other delta as yours.

The cell-mapping suite includes a deliberate tripwire: eight unseeded runs
must NOT all agree (it goes RED if someone "fixes" sampling by auto-seeding,
which would silently change honesty semantics). If you make sampling
seedable, plumb it as an explicit argument (the collapse_ledger wrapper is
the pattern) — never auto-seed.

## Conventions

- **Stdlib only** for the Python lane; zero dependencies for the JS lane.
- **Receipt discipline:** nothing unseeded is ever written as a result;
  every WORLD/sampling row names its seed; sealed receipts are immutable
  (corrections become appended amendment notes, as AUDIT.md's closing
  section did).
- **Pins are the memory:** doc changes and code changes that affect pinned
  behavior must update the pin in the same change set.
- **Provenance tags:** VERIFIED (run, dated) vs RECORDED (read from
  metadata) — keep the tags in AUDIT-style notes.
- Commit history is small and receipt-oriented (baseline seal, design
  receipt, wrapper, per-experiment seals); messages name the PR/receipt.

## Gotchas for editors

- Touching `micromoth.py` invalidates the engine sha256 recorded inside
  every sealed receipt (`vendored_sha256 bbd10ac2…`); the receipts are
  immutable, so a changed engine means a NEW baseline seal and new receipts,
  never edited old ones.
- Regenerating the manifest is mandatory with any tree change (new files are
  `unsealed`, edited files are `drifted`); the check output names rows.
- The measure-map dict is last-writer-wins per clbit; changing that behavior
  breaks the crossed-multi-measure receipt (`receipts/ledgers` siblings in
  quilt-qcells pin the same semantics there).
- `tools/selfplay.py` never mutates the working tree (temp-copy only), but
  it shells out to git; it expects a clean checkout semantics for baseline
  deltas.
- Do not reformat `docs/CELL-MAPPING.md`'s two stacked layers — the second
  layer cites probe results (VIEW purity, seeded determinism, x·x) that the
  test pins reference conceptually; splitting or deduping loses the
  provenance.
- Python 2 compatibility is an upstream concern in `versions/`; the receipt
  lane targets Python 3 only.
