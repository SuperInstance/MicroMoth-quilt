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
