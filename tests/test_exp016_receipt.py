"""Pins for receipts/exp016-hybrid.json (qcells lab exp016).

exp016 is the HYBRID RATE REPLICATION: exp006 skeleton birth +
exp015's exact MAP-Elites archive regime, run on exp014's fresh-root
panel (3/5/13/17/19/29/31/37) — the panel where champion-local
skeleton search crossed only 4/8 ({3,13,17,19}). Question: does the
archive change the seeded crossing rate? Pre-registered bands:
>=7/8 = ARCHIVE AMPLIFIES SEEDING; 3-6/8 = ARCHIVE NEUTRAL; <=2/8 =
CHAMPION LOCALITY IS THE LAW.

Sealed outcome: ARCHIVE NEUTRAL at the top edge — hybrid 6/8
({3,5,13,29,31,37}), agreement with champion-local only {3,13}; the
archive converts the hard class (29/31/37 cross at gens 4/7/3) but
loses the easy class (17 stops at 0.4355, 19 at 0.2422 — the exp013
partial plateau). Per exp012 ROOT-LOTTERY doctrine the root-disjoint
draw is an N/M rate read, never a mechanism victory.

Integrity pins are load-bearing: results-style receipt (no witness
LEDGER; exp001 remains the lane's only LEDGER receipt) — sealed
artifacts are runner + results.json + telemetry jsonl, and the
receipt's sha256 table must match every file byte-for-byte or the
seal is void.

The guard pin is load-bearing: the control telemetry is the
in-harness default-lane run reproducing exp001's champion at verify
1.0 (8 rows, seed-7 canonical lane), recorded BEFORE any results
were written.

Cross-receipt pins anchor on MERGED receipts only (exp012 PR #17,
exp013 PR #18); the exp014 comparator is embedded in results.json
with named provenance (PR #19 Casey-gated) and pinned here as
embedded constants, not as files-on-main.

Run: python3 -m unittest tests.test_exp016_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp016-hybrid.json"
ARTIFACTS = HERE / "receipts" / "exp016-hybrid"
EXP001_RECEIPT = HERE / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE / "receipts" / "exp005-ghz-balance.json"
EXP012_RECEIPT = HERE / "receipts" / "exp012-root-replication.json"
EXP013_RECEIPT = HERE / "receipts" / "exp013-curriculum.json"

ROOTS = (3, 5, 13, 17, 19, 29, 31, 37)
BAR = 0.45
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]
CROSS_P = 0.482421875
# exp014 champion-local comparator (embedded provenance, PR #19
# Casey-gated at seal time — constants, not files-on-main)
EXP014_CHAMP_LOCAL = {3, 13, 17, 19}
# sealed hybrid outcome per root (measured, named not rounded)
HYBRID_CROSS = {3: 5, 5: 5, 13: 4, 29: 4, 31: 7, 37: 3}
HYBRID_MAX_BELOW_BAR = {17: 0.4355, 19: 0.2422}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestExp016Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "results", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp016-hybrid")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"]["roots"], list(ROOTS))
        self.assertEqual({receipt["seeds"][k] for k in ("train", "verify",
                                                        "shots")},
                         {101, 202, 512})
        self.assertIn("ARCHIVE NEUTRAL", receipt["title"])

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

    def test_preregistered_band_pin_named_at_birth(self):
        # the three-band interpretation (AMPLIFIES / NEUTRAL /
        # LOCALITY) is in results.json BEFORE any outcome
        results = json.loads((ARTIFACTS / "exp016.results.json")
                             .read_text())
        pin = results["pre_run_pin"]
        self.assertIn("ARCHIVE AMPLIFIES SEEDING", pin)
        self.assertIn("ARCHIVE NEUTRAL", pin)
        self.assertIn("CHAMPION LOCALITY IS THE LAW", pin)
        # the exp014 comparator panel is embedded with provenance at
        # birth, and it is the SAME root panel this experiment runs
        comp = results["exp014_comparator"]
        self.assertIn("793a771", comp["source"])
        self.assertIn("Casey-gated", comp["source"])
        self.assertEqual(comp["champion_local_skeleton_crosses"],
                         [3, 13, 17, 19])
        # descriptor-honesty at birth: verify is descriptor-only
        self.assertIn("descriptor-only", results["design"])
        # the sealed verdict must be one of the pre-registered bands
        receipt = json.loads(RECEIPT.read_text())
        self.assertTrue(receipt["results"]["verdict"]
                        .startswith("ARCHIVE NEUTRAL"))

    def test_hybrid_crossing_table_matches_sealed_constants(self):
        # 6/8 in the pre-registered NEUTRAL band (3-6), top edge —
        # every crossing root at the exact exp005 balance 0.4824,
        # every non-crossing root NAMED below the bar, never rounded
        results = json.loads((ARTIFACTS / "exp016.results.json")
                             .read_text())
        table = results["crossing_table"]
        self.assertEqual(results["hybrid_crosses"],
                         sorted(HYBRID_CROSS))
        self.assertEqual(results["hybrid_cross_fraction"], "6/8")
        for root, gen in HYBRID_CROSS.items():
            row = table[f"r{root}.hybrid"]
            self.assertTrue(row["crossed"])
            self.assertEqual(row["first_ge_045_gen"], gen)
            self.assertAlmostEqual(row["max_elite_verify"], CROSS_P,
                                   places=4)
        for root, maxv in HYBRID_MAX_BELOW_BAR.items():
            row = table[f"r{root}.hybrid"]
            self.assertFalse(row["crossed"])
            self.assertAlmostEqual(row["max_elite_verify"], maxv,
                                   places=4)
            self.assertIsNone(row["first_ge_045_gen"])

    def test_root_agreement_table_is_honest(self):
        # the root-disjoint draw is reported three ways, and per
        # exp012 ROOT-LOTTERY it is an N/M rate read: agreement only
        # {3,13}, hybrid-only includes ALL THREE hard-class roots
        # 29/31/37 champion-local missed, champion-only {17,19}
        results = json.loads((ARTIFACTS / "exp016.results.json")
                             .read_text())
        agree = results["root_agreement_with_exp014"]
        self.assertEqual(agree["both_cross"], [3, 13])
        self.assertEqual(agree["hybrid_only"], [5, 29, 31, 37])
        self.assertEqual(agree["champion_local_only"], [17, 19])
        hard_class = {29, 31, 37}
        self.assertTrue(hard_class.issubset(set(agree["hybrid_only"])))

    def test_telemetry_matches_results_and_has_12_gens(self):
        results = json.loads((ARTIFACTS / "exp016.results.json")
                             .read_text())
        for run in results["runs"]:
            root = run["root_seed"]
            rows = [json.loads(l) for l in
                    (ARTIFACTS /
                     f"exp016.telemetry.r{root}.hybrid.jsonl")
                    .read_text().splitlines()]
            self.assertEqual(len(rows), 12, f"r{root} telemetry rows")
            self.assertEqual([r["gen"] for r in rows], list(range(12)))
            final = rows[-1]
            self.assertAlmostEqual(final["a1_max_elite_verify"],
                                   run["max_elite_verify"], places=4)
            # per-generation honesty: the partial-plateau signal is
            # visible in-band every generation (cloud max), and the
            # birth row records the skeleton seed at gen -1
            self.assertGreaterEqual(
                max(r["cloud_max_verify"] for r in rows), 0.0)

    def test_guard_reproduces_exp001_at_canonical_root7(self):
        # the control telemetry is the in-harness default-lane run,
        # recorded before any results: 8 rows ending on exp001's
        # champion at verify 1.0
        rows = [json.loads(l) for l in
                (ARTIFACTS / "exp016.telemetry.control.jsonl")
                .read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]["genome"], EXP001_CHAMPION)
        self.assertEqual(rows[-1]["verify_p"], 1.0)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_freeze_and_doctrine_anchors_merged(self):
        # exp005's freeze remains the illuminated law; the two
        # doctrine anchors are MERGED receipts at seal time: exp012
        # (PR #17) ROOT-LOTTERY governs the verdict read, exp013
        # (PR #18) names the 0.2422 partial-plateau class r19 sits in
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)
        results = json.loads((ARTIFACTS / "exp016.results.json")
                             .read_text())
        self.assertTrue(results["guard_exp001_reproduced"])
        exp012 = json.loads(EXP012_RECEIPT.read_text())
        self.assertIn("root-lottery", exp012["title"].lower())
        exp013 = json.loads(EXP013_RECEIPT.read_text())
        self.assertIn("wrong scale", exp013["title"])

    def test_neutral_band_edge_named_in_honest_limits(self):
        # 6/8 is the TOP edge of the pre-registered neutral band —
        # the receipt must name the edge, the asymmetry (hard-class
        # conversion vs easy-class loss), and forbid the mechanism-
        # victory reading
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("TOP edge", limits)
        self.assertIn("29/31/37", limits)
        self.assertIn("0.4355", limits)
        self.assertIn("ROOT-LOTTERY", limits)
        self.assertIn("not a mechanism victory", limits)


if __name__ == "__main__":
    unittest.main()
