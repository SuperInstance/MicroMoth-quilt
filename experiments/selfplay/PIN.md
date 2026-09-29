# Pre-registration PIN — exp015/selfplay-d1

Written BEFORE building the instrument. Lane owner: selfplay-d1.
Verbatim from the lane's tasking:

- Claim under test: the qcells batteries catch synthetic bugs matched to their own shape vocabulary at a measurable, shape-dependent rate (C05+C07, prospector card refs).
- Confirming: >=50 injection rounds across >=10 distinct mutation-shape categories; per-round receipts; catch-rate curve by shape; 12 seeded canary bugs with caught-count.
- Refuting: >30% of injected bugs crash the battery harness itself (instrument broken, not batteries).
- Boring: 100% catch on all shapes (batteries trivially overfit) — report it as such if seen.
- Metric+gate: catch_rate per shape = caught/(caught+missed); canary field `canaries_caught/12`; all receipts carry roots [7,11,23] if the battery accepts seeds.
- Budget: 25 min; abort -> report whatever exists with failure_mode.

## Verification deltas recorded up front (honest negatives section, filled during build)

- `qcells/` does NOT exist on any branch of this repo (verified: `git ls-tree -r`
  on main + all lane branches). The battery in residence is `tests/` — 16 test
  files, 144 test cases at baseline. The claim's subject is re-pointed at the
  actual battery; the instrument records this as deviation D1.
- Baseline is NOT green: `tests/test_import_baseline.py::BaselineSealed::
  test_manifest_exists_and_matches` fails on pristine main (import-baseline.json
  digest drift, pre-existing, not caused by this lane). Catch semantics are
  therefore delta-based: a round is CAUGHT iff the failing-test set strictly
  grows relative to the pristine baseline run in the same harness.
