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

`receipts/exp004-jitter-drop.json` — qcells-lab exp004 (Finding 2
policy follow-up): the exp003 ablation finding is promoted to POLICY.
Same search, same named seeds (root 7, train 101, verify 202, 512
shots), one change — the jitter branch is dropped entirely
(`mutate_classed restrict=("replace","indel")`), zero harness change,
reusing exp003's ablation seam as the policy knob. Verdict: control
still reproduces exp001 byte-for-byte; both arms reach the identical
champion [h(1),h(1),x(0)] at held-out verify 1.000, but the
jitter-dropped policy crosses at gen 2 vs the control's gen 4 — same
honesty, twice the convergence; jitter was only burning candidate
draws in the mixed neighborhood. 13 witness-ledger rows for the sealed
policy champion (genome + measure surface), PROOF head
`7bffc7144b684ccb`, replay OK. `tests/test_exp004_receipt.py` adds 9
pins: chain re-derived in-repo, seed-in-WORLD-row doctrine, executable
champion (512/512 verify shots in `01`), control==exp001 seal,
no-jitter crosses earlier on the same champion, cross-receipt
champion agreement with the exp003 ablation seal, honest-limit scope
pins, in-memory tamper trip. Honest limits inside the receipt
(single root seed — the multi-root crossing-rate doctrine post-dates
this experiment; product-state target; policy scoped to discrete-gate
search — continuous-only lanes cannot leave the start genome without
the gate classes they were never given).

`receipts/exp005-ghz-balance.json` — qcells-lab exp005 (the Finding-3
precursor): the engine leaves its 2-qubit home target for n=3 balanced
GHZ {|000>,|111>}. Anti-laundering pin recorded before the lab run: a
bare counts-set target is satisfied by deterministic product |000>, so
fitness is the balance witness min(c000,c111)/shots; the prelude
measured hand GHZ balance 0.4824 vs product 0.000. Same named seeds as
exp001-exp004 (root 7, train 101, verify 202, 512 shots), same exp004
jitter-dropped replace/indel policy. Verdict: FROZEN — the exp001
control guard reproduces byte-identical inside this harness, while the
n=3 lane sits at train/verify balance 0.000 for all 12 generations;
the sealed champion [h(1),cx(2,0),x(2)] lands only in {100,110} on
the named verify seed. 15 witness-ledger rows (program + measure
surface), PROOF head `eaba19fd5cc1c15e`, replay OK. `tests/test_exp005_receipt.py`
adds 9 pins: chain re-derived in-repo, seed-in-WORLD-row doctrine,
executable frozen champion with live WORLD histogram, control-guard
flag, live prelude re-derivation, frozen-curve pins, honest-limit
scope, in-memory tamper trip. Honest limits inside the receipt
(single root seed — the later multi-root crossing-rate doctrine
post-dates this experiment; champion-local mutator; n=3 GHZ balance
witness, not a universal no-entanglement claim).

`receipts/exp006-ghz-seeded.json` — qcells-lab exp006 (Finding 3
candidate (a)): exp005 froze the unseeded engine on n=3 balanced GHZ;
the ranked first fix was a GHZ-prefix seeded restart — loadCoev
doctrine (seeds around champs, pong-quilt #73) applied at birth. Two
seeded lanes on identical named seeds (root 7, train 101, verify 202,
512 shots) and the exp004 jitter-dropped replace/indel policy. Lane A
seed [h(0),cx(0,1)] — bare skeleton, birth balance 0.0, one indel from
correlation. Lane B seed [h(0),cx(0,1),h(2)] — partial entangler,
birth balance 0.2422, the anti-laundering seed-choice control.
Verdict: lane A CROSSES — verify balance 0.4824 by gen 2 via a
non-canonical crx route [h(0),crx(pi,0,2),cx(0,1)] the unaided search
never found; lane B TRAPS — never sampled above its 0.2422 birth
fitness in 8 gens x pop 16 = 120 draws, champion == seed genome.
Seed CHOICE beats seed FITNESS (Finding 4 born here). The exp001
control guard re-ran in-harness byte-identical. 15 witness-ledger
rows (expanded champion + measure surface), PROOF head
`bfe7bd25cd7b6f79`, replay OK. `tests/test_exp006_receipt.py` adds
10 pins: chain re-derived in-repo, seed-in-WORLD-row doctrine,
executable sealed champion with live WORLD histogram (crx angle
expansion pinned against genome-circuit semantics), control-guard
flag, live seed-choice prelude re-derivation, lane A crosses / lane B
traps curve pins, honest-limit scope, in-memory tamper trip. Honest
limits inside the receipt (single root seed — the later multi-root
crossing-rate doctrine post-dates this experiment; the seeded lanes
answer SEEDING, exp005's unaided freeze stands; lane B's trap is a
120-draw negative search result, not a universal claim).
