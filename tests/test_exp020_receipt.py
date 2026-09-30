"""Pins for receipts/exp020-tie-break.json (qcells lab exp020).

exp020 is the TIE-BREAK ABLATION: exp019's archive-assembly mechanism
read assigned roots 29/37 the TIE-BAND-DIVERSITY mechanism (the archive
samples parents uniformly across train-tied elites while champion-local
freezes on the incumbent) — but that read was POST-HOC, never tested
by running. exp020 tests it directly: the exact exp016 champion-local
lane with ONLY the gen-max tie-break rule flipped (ARM-TIESAMPLE:
uniform rng.choice among exact-fitness gen-max ties vs ARM-INCUMBENT:
max() first-wins, exp014 semantics). No archive, no non-champion
retention — tie sampling is the ONLY difference between paired runs.

Sealed outcome: TIE-BAND-DIVERSITY REPLICATED.
  tiesample crossed 2/3 hard roots (29, 37 @0.4824) the incumbent arm
  missed; r31 still out (peaked 0.3027). The incumbent arm reproduced
  exp014's champion-local class live in-arm: 0/3 hard at the 0.2422
  plateau, easy control 13 crossed in both arms (harness sanity).
  exp019's post-hoc tie-aware read upgrades to run-tested mechanism —
  still an N/M rate claim per ROOT-LOTTERY (exp012), not a law.

Integrity pins are load-bearing: results-style receipt - sealed
artifacts are runner + results.json + 8 per-run telemetry jsonl
(2 arms x roots 13/29/31/37); the sha256 table must match byte-for-byte
or the seal is void.

The pre-registered interpretation bands are pinned as sealed text so a
retro-fitted verdict would trip: INCUMBENT must reproduce the exp014
class; TIESAMPLE >=1 hard crossing -> REPLICATED; TIESAMPLE 0/3 ->
TIE SAMPLING ALONE INSUFFICIENT. The sealed verdict must match the
band logic.

Cross-receipt anchors are on MERGED receipts only (exp012 PR #17,
exp014 PR #19, exp016 PR #22, exp018 PR #24); exp019 (PR #25) is
Casey-gated at seal time and is cited from its sealed artifacts with
named provenance - no pin depends on exp019 files being on main.

FAIL-first: this module is absent on main - the suite trips on
discovery of a missing receipt on pristine main.

Run: python3 -m unittest tests.test_exp020_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp020-tie-break.json"
ARTIFACTS = HERE / "receipts" / "exp020-tie-break"
EXP001_RECEIPT = HERE / "receipts" / "exp001-bias-search.json"
RESULTS = ARTIFACTS / "exp020.results.json"

BAR = 0.45
HARD = ("29", "31", "37")
ARTIFACT_NAMES = [
    "exp020.results.json",
    "exp020.telemetry.incumbent.r13.jsonl",
    "exp020.telemetry.incumbent.r29.jsonl",
    "exp020.telemetry.incumbent.r31.jsonl",
    "exp020.telemetry.incumbent.r37.jsonl",
    "exp020.telemetry.tiesample.r13.jsonl",
    "exp020.telemetry.tiesample.r29.jsonl",
    "exp020.telemetry.tiesample.r31.jsonl",
    "exp020.telemetry.tiesample.r37.jsonl",
    "exp020_tie_break_ablation.py",
]


def load_receipt():
    return json.loads(RECEIPT.read_text())


def load_results():
    return json.loads(RESULTS.read_text())


def load_telemetry(name):
    rows = []
    with open(ARTIFACTS / name, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class TestExp020Receipt(unittest.TestCase):
    """Pins for the exp020 tie-break ablation receipt."""

    def test_seal_schema(self):
        receipt = load_receipt()
        self.assertEqual(receipt["schema"],
                         "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["experiment"], "exp020-tie-break-ablation")
        self.assertEqual(receipt["success_threshold_verify_balance"], BAR)
        self.assertEqual(receipt["seeds"]["roots"], [13, 29, 31, 37])
        self.assertEqual(receipt["seeds"]["shots"], 512)

    def test_artifact_integrity(self):
        receipt = load_receipt()
        for name in ARTIFACT_NAMES:
            digest = hashlib.sha256(
                (ARTIFACTS / name).read_bytes()).hexdigest()
            self.assertEqual(receipt["integrity"][name], digest,
                             f"artifact {name} tampered - seal void")
        self.assertEqual(sorted(receipt["artifacts"]),
                         sorted(f"receipts/exp020-tie-break/{n}"
                                for n in ARTIFACT_NAMES))

    def test_guard_reproduces_exp001(self):
        # guard recorded BEFORE results: both the sealed results block
        # and the exp001 receipt agree the canonical champion stands.
        self.assertTrue(load_results()["guard"]["control_reproduces_exp001"])
        self.assertTrue(load_receipt()["results"]["guard_exp001_reproduced"])
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"],
                         [["h", 1], ["h", 1], ["x", 0]])

    def test_preregistered_bands_pinned(self):
        # interpretation bands pinned BEFORE running; the sealed
        # verdict must be the REPLICATED band, not a retro-fit.
        receipt = load_receipt()
        pin = receipt["pre_run_pin"]
        self.assertIn("TIESAMPLE >=1 hard-root crossing", pin)
        self.assertIn("TIE-BAND-DIVERSITY REPLICATED", pin)
        self.assertIn("TIE SAMPLING ALONE INSUFFICIENT", pin)
        self.assertIn("TIESAMPLE 0/3", pin)

    def test_verdict_matches_replicated_band(self):
        # REPLICATED band: tiesample crossed >=1 hard root incumbent
        # missed -> verdict must say REPLICATED, and the hard-class
        # table must agree exactly.
        receipt = load_receipt()
        self.assertIn("TIE-BAND-DIVERSITY REPLICATED",
                      receipt["results"]["verdict"])
        hard = receipt["results"]["hard_class"]
        self.assertEqual(hard["incumbent_crossed"], [])
        self.assertEqual(hard["tiesample_crossed"], [29, 37])
        self.assertEqual(hard["tiesample_only"], [29, 37])
        self.assertEqual(hard["neither_crossed"], [31])

    def test_incumbent_arm_reproduces_exp014_class(self):
        # incumbent = exp014 champion-local semantics live in-arm:
        # 0/3 hard roots at the 0.2422 plateau, easy 13 crossed.
        results = load_results()
        for root in HARD:
            run = results["runs"][f"incumbent.r{root}"]
            self.assertFalse(run["crossed"], root)
            self.assertEqual(run["max_verify_seen"], 0.2422, root)
        easy = results["runs"]["incumbent.r13"]
        self.assertTrue(easy["crossed"])
        self.assertEqual(easy["max_verify_seen"], 0.4824)

    def test_tiesample_crosses_r29_r37_at_bar(self):
        # the replicated crossings: telemetry final curves at 0.4824,
        # receipt per-root table agrees with the sealed results.json.
        receipt = load_receipt()
        results = load_results()
        for root in ("29", "37"):
            run = results["runs"][f"tiesample.r{root}"]
            self.assertTrue(run["crossed"], root)
            self.assertEqual(run["max_verify_seen"], 0.4824, root)
            self.assertGreaterEqual(run["max_verify_seen"], BAR)
            row = receipt["results"]["per_root"][f"tiesample.r{root}"]
            self.assertTrue(row["crossed"], root)
            self.assertEqual(row["max_verify"], 0.4824, root)

    def test_r31_resistant_named_not_hidden(self):
        # r31 did NOT cross under either arm; the honest limit names
        # it (0.3027 tiesample peak) instead of rounding it away.
        results = load_results()
        self.assertFalse(results["runs"]["tiesample.r31"]["crossed"])
        self.assertEqual(results["runs"]["tiesample.r31"]["max_verify_seen"],
                         0.3027)
        self.assertFalse(results["runs"]["incumbent.r31"]["crossed"])
        limits = " ".join(load_receipt()["honest_limits"])
        self.assertIn("r31", limits)

    def test_telemetry_final_rows_match_results(self):
        # every per-run telemetry jsonl's final curve agrees with the
        # sealed results.json run row - telemetry is the receipt.
        results = load_results()
        for name in ARTIFACT_NAMES:
            if not name.startswith("exp020.telemetry."):
                continue
            arm_root = name[len("exp020.telemetry."):-len(".jsonl")]
            rows = load_telemetry(name)
            self.assertTrue(rows, name)
            final = rows[-1]
            self.assertEqual(final["gen"], 11, name)
            run = results["runs"][arm_root]
            self.assertAlmostEqual(final["curve"]["verify_p"],
                                   run["champion_verify"], places=4,
                                   msg=name)

    def test_anchors_merged_only(self):
        # load-bearing anchors name MERGED PRs (exp014 #19, exp016 #22,
        # exp018 #24, exp012 #17); exp019 is named Casey-gated, never
        # as a merged anchor.
        cross = load_receipt()["cross_receipts"]
        self.assertIn("#19", cross["exp014"])
        self.assertIn("#22", cross["exp016"])
        self.assertIn("#24", cross["exp018"])
        self.assertIn("#17", cross["exp012"])
        self.assertIn("Casey-gated", cross["exp019"])
        self.assertNotIn("MERGED", cross["exp019"])

    def test_no_archive_no_retention_stated(self):
        # the load-bearing design fact: tie sampling was the ONLY
        # difference - no archive, no retention. A receipt quietly
        # re-introducing archive machinery would trip here.
        receipt = load_receipt()
        self.assertIn("NO archive", receipt["design"])
        self.assertIn("NO non-champion retention", receipt["design"])
        self.assertIn("N/M", " ".join(receipt["honest_limits"]))


if __name__ == "__main__":
    unittest.main()
