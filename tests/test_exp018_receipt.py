"""Pins for receipts/exp018-hard-root-autopsy.json (qcells lab exp018).

exp018 is the HARD-ROOT AUTOPSY: hard roots 29/31/37 resist
champion-local skeleton and reach arms (exp014 0/3 frozen) but crossed
under the exp016 archive regime (3/3 at the same seeds). Question:
did the winning move class (2q gate touching wire 2, pre-registered
from exp016's actual hard-root champions) ever get DRAWN in the
unaided birth cloud, and if so could selection SEE it? Reach problem
vs fitness/witness problem, read as a difference against control
root 13 under identical instrumentation.

Sealed outcome: FITNESS DESERT AT THE BIRTH CLOUD, not a reach
problem. The winning class was drawn 13-17x per hard root (all via
replace; the equivalence pin surfaced that the harness's
indel-insert pool is hard-wired 2-wire and can never touch wire 2),
but every hard-root cloud child sat at train=0.0 AND verify=0.0 for
all 12 gens — INCLUDING wire-2-entangled birth champions (r37 opens
with a structural superset of exp016's r37 winner and still pays
zero). The freeze is UPSTREAM of selection. exp016's archive crossing
therefore unlocked FITNESS ASSEMBLY (multi-parent mixing), consistent
with exp015 ELITISM-ARTIFACT. The desert is ROOT-SPECIFIC: control
r13 shows signal from gen 0 under the same draw counts.

Integrity pins are load-bearing: results-style receipt — sealed
artifacts are runner + results.json + telemetry jsonl, sha256 table
must match byte-for-byte or the seal is void.

The guard pin is load-bearing: control telemetry reproduces exp001's
champion at verify 1.0 (8 rows, seed-7 canonical lane), recorded
BEFORE results were written.

Cross-receipt pins anchor on MERGED receipts only (exp012 PR #17,
exp013 PR #18); the exp014/exp015/exp016/exp017 comparators are
embedded constants with named provenance (PRs #19/#21/#22/#23
Casey-gated at seal time).

Run: python3 -m unittest tests.test_exp018_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp018-hard-root-autopsy.json"
ARTIFACTS = HERE / "receipts" / "exp018-hard-root-autopsy"
EXP001_RECEIPT = HERE / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE / "receipts" / "exp005-ghz-balance.json"
EXP012_RECEIPT = HERE / "receipts" / "exp012-root-replication.json"
EXP013_RECEIPT = HERE / "receipts" / "exp013-curriculum.json"

HARD_ROOTS = (29, 31, 37)
CONTROL_ROOTS = (13,)
BAR = 0.45
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]
# exp016 archive-hybrid comparator, embedded provenance (receipt
# commit fba4ec7, PR #22 Casey-gated at seal time — constants, not
# files-on-main). Winning-move-class signatures pre-registered
# from these champions.
EXP016_CROSSINGS = {29: {"gen": 4, "win2": ("swap", "cx")},
                    31: {"gen": 7, "win2": ("swap", "crx")},
                    37: {"gen": 3, "win2": ("cx",)}}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_telemetry(name: str):
    return [json.loads(l) for l in
            (ARTIFACTS / name).read_text().splitlines()]


class TestExp018Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "results", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp018-hard-root-autopsy")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"]["hard_roots"], list(HARD_ROOTS))
        self.assertEqual(receipt["seeds"]["control_roots"],
                         list(CONTROL_ROOTS))
        self.assertEqual({receipt["seeds"][k] for k in ("train", "verify",
                                                        "shots")},
                         {101, 202, 512})
        self.assertIn("FITNESS DESERT AT THE BIRTH CLOUD", receipt["title"])
        self.assertIn("UPSTREAM of selection", receipt["results"]["verdict"])

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
        # any outcome; the win2 signature is pre-registered from the
        # exp016 champions with provenance
        results = json.loads((ARTIFACTS / "exp018.results.json")
                             .read_text())
        pin = results["pre_run_pin"]
        self.assertIn("REACH PROBLEM", pin)
        self.assertIn("WITNESS/FITNESS PROBLEM", pin)
        self.assertIn("SLOPE-TRAP AT SCALE", pin)
        self.assertIn("fba4ec7", results["win2_signature_source"])
        self.assertIn("Casey-gated", results["win2_signature_source"])
        receipt = json.loads(RECEIPT.read_text())
        self.assertTrue(receipt["results"]["verdict"]
                        .startswith("FITNESS DESERT AT THE BIRTH CLOUD"))

    def test_winning_class_drawn_but_every_child_zero(self):
        # load-bearing desert pin: the winning move class was DRAWN
        # 13-17x per hard root (all via replace — the harness's
        # insert pool is 2-wire hard-wired), yet EVERY cloud child on
        # every hard root sat at train=0.0 AND verify=0.0 for all 12
        # gens — 0 child-sims produced any balanced target mass
        results = json.loads((ARTIFACTS / "exp018.results.json")
                             .read_text())
        for root in HARD_ROOTS:
            run = next(r for r in results["runs"] if r["root_seed"] == root)
            self.assertTrue(run["hard_class"])
            drawn = run["win2_drawn_total"]
            self.assertGreaterEqual(drawn, 13)
            self.assertLessEqual(drawn, 17)
            self.assertEqual(set(run["win2_drawn_by_class"]), {"replace"},
                             "insert is 2-wire hard-wired: every win2 "
                             "draw must flow through replace")
            rows = load_telemetry(f"exp018.telemetry.r{root}.jsonl")
            self.assertEqual(len(rows), 12)
            self.assertEqual([r["gen"] for r in rows], list(range(12)))
            n_children = sum(len(r["cloud"]) for r in rows)
            self.assertEqual(n_children, 15 * 12,
                             "cloud = 15 new children per gen; the "
                             "champion is the 16th pop slot")
            zeros = sum(1 for r in rows for c in r["cloud"]
                        if c["train_p"] == 0.0 and c["verify_p"] == 0.0)
            self.assertEqual(zeros, n_children,
                             f"r{root}: {n_children - zeros} children "
                             "scored above zero — desert refuted")
            present = sum(1 for r in rows for c in r["cloud"]
                          if c["win2_present"])
            self.assertEqual(present, run["win2_children_total"])
            self.assertEqual(run["max_cloud_verify"], 0.0)
            self.assertEqual(run["max_win2_child_verify"], 0.0)

    def test_birth_champion_superset_still_pays_zero(self):
        # the sharpest pin: r37's BIRTH champion opens
        # cx(2,0)+swap(2,1)+swap(1,0) — wire-2 entangled, a structural
        # superset of exp016's r37 winner ([h(0),cx(0,2),cx(0,1)]'s
        # entangling core) — and still pays 0.0 at both seeds. The
        # desert is at birth, not in selection.
        results = json.loads((ARTIFACTS / "exp018.results.json")
                             .read_text())
        r37 = next(r for r in results["runs"] if r["root_seed"] == 37)
        self.assertTrue(r37["birth_champion_win2"])
        birth_gates = {g[0] for g in r37["birth_champion"]}
        self.assertIn("cx", birth_gates)
        self.assertIn("swap", birth_gates)
        wires = {g[i] for g in r37["birth_champion"] if len(g) >= 3
                 for i in (1, 2)}
        self.assertIn(2, wires)
        rows = load_telemetry("exp018.telemetry.r37.jsonl")
        self.assertEqual(rows[0]["curve"]["genome"], r37["birth_champion"])
        self.assertEqual(rows[0]["curve"]["verify_p"], 0.0)
        self.assertEqual(rows[0]["curve"]["train_p"], 0.0)

    def test_promotion_on_flat_landscape_is_tie_noise(self):
        # r31/r37's champions BECAME win2 — but only via 0.0 >= 0.0
        # tie promotion: no win2 child ever scored above zero, and
        # r29 never promoted one at all. Selection promoted a class
        # it could not see.
        results = json.loads((ARTIFACTS / "exp018.results.json")
                             .read_text())
        receipt = json.loads(RECEIPT.read_text())
        table = receipt["results"]["crossing_table"]
        for root in (31, 37):
            row = table[f"r{root}"]
            self.assertTrue(row["promotion_is_tie_noise"])
            self.assertTrue(row["win2_ever_promoted"])
            self.assertEqual(row["max_win2_child_verify"], 0.0)
        r29 = table["r29"]
        self.assertFalse(r29["win2_ever_promoted"])
        self.assertFalse(r29["final_champion_win2"])

    def test_desert_is_root_specific_control_signals_from_gen0(self):
        # difference read per ROOT-LOTTERY: control r13 under the
        # SAME instrumentation draws the winning class the same number
        # of times (14, all replace) but shows signal from gen 0 —
        # the desert is a property of the root's birth cloud, not the
        # lane or the harness
        receipt = json.loads(RECEIPT.read_text())
        control = receipt["results"]["crossing_table"]["r13.control"]
        self.assertEqual(control["win2_drawn_total"], 14)
        self.assertEqual(set(control["win2_drawn_by_class"]), {"replace"})
        self.assertFalse(control["frozen_12_gens"])
        self.assertTrue(control["signal_from_gen0"])
        rows = load_telemetry("exp018.telemetry.r13.jsonl")
        gen0 = rows[0]
        self.assertGreater(gen0["stat"]["cloud_max_train"], 0.0)
        self.assertGreater(gen0["stat"]["win2_max_train"], 0.0)
        self.assertAlmostEqual(control["max_cloud_verify"], 0.2422,
                               places=4)

    def test_guard_reproduces_exp001_at_canonical_root7(self):
        # control telemetry is the in-harness default-lane run,
        # recorded before results: 8 rows ending on exp001's champion
        # at verify 1.0
        rows = load_telemetry("exp018.telemetry.control.jsonl")
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]["curve"]["genome"], EXP001_CHAMPION)
        self.assertEqual(rows[-1]["curve"]["verify_p"], 1.0)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_mutate_equivalence_and_harness_quirk_named(self):
        # 800/800 rng-stream equivalence is load-bearing evidence the
        # post-hoc per-child verify did not perturb the search
        # stream; the pin must also name the harness quirk it
        # surfaced (insert pool hard-wired 2-wire)
        results = json.loads((ARTIFACTS / "exp018.results.json")
                             .read_text())
        pin = results["mutate_equivalence_pin"]
        self.assertIn("800/800", pin)
        self.assertIn("0 failures", pin)
        self.assertIn("hard-wired 2-wire", pin)
        self.assertTrue(results["guard_exp001_reproduced"])

    def test_freeze_and_doctrine_anchors_merged(self):
        # exp005's freeze remains the illuminated law; doctrine anchors
        # are MERGED receipts at seal time: exp012 ROOT-LOTTERY governs
        # the per-root difference read, exp013 names the 0.2422
        # partial-plateau class (r13 control's ceiling here)
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)
        exp012 = json.loads(EXP012_RECEIPT.read_text())
        self.assertIn("root-lottery", exp012["title"].lower())
        exp013 = json.loads(EXP013_RECEIPT.read_text())
        self.assertIn("wrong scale", exp013["title"])
        receipt = json.loads(RECEIPT.read_text())
        self.assertEqual(receipt["seeds"]["shots"], 512)

    def test_honest_limits_name_desert_and_provenance(self):
        # load-bearing honesty: post-hoc verify method, the 2-wire
        # quirk as harness limitation, tie-noise warning, and the
        # Casey-gated provenance of every embedded comparator
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("POST-HOC", limits)
        self.assertIn("800/800", limits)
        self.assertIn("hard-wired 2-wire", limits)
        self.assertIn("tie-noise", limits)
        self.assertIn("ROOT-SPECIFIC", limits)
        self.assertIn("NOT merged at seal time", limits)
        self.assertIn("fba4ec7", limits)


if __name__ == "__main__":
    unittest.main()
