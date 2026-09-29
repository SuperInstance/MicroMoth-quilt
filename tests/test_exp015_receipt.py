"""Pins for receipts/exp015-illumination.json (qcells lab exp015).

exp015 is MAP-ELITES ILLUMINATION OF THE FREEZE: does QD archive
coverage over the exact exp005 unaided lane reveal occupied cells at
held-out verify balance > 0 that single-fitness champion search never
promoted (freeze = elitism artifact), or is coverage empty above 0
(freeze = illumination-invariant engine law)? Two behavior descriptors
(A1: verify_balance_bucket x circuit_length, 36 cells; A2: balance x
verify-counts entropy, 30 cells), fitness = train balance ONLY (verify
is descriptor-only; selection never sees held-out seed 202), emitter =
one-move mutate_classed cloud off uniform A1 parents. Three configs x
roots 7/11/23, 12 gens x pop 16, exact exp005 lane (targets 000/111,
balance, n=3, train101/verify202/shots512, budget 6,
restrict=("replace","indel")).

Pre-registered branch pin (named at birth, not retrofitted):
  (a) occupied verify>0 cells on >=1 unaided root = ELITISM-ARTIFACT
  (b) >0 cells only under seeding = signal manufactured by seeding
  (c) all 9 runs empty above 0 = FREEZE IS ILLUMINATION-INVARIANT

Sealed outcome: ELITISM-ARTIFACT (partial), branch (a). All three
unaided archives hold verify>0 elites (r7 max 0.248, r11 max 0.1309,
r23 max 0.2422) that single-fitness champion search discarded every
generation — the zero-signal claim FAILS. But no config crosses the
0.45 bar without skeleton birth (skeleton 3/3 at 0.4824 gens 10/2/8;
unaided 0/3; transplant 0/3, r7 best 0.4355 below bar) — the CROSSING
claim is selection-regime-invariant. FREEZE verdict refined, not
refuted: illumination moves the unaided ceiling 0 -> 0.248 (the
Finding-4 partial-plateau class of exp013), seeding moves it 0.248 ->
0.4824. Archive-elite transplant (config c) is NOT a third crossing
class.

The integrity pins are load-bearing: results-style receipt (no witness
LEDGER; exp001 remains the lane's only LEDGER receipt) — sealed
artifacts are runner + results.json + telemetry jsonl, and the
receipt's sha256 table must match every file byte-for-byte or the
seal is void.

The guard pin is load-bearing: the control telemetry is the in-harness
default-lane run reproducing exp001's champion at verify 1.0 (8 rows,
seed-7 canonical lane), recorded BEFORE any results were written.

The cross-receipt pins anchor on MERGED receipts only: exp011 (the
ROOT-LOTTERY pre-registration), exp012 (merged PR #17, the doctrine),
exp013 (merged PR #18, the plateau class). exp014 was still
Casey-gated as PR #19 at seal time — named in cross_receipts, but no
pin here depends on exp014 files being on main.

Run: python3 -m unittest tests.test_exp015_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp015-illumination.json"
ARTIFACTS = HERE.parent / "receipts" / "exp015-illumination"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"
EXP011_RECEIPT = HERE.parent / "receipts" / "exp011-nonchampion-parent.json"
EXP012_RECEIPT = HERE.parent / "receipts" / "exp012-root-replication.json"
EXP013_RECEIPT = HERE.parent / "receipts" / "exp013-curriculum.json"

ROOTS = (7, 11, 23)
CONFIGS = ("unaided", "skeleton", "transplant")
BAR = 0.45
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]
CROSS_P = 0.482421875
UNAIDED_MAX = {7: 0.248, 11: 0.1309, 23: 0.2422}
SKELETON_FIRST_CROSS_GEN = {7: 10, 11: 2, 23: 8}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestExp015Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "results", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp015-illumination")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"]["roots"], list(ROOTS))
        self.assertEqual({receipt["seeds"][k] for k in ("train", "verify",
                                                        "shots")},
                         {101, 202, 512})
        self.assertIn("ELITISM-ARTIFACT", receipt["title"])
        self.assertIn("partial", receipt["title"])

    def test_engine_pin_matches_import_baseline(self):
        receipt = json.loads(RECEIPT.read_text())
        baseline = json.loads(
            (HERE.parent / "receipts" / "import-baseline.json")
            .read_text())
        self.assertIn("micromoth.py", baseline["files"])
        self.assertEqual(receipt["engine"]["vendored_sha256"],
                         baseline["files"]["micromoth.py"],
                         "receipt must pin the SAME vendored engine the "
                         "import-baseline manifest seals")

    def test_integrity_table_matches_artifacts_byte_for_byte(self):
        receipt = json.loads(RECEIPT.read_text())
        for name, digest in receipt["integrity"].items():
            self.assertTrue((ARTIFACTS / name).is_file(),
                            f"sealed artifact {name} missing")
            self.assertEqual(sha256_of(ARTIFACTS / name), digest,
                             f"artifact {name} drifted from its seal")
        sealed = set(receipt["integrity"])
        on_disk = {p.name for p in ARTIFACTS.iterdir() if p.is_file()}
        self.assertEqual(sealed, on_disk)

    def test_preregistered_branch_pin_named_at_birth(self):
        # the three-way branch (ELITISM-ARTIFACT / seeding-manufactured /
        # illumination-invariant) is in results.json BEFORE any outcome:
        # the design string + pre_run_pin must carry all three options
        results = json.loads((ARTIFACTS / "exp015.results.json")
                             .read_text())
        pin = results["pre_run_pin"]
        self.assertIn("ELITISM-ARTIFACT", pin)
        self.assertIn("ILLUMINATION-INVARIANT", pin)
        self.assertIn("manufactured by seeding", pin)
        # descriptor-honesty at birth: verify is descriptor-only
        self.assertIn("descriptor-only", results["design"])
        self.assertIn("selection never sees the held-out seed",
                      results["design"])
        # the sealed verdict must be one of the pre-registered branches
        receipt = json.loads(RECEIPT.read_text())
        self.assertTrue(receipt["results"]["verdict"]
                        .startswith("ELITISM-ARTIFACT"))

    def test_unaided_archives_hold_verify_gt0_elites_all_three_roots(self):
        # the zero-signal claim FAILS on every root: occupied verify>0
        # cells exist in the unaided archive, and they sit in the
        # (0, 0.45) band — the Finding-4 partial-plateau class, never
        # the crossing bar
        results = json.loads((ARTIFACTS / "exp015.results.json")
                             .read_text())
        self.assertEqual(results["unaided_gt0_runs"], list(ROOTS))
        for run in results["runs"]:
            if run["config"] != "unaided":
                continue
            root = run["root_seed"]
            self.assertGreater(run["a1_coverage_gt0"], 0,
                               f"root {root} unaided archive empty above 0")
            self.assertGreater(run["max_elite_verify"], 0.0)
            self.assertLess(run["max_elite_verify"], BAR)
            self.assertAlmostEqual(run["max_elite_verify"],
                                   UNAIDED_MAX[root], places=4)
            self.assertFalse(run["crossed"])
            self.assertIsNone(run["first_ge_045_gen"])

    def test_crossing_is_selection_regime_invariant(self):
        # the crossing claim survives the illumination regime change:
        # skeleton birth crosses 3/3 at the exact exp005 balance,
        # unaided 0/3, transplant 0/3 (r7's 0.4355 is NAMED, not rounded
        # up to the bar)
        results = json.loads((ARTIFACTS / "exp015.results.json")
                             .read_text())
        table = results["crossing_table"]
        for root in ROOTS:
            skel = table[f"r{root}.skeleton"]
            self.assertTrue(skel["crossed"])
            self.assertEqual(skel["first_ge_045_gen"],
                             SKELETON_FIRST_CROSS_GEN[root])
            self.assertAlmostEqual(skel["max_elite_verify"], CROSS_P,
                                   places=4)
            self.assertFalse(table[f"r{root}.unaided"]["crossed"])
            tx = table[f"r{root}.transplant"]
            self.assertFalse(tx["crossed"])
        self.assertAlmostEqual(table["r7.transplant"]["max_elite_verify"],
                               0.4355, places=4)

    def test_telemetry_matches_results_and_has_12_gens(self):
        results = json.loads((ARTIFACTS / "exp015.results.json")
                             .read_text())
        for run in results["runs"]:
            root, cfg = run["root_seed"], run["config"]
            rows = [json.loads(l) for l in
                    (ARTIFACTS /
                     f"exp015.telemetry.r{root}.{cfg}.jsonl")
                    .read_text().splitlines()]
            self.assertEqual(len(rows), 12, f"{root}.{cfg} telemetry rows")
            self.assertEqual([r["gen"] for r in rows], list(range(12)))
            final = rows[-1]
            self.assertAlmostEqual(final["a1_max_elite_verify"],
                                   run["max_elite_verify"], places=4)
            # per-generation honesty: the archive's best held-out verify
            # is visible in-band every generation — elites the champion
            # ledger never promoted were alive in the cloud at the time
            if cfg == "unaided":
                gt0_gens = [r["gen"] for r in rows
                            if r["cloud_max_verify"] > 0.0]
                self.assertTrue(gt0_gens,
                                f"root {root} unaided: no generation ever "
                                "saw cloud verify>0 — artifact claim void")

    def test_guard_reproduces_exp001_at_canonical_root7(self):
        # the control telemetry is the in-harness default-lane run,
        # recorded before any results: 8 rows ending on exp001's
        # champion at verify 1.0
        rows = [json.loads(l) for l in
                (ARTIFACTS / "exp015.telemetry.control.jsonl")
                .read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]["genome"], EXP001_CHAMPION)
        self.assertEqual(rows[-1]["verify_p"], 1.0)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_freeze_cross_receipt_still_holds(self):
        # exp005's freeze remains the illuminated law: champion-level
        # held-out balance on the unaided lane is 0.0 there and 0.0 here
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)
        results = json.loads((ARTIFACTS / "exp015.results.json")
                             .read_text())
        self.assertTrue(results["guard_exp001_reproduced"])

    def test_root_lottery_and_plateau_doctrine_anchors_merged(self):
        # the two doctrine anchors are MERGED receipts at seal time:
        # exp012 (PR #17) carries ROOT-LOTTERY as sealed law; exp013
        # (PR #18) names the partial-plateau class this receipt's
        # 0.2422/0.248 maxima belong to; exp011 pre-registered the
        # 1-in-4 rate both inherit
        exp012 = json.loads(EXP012_RECEIPT.read_text())
        self.assertIn("root-lottery", exp012["title"].lower())
        exp013 = json.loads(EXP013_RECEIPT.read_text())
        # exp013's sealed law is the trap-at-wrong-scale doctrine; the
        # ~0.2422/0.248 band exp015's unaided elites sit in IS that class
        self.assertIn("wrong scale", exp013["title"])
        exp011 = json.loads(EXP011_RECEIPT.read_text())
        limits11 = " ".join(exp011["honest_limits"])
        self.assertIn("ROOT-LOTTERY", limits11)
        self.assertIn("1-in-4", limits11)

    def test_transplant_is_not_a_third_crossing_class(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("NOT a third crossing class", limits)
        self.assertIn("0.4355", limits)
        results = json.loads((ARTIFACTS / "exp015.results.json")
                             .read_text())
        for run in results["runs"]:
            if run["config"] == "transplant":
                self.assertEqual(len(run["transplant_events"]), 2)


if __name__ == "__main__":
    unittest.main()
