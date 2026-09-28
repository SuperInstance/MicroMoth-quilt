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
