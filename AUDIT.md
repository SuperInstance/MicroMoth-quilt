# AUDIT — the import baseline (dormant lane, sealed 2026-09-28)

MicroMoth-quilt is a GitHub fork of `moth-quantum/MicroMoth`, imported
while the quilt-native lane sleeps. This note is the audit receipt the
lane reads on day one. Claim tags: **VERIFIED** (run this date),
**RECORDED** (read from repo metadata).

## Provenance

| Field | Value | Tag |
|---|---|---|
| Upstream | `moth-quantum/MicroMoth` | RECORDED (GitHub fork parent) |
| Baseline commit | `491e8819e681…` (repo HEAD at seal time) | VERIFIED (`git rev-parse HEAD`) |
| Tracked files at seal | 260 | VERIFIED (`git ls-files` → manifest) |
| Seal | `receipts/import-baseline.json` (sha256 per file) | VERIFIED (regenerable) |

The seal covers every tracked file except the manifest itself — a
sha256 self-digest is a fixed point no content can satisfy, so the
tool excludes it by name and records the exclusion inside the seal.

## Live checks performed at seal

1. **Import is functional** — a 2-qubit Bell circuit (`h`, `cx`, `measure`)
   run through `micromoth` placed 256/256 shots in `{'00','11'}`; zero
   leakage outside the entangled subspace. VERIFIED. This check is now
   permanent: `tests/test_import_baseline.py` reruns it on every invocation.
2. **CI present** — `.github/workflows/build.yml` from the upstream import.
   RECORDED.
3. **Ports tree intact** — Arduino, Csharp, JavaScript, Lua, Python,
   update_required all present at seal; their digests are in the manifest.
   VERIFIED via the manifest, not by eyeball.

## Doctrine for the sleeping lane

- The manifest answers "what exactly did we import?" — every future
  quilt-native change is a diff against this baseline, and any edit to
  the imported tree that nobody re-sealed trips RED
  (`tests/test_import_baseline.py`), naming regeneration as the remedy.
- Regeneration is the declared re-embed: `python3 tools/import_manifest.py`,
  committed WITH the change. Never hand-edit `receipts/import-baseline.json`.
- When the lane wakes (quilt-native cells wrapping micromoth circuits),
  the first new file should extend `tests/` here — the baseline pins are
  the template.

Sealed by the CCC main session, 2026-09-28 (Asia/Shanghai). FAIL-first
evidence for the pins is in the PR body that introduced this file.

## The lane woke — experiment receipts (2026-09-28)

The lane is no longer sleeping: CELL-MAPPING (#3 merged) and the
seed-plumbing wrapper (#4 merged) let micromoth circuits emit quilt
witness ledgers. The first experiment receipt is sealed at
`receipts/exp001-bias-search.json` — qcells-lab exp001, a
champion-seeded search toward |01⟩ (8 gens × pop 16, train/verify
seed split), 13 witness-ledger rows, PROOF head `7417f8a8ad75a2aa`,
replay OK. `tests/test_exp001_receipt.py` re-derives the fnv1a-64
chain in-repo, pins the seed-in-every-WORLD-row doctrine, and trips
RED on any tamper with the seal. Honest limits ride inside the
receipt (degenerate `h;h` champion; mid-circuit `m` is a sampling
event, never a state mutation). Regeneration doctrine above is
unchanged — experiment receipts are additive, never edits to the
import baseline.

`receipts/exp002-parsimony-sweep.json` — qcells-lab exp002 (Finding 1
follow-up): the exp001 search gains a per-gate parsimony penalty on
the TRAIN selection score only (verify promotion gate untouched),
swept over λ 0.00/0.02/0.05 on identical named seeds (root 7, train
101, verify 202, 512 shots). Control reproduces exp001 byte-for-byte;
both pressure arms collapse to the len-1 champion [x(0)] at verify
1.0. 9 witness-ledger rows for the sealed parsimony champion
(genome + measure surface), PROOF head `c5e9be966abaf0db`, replay OK.
`tests/test_exp002_receipt.py` adds 7 pins: chain re-derived in-repo,
seed-in-WORLD-row doctrine, executable len-1 champion (512/512
verify shots in `01` under the vendored engine), control-arm champion
identical to the exp001 seal, in-memory tamper trip. Honest limits
inside the receipt (all champions are product states — the sweep
seals selection mechanics, not entanglement search; λ resolution
stops at one breakpoint).

`receipts/exp003-mutation-ablation.json` — qcells-lab exp003 (Finding 2
follow-up): the exp001 search gains a `mutate_classed` seam and four
ablation arms run on identical named seeds (root 7, train 101, verify
202, 512 shots): control / replace-only / indel-only / jitter-only. A
non-applicable class is resampled, never silently replaced; a hard
no-move raises MutationDeadlock, recorded as that arm's result.
Verdict: control reproduces exp001 byte-for-byte; replace-only reaches
the identical champion but crosses at gen 1 vs gen 4 (the control
stall was other classes burning draws, not search difficulty);
indel-only never crosses (verify P(01) = 265/512, re-derived live by
the pins); jitter-only deadlocks at gen 0 (no rotation gate in the
seed champion). 13 witness-ledger rows for the sealed ablation
champion (genome + measure surface), PROOF head `ade3dc62f7e589e9`,
replay OK. `tests/test_exp003_receipt.py` adds 9 pins: chain
re-derived in-repo, seed-in-WORLD-row doctrine, executable champion
(512/512 verify shots in `01`), control==exp001 seal, replace crosses
earlier on the same champion, indel non-crossing arm re-derived live,
jitter deadlock recorded-not-worked-around, in-memory tamper trip.
Honest limits inside the receipt (single root seed — the multi-root
crossing-rate doctrine post-dates this experiment; all champions are
product states; the jitter deadlock is birth-genome-specific).
