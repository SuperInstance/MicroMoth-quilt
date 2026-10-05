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
python3 -m pip install pytest        # only for the test suite
python3 -m pytest tests/ -q
# -> 256 passed — green since the wave-69 re-seal; the import-baseline pin is
#    the tripwire (drift turns it RED again, see gotchas).

# 3. The seeded collapse-receipt tool (self-check, prints a receipt):
python3 tools/collapse_ledger.py
# -> {"cells":21,"sealed":true,"shots":16,"status":"EFFECT/SEALED","verify":{"ok":true,"why":"ok"}}

# 4. The manifest drift checker:
python3 tools/import_manifest.py --check
# -> exit 0: SEAL OK: sealed=508 tracked=508 unsealed=0 drifted=0 orphaned=0
#    (any unsealed/drifted file is named, with the re-seal remedy).
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

- **The import-baseline pin is a tripwire, not a broken test.** It was the
  suite's one standing RED (files added post-seal, manifest not re-sealed)
  until the wave-69 close ran `python3 tools/import_manifest.py` — the
  declared re-embed — and the suite went green. Any tree change without a
  re-seal turns it RED again (new tracked file = unsealed, edited file =
  drifted) and names the remedy (`python3 tools/import_manifest.py`,
  committed with the change). Do not hand-edit
  `receipts/import-baseline.json`.
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
- **A typo'd `get=` value falls back silently.** `simulate(get=…)` does no
  enum validation: an unrecognized value is treated as the default and you
  get sampled counts with no error (verified by the wave-69 drill). Check
  your `get` spelling before trusting a histogram.
- **The upstream docstring lies about the t-gate**: `micromoth.py:108` says
  the t-gate "Applies a z gate" — it actually applies `rz(pi/4)`. The
  docstring is wrong (upstream verbatim); the decomposition is right.
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

- Keep the import manifest sealed: after any intentional tree change, re-run
  `python3 tools/import_manifest.py` and commit the manifest WITH the change
  (the wave-69 close re-sealed the docs layer + README drift).
- PROOF statevector witness cell at a TICK — the next cell in the ledger
  (README roadmap). `tools/collapse_ledger.py` does LINK/BIND/EFFECT; PROOF
  (rounded-amplitude sha256 witness) is specced in CELL-MAPPING.md and
  implemented in the sibling `quilt-qcells`, not here.
- The quilt-native plugin lane coordinates with `quilt-qcells` (wave 49)
  rather than duplicating it — the "sibling-port gate" in the README.
- Selfplay next probes (experiments/selfplay/SUMMARY.md): crx-only-path and
  memory-output-ordering bug shapes are thinly pinned; boundary_offbyone
  variant 2 targets arithmetic, not semantics.

---

## Fleet seed (2026-10-06 handoff) — momentum, vision, roadmaps, mesh

> Additive section for follow-up agents; the sections above are the
> zero-shot mechanics. Mesh context: `SuperInstance/fleet-seeds` →
> `docs/handoff-2026-10-06/ORG-MESH.md`.

### Momentum since the doc above froze

- **CELL-MAPPING is fully merged** (PRs #33–#42): FORGET shot-erasure,
  `cell_receipts` JSONL artifact driver (write → verify-by-replay, refused-
  not-faked on header/count/tamper divergence), the `simulate()` injected-RNG
  seam (the global-`random` determinism hole, named then fixed, seeded
  byte-identical), seeded plumbing adoption (concurrency-pinned), and VIEW
  cells (per the CELL-MAPPING "we looked" clause — counts seeded, statevector
  sha256-pinned, never inlined: *ledger cheap, VIEW not*). Suite 352/352 at
  merge; import-baseline pin is the tripwire.
- **The IonQ ladder climbed rungs 1–2** (both on main via #44):
  rung-1 `tools/rung1_preflight.py` — forbidden-sum discriminator, P(01)+P(10)
  = 0.49815 measured vs 0.50 coherent / 0.0 classical (200k shots, ~500σ
  teeth); rung-2 `tools/rung2_preflight.py` — sin² bridge exact at π,
  additivity 0.7494 vs 0.75 coherent / 0.50 accumulator flagged, cancellation
  exact 0.0. Both sim-only pre-flights with honest limits documented.
- **Manifest discipline is load-bearing:** every file sealed, reseal counts
  pinned (524→527 across the lane), fresh-audit caught a real stale-manifest
  ship once (the reseal-left-unstaged bug) — the tool earns its keep here.
- **No credentials needed for anything in this repo** — the quantum work is
  simulator-native. (The MothQuantum hardware token was revoked 2026-10-06;
  it was never needed here.)

### Vision

Feature-poverty as a virtue: nine executable operations you can read in an
afternoon, wrapped in the fleet's receipt discipline so that *a quantum
circuit is a hash-chained ledger* — every gate a BIND cell, every measurement
a sealed collapse event, every view a VIEW cell. The quantum lane is the
sharpest possible test of "no receipt, no claim," because a sampled outcome
is an event, not a state: an unseeded histogram is a claim nobody can
re-verify. This repo refuses to launder that.

### Roadmaps (several directions)

1. **IonQ rung-3 (4–7q wsum/decoherence)** — the spend rung. Gated on
   hardware credits AND the EFFECT/HARDWARE doctrine (rungs 1–2 sim
   preflights PASS; do not attempt the hardware rung without Casey's go).
2. **Extraction-style publishing** (mirror `coev`): the cell-ledger layer
   could stand alone as `micromoth-ledger` for anyone's MicroQiskit fork.
3. **More opcode adoption** — WORLD/TIME are named in the mapping doc; the
   mid-circuit measurement seam (#41) is the natural next adopter.
4. **QRC adjacency** — MothQuantum's public `qrc-train-v2` / `labyrinth-v1`
   engines are conceptually adjacent (quantum-graph structures → receipts);
   cite-not-build until a fresh key exists.
5. **Champion-seeded search expansion** — exp001–exp022 seeded gate-search
   receipts; new targets (larger entangled classes) are one seeded run each.

### How it meshes

- **One algebra, many substrates:** the five-opcode idiom (BIND/LINK/EFFECT/
  VIEW/TICK + FORGET/PROOF/WORLD) is the same idiom as the fleet WAL
  (fleet-witness), quilt-jev-toolkit organs, and quilt-in-git ticks. A gate
  application and a WAL row are the same act in different materials.
- **fresh-audit originated in quilt-tools#45** and is run on every PR here;
  receipts committed on-branch.
- **Referral graph:** edges to/from this lane land in `quilt-tools`; the
  graph counts this repo in its 25-repo view.
- Org state: `fleet-seeds` → `docs/handoff-2026-10-06/HANDOFF.md`.
