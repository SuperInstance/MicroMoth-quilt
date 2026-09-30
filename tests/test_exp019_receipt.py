"""Pins for receipts/exp019-archive-assembly.json (qcells lab exp019).

exp019 is the ARCHIVE-ASSEMBLY MECHANISM READ: the genealogy of the
exp016 hard-root crossing (29/31/37), reconstructed offline from the
sealed exp016 per-generation a1 archive snapshots (MERGED PR #22,
commit e128e92). exp018 read the unaided side - FITNESS DESERT AT THE
BIRTH CLOUD, freeze upstream of selection - and INTERPRETED the hybrid
crossing as fitness assembly via multi-parent mixing. This receipt
pins that interpretation as a tested mechanism read, per root.

Sealed outcome: FITNESS ASSEMBLY REFINED, not refuted.
  Pre-registered verdicts (strict train-inferiority discard test):
    29 HILL-CLIMB, 31 MIXED, 37 HILL-CLIMB.
  The pre-registered test is BLIND under the exp018 desert's train
  ties (0.0 and 0.2559 are ubiquitous), named pre-run in the design
  pin. POST-HOC tie-aware read (per-ancestor gen-max context):
    31 RETENTION-ASSEMBLY - the crossing route rides through three
      zero-train ancestors (r31-hybrid-2/23/39) with train STRICTLY
      below their birth-gen archive max; two of them carry gates the
      final crossing needs (swap(0,2), x(0)). Only archive cell
      retention keeps them; champion-local would have dropped them.
    29 + 37 TIE-BAND-DIVERSITY - every chain ancestor sat at its
      gen's train max under ties; champion-local keeps the INCUMBENT
      on ties and never crosses between tied elites, while the
      archive samples parents uniformly across all occupied cells
      (empirical comparator: exp014 champion-local 0/3 on hard roots
      at the same seeds).
  The archive is load-bearing on all three hard roots: via retention
  where fitness inferiority is strict, via uniform parent-cell
  sampling where the desert ties.

Integrity pins are load-bearing: results-style receipt - sealed
artifacts are runner + results.json + control telemetry jsonl, sha256
table must match byte-for-byte or the seal is void.

The guard pin is load-bearing: control telemetry reproduces exp001's
champion (canonical seed-7 lane) and was recorded BEFORE results were
written.

Cross-receipt pins anchor on MERGED receipts only (exp012 PR #17,
exp013 PR #18, exp016 PR #22 whose telemetry this receipt reads);
exp014/exp015/exp017/exp018 comparators are embedded constants with
named provenance (PRs Casey-gated at seal time).

FAIL-first: this module is absent on main - the suite trips on the
import/ discovery of a missing receipt on pristine main.

Run: python3 -m unittest tests.test_exp019_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp019-archive-assembly.json"
ARTIFACTS = HERE / "receipts" / "exp019-archive-assembly"
EXP001_RECEIPT = HERE / "receipts" / "exp001-bias-search.json"
EXP016_RECEIPT = HERE / "receipts" / "exp016-hybrid.json"
EXP014_RESULTS = (HERE / "receipts" / "exp014-skeleton-multiroot"
                  / "exp014.results.json")

BAR = 0.45
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]


def load_receipt():
    return json.loads(RECEIPT.read_text())


def load_telemetry(name):
    rows = []
    with open(ARTIFACTS / name, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class TestExp019Receipt(unittest.TestCase):
    """Pins for the exp019 archive-assembly mechanism read."""

    def test_seal_schema(self):
        receipt = load_receipt()
        self.assertEqual(receipt["schema"],
                         "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["success_threshold_verify_balance"], BAR)
        self.assertTrue(receipt["engine"]["no_new_evo_runs"])
        self.assertEqual(receipt["seeds"]["roots"], [29, 31, 37])

    def test_artifact_integrity(self):
        receipt = load_receipt()
        names = ["exp019_archive_assembly_genealogy.py",
                 "exp019.results.json",
                 "exp019.telemetry.control.jsonl"]
        for name in names:
            digest = hashlib.sha256(
                (ARTIFACTS / name).read_bytes()).hexdigest()
            self.assertEqual(receipt["integrity"][name], digest,
                             f"artifact {name} tampered - seal void")
        self.assertEqual(sorted(receipt["artifacts"]),
                         sorted(f"receipts/exp019-archive-assembly/{n}"
                                for n in names))

    def test_guard_control_reproduces_exp001(self):
        # guard recorded BEFORE results: control telemetry's final
        # curve genome is the canonical exp001 champion, and exp001's
        # own receipt agrees.
        rows = load_telemetry("exp019.telemetry.control.jsonl")
        self.assertTrue(rows)
        self.assertTrue(rows[-1]["promoted"])
        self.assertEqual(rows[-1]["genome"], EXP001_CHAMPION)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)
        self.assertTrue(load_receipt()["results"]["guard"]
                        ["exp001_reproduces"])

    def test_crossing_identity_all_three_hard_roots(self):
        # earliest verify>=0.45 elite per root, from the sealed
        # exp016 telemetry; born gens 4/7/3, all at 0.4824/0.498.
        roots = load_receipt()["results"]["roots"]
        expected = {"29": (4, 0.4824), "31": (7, 0.4824),
                    "37": (3, 0.4824)}
        for root, (gen, verify) in expected.items():
            cross = roots[root]["crossing"]
            self.assertEqual(cross["born_gen"], gen, root)
            self.assertAlmostEqual(cross["verify"], verify, places=4,
                                   msg=root)
            self.assertAlmostEqual(cross["train"], 0.498, places=4,
                                   msg=root)
            self.assertGreaterEqual(cross["verify"], BAR)

    def test_no_strict_ancestor_crossed(self):
        # condition (a) pre-registered: the crossing is not one
        # lineage's smooth climb - no strict ancestor at bar on any
        # hard root.
        roots = load_receipt()["results"]["roots"]
        for root in ("29", "31", "37"):
            self.assertEqual(roots[root]["ancestor_at_bar_count"], 0,
                             root)

    def test_preregistered_verdicts_stand(self):
        # the pre-registered strict-inferiority verdicts are sealed
        # as-is; the tie-blindness is documented, not corrected away.
        receipt = load_receipt()
        self.assertEqual(receipt["results"]["headline_verdicts_pre_registered"],
                         {"29": "HILL-CLIMB", "31": "MIXED",
                          "37": "HILL-CLIMB"})

    def test_post_hoc_tie_aware_reads(self):
        receipt = load_receipt()
        self.assertEqual(
            receipt["results"]["headline_post_hoc_tie_aware"],
            {"29": "TIE-BAND-DIVERSITY", "31": "RETENTION-ASSEMBLY",
             "37": "TIE-BAND-DIVERSITY"})

    def test_r31_retention_assembly_gate_level(self):
        # r31: the crossing route rides through ancestors with train
        # STRICTLY below their birth-gen archive max (0.0 vs 0.2559)
        # - archive retention is load-bearing at the gate level; the
        # carriers include the decisive wire-2 gates.
        roots = load_receipt()["results"]["roots"]
        rows = roots["31"]["post_hoc_tie_aware"]["rows"]
        strict = [r for r in rows[1:] if r["strictly_discarded"]]
        self.assertEqual(len(strict), 2, rows)
        for r in strict:
            self.assertEqual(r["train"], 0.0)
            self.assertEqual(r["gen_max_train"], 0.2559)
        carriers = roots["31"]["champion_discarded_carriers"]
        carried = {tuple(g) for c in carriers for g in c["carried_gates"]}
        self.assertIn(("swap", 0, 2), carried)
        self.assertIn(("x", 0), carried)

    def test_tie_band_diversity_rows_r29_r37(self):
        # 29 + 37: every chain ancestor at gen train-max (ties);
        # champion-local keeps the incumbent on ties, the archive
        # samples uniformly across tied cells - parent DIVERSITY is
        # the load-bearing difference, not retention.
        roots = load_receipt()["results"]["roots"]
        for root in ("29", "37"):
            rows = roots[root]["post_hoc_tie_aware"]["rows"]
            self.assertTrue(len(rows) > 1, root)
            for r in rows[1:]:
                self.assertTrue(r["tie_band"], (root, r))
                self.assertFalse(r["strictly_discarded"], (root, r))

    def test_r37_direct_skeleton_mutation(self):
        # r37 chain: one ancestor (the birth skeleton) - the crossing
        # is a single move away from the seed; the archive's role is
        # purely which parents get sampled, never retention.
        roots = load_receipt()["results"]["roots"]
        self.assertEqual(roots["37"]["chain_length_ancestors"], 1)
        self.assertEqual(roots["37"]["crossing"]["genome"],
                         [["h", 0], ["cx", 0, 2], ["cx", 0, 1]])

    def test_exp016_anchor_merged_crosses_hard_roots(self):
        # the telemetry under read is the MERGED exp016 receipt on
        # main: hybrid crossed 29/31/37 (6/8), champion-local 0/3
        # on the hard class per the exp014 comparator.
        exp016 = json.loads(EXP016_RECEIPT.read_text())
        self.assertEqual(exp016["status"], "SEALED")
        for root in (29, 31, 37):
            key = f"r{root}.hybrid"
            self.assertTrue(
                exp016["results"]["crossing_table"][key]["crossed"], key)
        exp014 = json.loads(EXP014_RESULTS.read_text())
        crosses = {str(r) for r in exp014.get("skeleton_crosses", [])}
        hard = {"29", "31", "37"}
        self.assertFalse(hard & crosses,
                         "exp014 comparator must show 0 hard-root "
                         "champion-local crosses")

    def test_doctrine_read_refined_not_refuted(self):
        receipt = load_receipt()
        self.assertIn("REFINED", receipt["results"]["doctrine_read"])
        self.assertIn("not refuted", receipt["results"]["doctrine_read"])


if __name__ == "__main__":
    unittest.main()
