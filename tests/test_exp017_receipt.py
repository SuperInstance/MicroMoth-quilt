"""Pins for receipts/exp017-easy-class-dilution.json (qcells lab exp017).

exp017 is the EASY-CLASS DILUTION probe: exp014 champion-local search
crossed roots {3,13,17,19} (4/8) while the exp016 uniform archive
hybrid crossed {3,5,13,29,31,37} (6/8) with agreement only {3,13} —
roots 17/19 crossed champion-local but NOT under the archive regime.
Question: archive DILUTION of the seed signal, or root-lottery draw?
Design: uniform arm (exp016 verbatim) + champion-rescue arm (every 2nd
emission parents from the single fittest A1 elite) on roots 13/17/19,
with birth-skeleton lineage telemetry.

Sealed outcome: EASY CLASS DECOMPOSES + RESCUE IS NOT A RESCUE. The
uniform arm byte-reproduces exp016 (same rng stream: r13 crosses gen 4,
r17 peaks 0.4355, r19 plateaus 0.2422 — a determinism check, NOT new
draws). The rescue arm fails EVERYWHERE, including robust root 13 (max
0.4355, below bar where the uniform archive crossed it twice). Archive
dilution is REFUTED as the 17/19 explanation; champion locality is not
bolt-on recoverable inside a coverage-driven archive.

Integrity pins are load-bearing: results-style receipt — sealed
artifacts are runner + results.json + telemetry jsonl, sha256 table
must match byte-for-byte or the seal is void.

The guard pin is load-bearing: control telemetry reproduces exp001's
champion at verify 1.0 (8 rows, seed-7 canonical lane), recorded
BEFORE results were written.

Cross-receipt pins anchor on MERGED receipts only (exp012 PR #17,
exp013 PR #18); the exp014/exp016 comparators are embedded constants
with named provenance (PRs #19/#22 Casey-gated at seal time).

Run: python3 -m unittest tests.test_exp017_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp017-easy-class-dilution.json"
ARTIFACTS = HERE / "receipts" / "exp017-easy-class-dilution"
EXP001_RECEIPT = HERE / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE / "receipts" / "exp005-ghz-balance.json"
EXP012_RECEIPT = HERE / "receipts" / "exp012-root-replication.json"
EXP013_RECEIPT = HERE / "receipts" / "exp013-curriculum.json"

ROOTS = (13, 17, 19)
BAR = 0.45
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]
CROSS_P = 0.482421875
# exp016 uniform-hybrid comparator, embedded provenance (receipt
# commit fba4ec7, PR #22 Casey-gated at seal time — constants, not
# files-on-main)
EXP016_UNIFORM = {13: {"crossed": True, "gen": 4, "max": CROSS_P},
                  17: {"crossed": False, "gen": None, "max": 0.4355},
                  19: {"crossed": False, "gen": None, "max": 0.2422}}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestExp017Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "results", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp017-easy-class-dilution")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"]["roots"], list(ROOTS))
        self.assertEqual({receipt["seeds"][k] for k in ("train", "verify",
                                                        "shots")},
                         {101, 202, 512})
        self.assertIn("EASY CLASS DECOMPOSES", receipt["title"])
        self.assertIn("RESCUE IS NOT A RESCUE", receipt["title"])

    def test_engine_pin_matches_import_baseline(self):
        receipt = json.loads(RECEIPT.read_text())
        baseline = json.loads(
            (HERE / "receipts" / "import-baseline.json").read_text())
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

    def test_preregistered_interpretations_named_at_birth(self):
        # all three pinned interpretations are in results.json BEFORE
        # any outcome; the exp016 comparator is embedded with
        # provenance; the sealed verdict is the pinned third branch
        results = json.loads((ARTIFACTS / "exp017.results.json")
                             .read_text())
        pin = results["pre_run_pin"]
        self.assertIn("DILUTION VERIFIED", pin)
        self.assertIn("LOTTERY DRAW", pin)
        self.assertIn("EASY CLASS DECOMPOSES", pin)
        comp = results["exp016_comparator"]
        self.assertIn("fba4ec7", comp["source"])
        self.assertIn("Casey-gated", comp["source"])
        receipt = json.loads(RECEIPT.read_text())
        self.assertTrue(receipt["results"]["verdict"]
                        .startswith("EASY CLASS DECOMPOSES"))

    def test_uniform_arm_byte_reproduces_exp016(self):
        # the uniform arm is a DETERMINISTIC replay (same rng stream):
        # r13 crosses gen 4 at the exp005 balance, r17 names 0.4355,
        # r19 names 0.2422 — never rounded, no new draws claimed
        results = json.loads((ARTIFACTS / "exp017.results.json")
                             .read_text())
        table = results["crossing_table"]
        for root, exp in EXP016_UNIFORM.items():
            row = table[f"r{root}.uniform"]
            self.assertEqual(row["crossed"], exp["crossed"])
            self.assertEqual(row["first_ge_045_gen"], exp["gen"])
            self.assertAlmostEqual(row["max_elite_verify"], exp["max"],
                                   places=4)

    def test_rescue_arm_fails_everywhere_incl_robust_root13(self):
        # load-bearing negative: bolting 50% fittest-elite parenting
        # onto the archive regime STOPS root 13 crossing (it crossed
        # under the uniform archive in exp016 AND in this replay) and
        # leaves 17/19 at their below-bar plateaus
        results = json.loads((ARTIFACTS / "exp017.results.json")
                             .read_text())
        table = results["crossing_table"]
        r13 = table["r13.rescue"]
        self.assertFalse(r13["crossed"])
        self.assertAlmostEqual(r13["max_elite_verify"], 0.4355, places=4)
        self.assertIsNone(r13["first_ge_045_gen"])
        self.assertFalse(table["r13.uniform"]["crossed"] is False,
                         "control: uniform arm must still cross r13")
        for root in (17, 19):
            row = table[f"r{root}.rescue"]
            self.assertFalse(row["crossed"])
            self.assertIsNone(row["first_ge_045_gen"])
            self.assertLess(row["max_elite_verify"], BAR)

    def test_lineage_telemetry_present_for_all_runs(self):
        # every run carries birth-skeleton lineage fields per gen
        results = json.loads((ARTIFACTS / "exp017.results.json")
                             .read_text())
        for run in results["runs"]:
            root = run["root_seed"]
            arm = run["arm"]
            rows = [json.loads(l) for l in
                    (ARTIFACTS /
                     f"exp017.telemetry.r{root}.{arm}.jsonl")
                    .read_text().splitlines()]
            self.assertEqual(len(rows), 12, f"r{root}.{arm} rows")
            self.assertEqual([r["gen"] for r in rows], list(range(12)))
            for r in rows:
                self.assertIn("skel_lineages_alive_in_a1", r)
                self.assertIn("skel_children_max_verify", r)
                self.assertIn("cloud_max_verify", r)
            final = rows[-1]
            self.assertEqual(final["skel_lineages_alive_in_a1"],
                             run["skel_lineages_alive_final"])
            # per-gen cloud max can dip below the archive elite late
            # in the run; the run's max_elite_verify must equal the
            # FINAL ARCHATE's best verify, not the final gen's cloud
            archive_max = max(r["verify"] for r in
                              final["a1"].values()) if final["a1"] else 0.0
            self.assertAlmostEqual(archive_max,
                                   run["max_elite_verify"], places=4)

    def test_guard_reproduces_exp001_at_canonical_root7(self):
        # control telemetry is the in-harness default-lane run,
        # recorded before results: 8 rows ending on exp001's champion
        # at verify 1.0 — and it is byte-identical to exp016's guard
        rows = [json.loads(l) for l in
                (ARTIFACTS / "exp017.telemetry.control.jsonl")
                .read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]["genome"], EXP001_CHAMPION)
        self.assertEqual(rows[-1]["verify_p"], 1.0)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_freeze_and_doctrine_anchors_merged(self):
        # exp005's freeze remains the illuminated law; doctrine anchors
        # are MERGED receipts at seal time: exp012 ROOT-LOTTERY governs
        # the rate read, exp013 names the 0.2422 partial-plateau class
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)
        results = json.loads((ARTIFACTS / "exp017.results.json")
                             .read_text())
        self.assertTrue(results["guard_exp001_reproduced"])
        exp012 = json.loads(EXP012_RECEIPT.read_text())
        self.assertIn("root-lottery", exp012["title"].lower())
        exp013 = json.loads(EXP013_RECEIPT.read_text())
        self.assertIn("wrong scale", exp013["title"])

    def test_honest_limits_name_replay_and_refutation(self):
        # load-bearing honesty: the receipt must name the deterministic
        # replay (uniform arm adds no new draws), the rescue refutation
        # (dilution REFUTED, champion locality not bolt-on
        # recoverable), the below-bar named values, and the
        # Casey-gated provenance of both embedded comparators
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("DETERMINISTIC REPLAY", limits)
        self.assertIn("RESCUE IS NOT A RESCUE", limits)
        self.assertIn("REFUTED", limits)
        self.assertIn("0.4355", limits)
        self.assertIn("ROOT-LOTTERY", limits)
        self.assertIn("fba4ec7", limits)
        self.assertIn("NOT merged at seal time", limits)


if __name__ == "__main__":
    unittest.main()
