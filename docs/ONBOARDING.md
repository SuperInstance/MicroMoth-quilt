# MicroMoth-quilt — Agent Onboarding
> Zero-shot entry point. Clone → competent in ~10 minutes.

## Identity (2 sentences)

MicroMoth-quilt is the smallest, most feature-poor quantum computing framework
(a maintained fork of MicroQiskit, ~289 lines of dependency-free Python in
`micromoth.py`) with a SuperInstance fleet lane bolted on top that treats every
quantum circuit as a hash-chained receipt ledger. The feature-poverty is the
design point: nine executable operations, a dense statevector simulator you can
read in an afternoon, and a receipt discipline that makes every run
re-executable and tamper-evident.

## Why it exists (the fleet problem it solves)

The fleet's honesty law is "no receipt, no claim", and a quantum simulator is a
sharp test of it: a sampled measurement outcome is an event, not a state, so an
unseeded histogram is a claim nobody can re-verify. Waves 48–49 built this
lane to answer that: the import was sealed (AUDIT.md + a sha256 manifest),
the circuit-as-ledger design was written op by op (docs/CELL-MAPPING.md: the
five-opcode algebra BIND / LINK / EFFECT / VIEW / TICK, plus adopted
FORGET / PROOF / WORLD), and the determinism hole (simulate() samples with the
global, unseeded `random` module) was named rather than laundered. The lane
then woke fully: 22 sealed experiment receipts (exp001–exp022) run a
champion-seeded gate-search toward entangled targets, each pinned by tests
that re-derive the fnv1a-64 chain and live re-execute the sealed result.

## Verify it works (exact commands)

```bash
git clone https://github.com/SuperInstance/MicroMoth-quilt.git && cd MicroMoth-quilt

# 1. The simulator, no install, stdlib only (Python >= 3.6):
python3 -c "
import micromoth
q = micromoth.QuantumCircuit(2, 2)
q.h(0); q.cx(0, 1)
q.measure(0, 0); q.measure(1, 1)
print(micromoth.simulate(q, shots=256, get='counts'))
"
# -> a Bell histogram, e.g. {'11': 148, '00': 108}. Exact counts vary run to
#    run (unseeded sampling by design); every shot lands in {'00','11'}.

# 2. The pin suite (pytest needed; run from repo root):
python3 -m pytest tests/ -q
# -> 255 passed, 1 failed: tests/test_import_baseline.py manifest drift is a
#    PRE-EXISTING, by-design RED (see gotchas). Everything else green.

# 3. The seeded collapse-receipt tool (self-check, prints a receipt):
python3 tools/collapse_ledger.py
# -> {"cells":21,"sealed":true,"shots":16,"status":"EFFECT/SEALED","verify":{"ok":true,"why":"ok"}}

# 4. The manifest drift checker (currently trips RED on purpose):
python3 tools/import_manifest.py --check
# -> exit 1: sealed=498 tracked=502 unsealed=4 (seal.yml, test_widening_pins.py,
#    pre-push hook, install_hooks.sh), drifted=0; remedy named in output.
```

No external credentials are needed for anything in this repo. The only
network-optional path is `quantum-wow/` "real" mode (BYO Moth Quantum API key
at runtime; never committed; degrades to local simulation on any failure).

## Reading order (paths, not vibes)

1. `README.md` — the two-identity statement (simulator + receipt lane) and the
   addition table; the upstream README below it is preserved verbatim.
2. `micromoth.py` — 289 lines, the whole framework. Read it; that IS the spec.
3. `docs/CELL-MAPPING.md` — the design receipt mapping quantum ops to quilt
   cells, the nine-op inventory, and the determinism hole (two stacked layers).
4. `AUDIT.md` — the import baseline: provenance, what was verified at seal,
   and per-receipt summaries for exp001–exp007.
5. `tools/collapse_ledger.py` — the seed-plumbing wrapper that mints SEALED
   collapse receipts (LINK + BIND chain + per-shot EFFECT cells).
6. `receipts/exp001-bias-search.json` and one later receipt (e.g.
   `receipts/exp022-desert-break.json`) — see what a sealed experiment
   receipt actually carries (schema, seeds, title, PROOF head).
7. `docs/KNOWLEDGE-MAP.md` — the index of everything deeper, including this
   docs layer.

## The things that will bite you (gotchas)

- **One pre-existing RED.** `tests/test_import_baseline.py::test_manifest_
  exists_and_matches` fails on pristine main: four files were added after the
  seal (seal.yml, test_widening_pins.py, tools/hooks/pre-push,
  tools/install_hooks.sh) and the manifest was not re-sealed. The pin is
  working as designed — it fails loudly and names the remedy
  (`python3 tools/import_manifest.py`, committed with the change). Do not
  hand-edit `receipts/import-baseline.json`.
- **Sampling is unseeded by design.** `simulate(get='counts'|'memory')` draws
  from the global `random` module; the same circuit gives different counts on
  every run. This is the documented "determinism hole" (CELL-MAPPING.md).
  Never treat an unseeded histogram as a replayable claim. For replayable
  sampling use `tools/collapse_ledger.py::collapse_receipt(qc, shots, seed)`
  (or seed the global RNG yourself and restore it after).
- **Sugar gates never appear in `qc.data`.** `y`, `z`, `t`, `ry` decompose at
  append time into `rz`/`x`/`rx` (`t` is `rz(pi/4)`, `z` is `rz(pi)`,
  `y` is `rz(pi)+x`, `ry(th)` is `rx(pi/2), rz(th), rx(-pi/2)`). If you
  hand-build `data`, the ledger tools raise on sugar ops by design.
- **The gates-after-measure guard has a seam.** `simulate()` asserts no gate
  acts on a qubit after its measure command, but the guard only arms when the
  measure was `('m', j, j)` — a measure to a *different* clbit
  (`measure(0, 1)`) does not arm it, so a later gate on qubit 0 passes
  silently (code-read; unverified by a dedicated test). Prefer `measure(q,q)`
  or `measure_all()`.
- **`get='probability_dictionary'` (as one preserved README line says) does
  not exist** — the code accepts `'probabilities_dict'` exactly.
- **Measurement remapping is last-writer-wins.** `outputnum_clbitsap` is a
  dict keyed by clbit; two measures into the same clbit keep only the last.
- **Statevector cost is 2^n amplitude pairs.** The ledger is cheap; the VIEW
  is not. Do not "just try" 30 qubits.
- **Receipt provenance path note.** Sealed receipts' directive strings name a
  local workspace path (`workspace/labs/qcells`); the canonical, addressable
  home of the qcells lab is the org repo `SuperInstance/micrograd-quilt`
  (labs/qcells tree). Sealed receipts are immutable; AUDIT.md's closing note
  records this amendment.
- **This workspace's mtimes may be normalized** — anything comparing
  file mtimes (not used by this repo's pins, which are content-sha based) can
  misbehave; the fleet-wide lesson is to prefer content-sha seals.

## Where deeper knowledge lives

- Knowledge map: [docs/KNOWLEDGE-MAP.md](./KNOWLEDGE-MAP.md)
- Fleet journal: SuperInstance/superinstance-lab → worklog.md
  (grep 'MicroMoth-quilt'; the wave-66 decomposition lane recorded the
  smoke verdict "PARTIAL 19/20 — manifest-drift pin failing loudly",
  which matches what you will see running the suite today)
- `receipts/` — the sealed evidence: import-baseline.json (sha256 per tracked
  file) and exp001–exp022 experiment receipts (many with telemetry JSONL
  subdirectories and the generating script next to the results)
- `experiments/selfplay/` — the exp015 bug-injection instrument's
  pre-registration (PIN.md), shape vocabulary (SHAPES.md), summary
  (SUMMARY.md), and 61 per-round receipt JSONs
- `versions/` — the upstream ports (Python, Lua, Arduino, C#, JavaScript) and
  `versions/update_required/` (legacy MicroQiskit ports not yet upgraded)
- `quantum-wow/` — the zero-dependency browser plugin (simulated/real QRNG
  adapter + widget) built on the JS port
- Sibling repos: `SuperInstance/quilt-qcells` (the CELL-MAPPING premise
  implemented inside the quilt engine itself — coordinate, don't duplicate);
  `SuperInstance/micrograd-quilt` (labs/qcells — canonical lab home);
  `SuperInstance/moth-research` (offline exhibits of the Moth Quantum API)

## Current frontier (what is open right now)

- Re-seal the import manifest (4 unsealed tracked files; the checker names
  them). This is the standing RED and the first chore of any new lane.
- PROOF statevector witness cell at a TICK — the next cell in the ledger
  (README roadmap). `tools/collapse_ledger.py` does LINK/BIND/EFFECT; PROOF
  (rounded-amplitude sha256 witness) is specced in CELL-MAPPING.md and
  implemented in the sibling `quilt-qcells`, not here.
- The quilt-native plugin lane coordinates with `quilt-qcells` (wave 49)
  rather than duplicating it — the "sibling-port gate" in the README.
- Selfplay next probes (experiments/selfplay/SUMMARY.md): crx-only-path and
  memory-output-ordering bug shapes are thinly pinned; boundary_offbyone
  variant 2 targets arithmetic, not semantics.
