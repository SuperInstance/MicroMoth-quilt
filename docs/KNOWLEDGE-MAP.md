# MicroMoth-quilt — Knowledge Map
> The index of indexes. Everything deeper, with one line each.

## In this repo

- `micromoth.py` — the entire framework (289 lines, stdlib only): QuantumCircuit builder + dense statevector `simulate()`; the receipt lane's sealed subject.
- `AUDIT.md` — the import-baseline audit: provenance (upstream 404 → self-governing), seal-time checks, per-receipt summaries exp001–exp007, canonical-home amendment (2026-09-30).
- `receipts/import-baseline.json` — sha256 per tracked file at seal; regenerable via tools; never hand-edit.
- `receipts/exp001..exp022` — 22 sealed experiment receipts (`micromoth-quilt/exp-receipt@v1`); exp012–exp022 have subdirectories with `*.telemetry.*.jsonl`, `*.results.json`, and the generating `*.py` kept beside the outputs.
- `tools/import_manifest.py` — manifest builder/checker (`--check` exits 1 with a named drift report; excludes itself by name and records the exclusion).
- `tools/collapse_ledger.py` — seed-plumbed collapse receipts: LINK + BIND + EFFECT cells, fnv1a-64 chain, `verify()` with live re-execution; self-check entry point.
- `tools/selfplay.py` — exp015 bug-injection instrument (temp-copy mutation only, delta-based catching, 12 shapes).
- `tools/install_hooks.sh`, `tools/hooks/pre-push` — pre-push manifest guard (one of the 4 files currently unsealed).
- `tests/` — 24 pin files: import baseline, cell mapping (doc≡dispatch), collapse ledger, one pin file per experiment receipt (test_exp001…test_exp022), grader blindspots, widening pins, lab-home citation.
- `experiments/selfplay/` — PIN.md (pre-registration, honest-negative policy), SHAPES.md (mutation vocabulary), SUMMARY.md (58/60 caught, 0.97; canaries 12/12), `rounds/` (61 JSON round receipts).
- `quantum-wow/` — `micromoth.js` (zero-dependency ES-module port; adds a `crz` extension), `quantum-wow.js` (QuantumWow: quantumSeed/quantumCoin/quantumField/setApiKey/mountWidget; simulated vs real-BYO-key with honest degradation), `index.html` (click-and-play demo).
- `versions/` — upstream ports: Python/ (template + tutorial), Lua/ (PICO-8), Arduino/, Csharp/ (with built test binaries), JavaScript/; `versions/update_required/` holds legacy MicroQiskit ports (Godot, Ruby, Kotlin, C++, Racket, Processing, Dart) not yet upgraded.
- `docs/` (pre-existing) — Sphinx skeleton: `index.rst`, `micropython.rst`, `lua.rst`, `conf.py`, `requirements.txt`; plus the fleet's `CELL-MAPPING.md`.
- `LICENSE` — Apache 2.0 (Moth Quantum 2024 / IBM 2023 headers preserved in sources).

## Pre-existing docs (before the wave-69 docs layer)

- `README.md` — the two-identity statement (MicroMoth + quilt receipt lane), addition table, try-it block; upstream README preserved verbatim below, including the quantum-wow section and the CORS / NIST-extractor honesty notes.
- `AUDIT.md` — the audit receipt described above (provenance + experiment summaries).
- `docs/CELL-MAPPING.md` — TWO stacked layers: (1) the DESIGN receipt (op table, five-opcode mapping, re-execution contract, honest limits); (2) an appended probed design note (program vs executable arity, VIEW purity probe, the determinism hole with live probe numbers, the x·x TICK nuance, proposed cell kinds, smallest-first build, executable pins).
- `docs/index.rst` + `micropython.rst` + `lua.rst` + `conf.py` + `requirements.txt` — upstream Sphinx docs pointing at readthedocs.
- `experiments/selfplay/{PIN,SHAPES,SUMMARY}.md` — the selfplay instrument's pre-registration, shape vocabulary, and sealed report.
- `versions/*/README.md` / `MicroMothArduino.md` / `MicroMothCSharp.md` / `micromothJS.md` — per-port install guides.
- Wave-69 additions (this layer): `docs/ONBOARDING.md`, `docs/USER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/ENGINEERING-NOTES.md`, `docs/CTO-BRIEF.md`, `docs/KNOWLEDGE-MAP.md`, and the Documentation section appended to `README.md`.

## In the fleet

- `SuperInstance/quilt-qcells` — sibling/downstream: implemented the CELL-MAPPING premise as a working plugin over the quilt engine (wraps a micromoth.QuantumCircuit, fnv1a-64 chain, conformance P1–P4). This repo coordinates rather than duplicates (README "sibling-port gate"); it vendors a byte-identical `micromoth.py` (sha256 bbd10ac2…).
- `SuperInstance/micrograd-quilt` — downstream/labs host: its `labs/qcells` tree is the canonical, addressable home of the experiment lab (AUDIT.md amendment, RECORDED 2026-09-30); exp018–exp022 mirrored there as receipt PRs #5–#7.
- `SuperInstance/moth-research` — sibling (docs-only): offline HTML exhibits of the Moth Quantum API (coin-toss-v1, qpixl-v1, graph-v1 engines) that quantum-wow's real mode calls.
- `SuperInstance/AI-Writings` — upstream canon: `algebra.md` defines the five opcodes BIND/LINK/EFFECT/VIEW/TICK (+ adopted FORGET/PROOF/WORLD) and the fnv1a-64 conventions; CELL-MAPPING cites it by blob sha.
- `SuperInstance/git-agent` — precedent: `quilt_emit` (git-agent#1) is the ledger-emitter pattern CELL-MAPPING names as `micromoth_emit`'s ancestor.
- `SuperInstance/quilt-gpu-lab` — precedent: receipt-manifest sealing doctrine (quilt-gpu-lab#2).
- `SuperInstance/quilt` — the reactive cell runtime whose cells/ledgers idiom this repo borrows; `quilt-organ-workers`, `jev-quilt` — same receipt/judge family (context only).

## In the journal

SuperInstance/superinstance-lab → worklog.md, grep 'MicroMoth-quilt' (and 'micromoth'):

- Line ~187 (early wave): moth-quantum research — MicroMoth/quantum-audio clones; API found and live-probed (coin-toss-v1, qpixl-v1, graph-v1).
- Lines ~636–638 (wave 49): the CELL-MAPPING design read; `quilt-qcells` built fresh against it (vendored micromoth.py byte-identical, upstream 5eb1619).
- Line ~657 (wave 49): deep-read — "CELL-MAPPING.md is a DESIGN receipt explicitly awaiting implementation".
- Lines ~1194–1201 (wave 66, task 66-e family): decomposition lane studied and smoked this repo — pytest "19 passed, 1 FAILED" on the three receipt pin files; manifest drift named as the honest negative; verdict "MicroMoth-quilt PARTIAL 19/20 (manifest-drift pin failing loudly — honest negative)"; six decomposition JSONs written to download/decomposition-atlas/parts/labs/.
- Line ~1426 (wave 69): remote census — MicroMoth-quilt observed +29 ahead-only (others pushing).
- Task IDs visible in those entries: wave-49-a (jepa keeper) / 49-c (qcells subagent) context; the labs-decomposition task (line 1185) and substrate task (line 1207) cite this repo as part of the labs family. The repo's own PR series (#3 CELL-MAPPING, #4 wrapper, #30 seal-pin lane) is referenced from AUDIT.md and SUMMARY.md.

## Receipts of record

- `receipts/import-baseline.json` — proves what was imported: sha256 per tracked file at seal (AUDIT: baseline commit 491e8819e681…, 260 tracked files at seal; README's table says 267 — counts drift as files were added; the checker's live numbers this wave: sealed=498, tracked=502, unsealed=4, drifted=0).
- `receipts/exp001-bias-search.json` — first experiment: champion-seeded search toward |01⟩ (8 gens × pop 16, train/verify split), 13 witness rows, PROOF head `7417f8a8ad75a2aa`, replay OK.
- `receipts/exp002-parsimony-sweep.json` — parsimony penalty sweep (λ 0.00/0.02/0.05): both pressure arms collapse to the len-1 champion [x(0)] at verify 1.0; PROOF head `c5e9be966abaf0db`.
- `receipts/exp003-mutation-ablation.json` / `exp004-jitter-drop.json` — ablation arms on identical named seeds; replace-only crosses earlier; policy "drop jitter" adopted (gen 2 vs gen 4); PROOF heads `ade3dc62f7e589e9`, `7bffc7144b684ccb`.
- `receipts/exp005-ghz-balance.json` (FROZEN at balance 0.000 for 12 gens) and `exp006-ghz-seeded.json` (lane A crosses via a non-canonical crx route; "seed CHOICE beats seed FITNESS" — Finding 4 born here; PROOF heads `eaba19fd5cc1c15e`, `bfe7bd25cd7b6f79`).
- `receipts/exp007-bell-balance.json` — H1 refuted for the balance witness (home turf freezes at ~0.23; only the zero-fitness skeleton crosses); PROOF head `a62029c424a2f0fe`.
- `receipts/exp022-desert-break.json` — latest sealed: TRAIN-VISIBLE crossing on every r31 crossing stream; retention-assembly is the only no-break mechanism (title carries the verdict).
- `experiments/selfplay/rounds/round-000-baseline.json` … `round-060.json` + `SUMMARY.md` — the instrument's own receipts: 58/60 caught (0.97), canaries 12/12, 0 harness crashes.
- `tests/test_exp001..022_receipt.py` — the pins that keep every receipt above challengable forever (chain re-derivation + live re-execution + tamper trip).

## How to search further

```bash
# All experiment receipts and their verdicts:
grep -l '"status": "SEALED"' receipts/*.json
grep -h '"title"' receipts/exp0*.json | head -30

# Every place the fleet algebra opcodes appear:
grep -rn "BIND\|EFFECT\|TICK" docs/CELL-MAPPING.md tools/collapse_ledger.py | head -40

# The determinism hole, everywhere it is named:
grep -rn "seed" docs/CELL-MAPPING.md tools/collapse_ledger.py AUDIT.md | head -30

# Which pins guard which claim:
grep -rn "def test" tests/ | head -60

# Journal history:
grep -n "MicroMoth-quilt" /home/z/my-project/worklog.md
grep -n "quilt-qcells"   /home/z/my-project/worklog.md   # the sibling that executed this repo's design
```
