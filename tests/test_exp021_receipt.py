"""Pins for receipts/exp021-r31-autopsy.json (qcells lab exp021).

exp021 is the R31 TIE-CONTEXT AUTOPSY: exp020 crossed hard roots 29+37
under tie-sampled champion-local selection but root 31 alone stayed
closed (@0.3027). exp021 asks WHY, with two pre-registered questions:

Q1 (rate vs wall): replicate the exact exp020 tiesample lane on root 31
across K=8 salted rng streams (seeds 31000..31007). Pinned BEFORE
running: >=1 crossing in 8 -> RATE NOT WALL (resistance is a per-stream
ROOT-LOTTERY draw per exp012); 0/8 -> WALL AT K=8 POWER.

Q2 (opportunity census): on the canonical seed-31 stream, passively
census EVERY cloud cell's held-out verify per gen under both tie arms.
Census evals consume NO rng; the child stream and tie-break sequence
are byte-identical to exp020 (the instrument observed, never steered).
Pinned BEFORE running, three outcomes: (a) a tie BAND holds a
verify>=0.45 cell some gen -> OPPORTUNITY-MISSED; (b) the cloud holds
one but never in a band -> STRUCTURAL MISMATCH; (c) the cloud NEVER
holds one in 12 gens -> DESERT-EXTENDS-TO-CLOUD (exp019
RETENTION-ASSEMBLY is the only remaining mechanism).

Sealed outcome: RATE NOT WALL + DESERT-EXTENDS-TO-CLOUD. 3/8 salted
streams crossed (k3/k5/k6 @0.4824); on the canonical stream neither
arm's cloud ever held a verify>=0.45 cell (max cloud verify = champion
itself: 0.3027 tiesample / 0.2422 incumbent; opportunity gens empty).

Integrity pins are load-bearing: results-style receipt - sealed
artifacts are runner + results.json + 8 Q1 telemetry jsonl + 2 Q2
telemetry jsonl; the sha256 table must match byte-for-byte or the seal
is void.

The pre-registered bands are pinned as sealed text so a retro-fitted
verdict would trip. Cross-receipt anchors are on MERGED receipts only
(exp012 #17, exp014 #19, exp016 #22, exp018 #24, exp019 #25, exp020
#26).

FAIL-first: this module is absent on main - the suite trips on
discovery of a missing receipt on pristine main.

Run: python3 -m unittest tests.test_exp021_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp021-r31-autopsy.json"
ARTIFACTS = HERE / "receipts" / "exp021-r31-autopsy"
RESULTS = ARTIFACTS / "exp021.results.json"

BAR = 0.45
ARTIFACT_NAMES = [
    "exp021.results.json",
    "exp021.telemetry.q1.k0.jsonl",
    "exp021.telemetry.q1.k1.jsonl",
    "exp021.telemetry.q1.k2.jsonl",
    "exp021.telemetry.q1.k3.jsonl",
    "exp021.telemetry.q1.k4.jsonl",
    "exp021.telemetry.q1.k5.jsonl",
    "exp021.telemetry.q1.k6.jsonl",
    "exp021.telemetry.q1.k7.jsonl",
    "exp021.telemetry.q2.incumbent.r31.jsonl",
    "exp021.telemetry.q2.tiesample.r31.jsonl",
    "exp021_r31_tie_context.py",
]
Q2_TELEMETRY = [
    "exp021.telemetry.q2.incumbent.r31.jsonl",
    "exp021.telemetry.q2.tiesample.r31.jsonl",
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


class TestExp021Receipt(unittest.TestCase):
    """Pins for the exp021 r31 tie-context autopsy receipt."""

    def test_seal_schema(self):
        receipt = load_receipt()
        self.assertEqual(receipt["schema"],
                         "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["experiment"],
                         "exp021-r31-tie-context-autopsy")
        self.assertEqual(receipt["success_threshold_verify_balance"], BAR)
        self.assertEqual(receipt["seeds"]["train"], 101)
        self.assertEqual(receipt["seeds"]["verify"], 202)
        self.assertEqual(receipt["seeds"]["shots"], 512)

    def test_artifact_integrity(self):
        receipt = load_receipt()
        for name in ARTIFACT_NAMES:
            digest = hashlib.sha256(
                (ARTIFACTS / name).read_bytes()).hexdigest()
            self.assertEqual(receipt["integrity"][name], digest,
                             f"artifact {name} tampered - seal void")
        self.assertEqual(sorted(receipt["artifacts"]),
                         sorted(f"receipts/exp021-r31-autopsy/{n}"
                                for n in ARTIFACT_NAMES))

    def test_guard_reproduces_exp001(self):
        # guard recorded BEFORE results: the instrumented (census-active)
        # loop reproduces exp001 byte-identical on the default lane.
        self.assertTrue(load_results()["guard"]
                        ["exp001_reproduced_byte_identical"])
        self.assertTrue(load_receipt()["results"]
                        ["guard_exp001_reproduced"])

    def test_preregistered_bands_pinned(self):
        # interpretation bands pinned BEFORE running; the sealed
        # verdict must be the RATE band + outcome (c), not a retro-fit.
        pin = load_receipt()["pre_run_pin"]
        self.assertIn("RATE NOT WALL", pin)
        self.assertIn("WALL AT K=8 POWER", pin)
        self.assertIn("OPPORTUNITY-MISSED", pin)
        self.assertIn("STRUCTURAL MISMATCH", pin)
        self.assertIn("DESERT-EXTENDS-TO-CLOUD", pin)

    def test_verdict_matches_sealed_bands(self):
        # RATE band (Q1): >=1 crossing in 8 -> RATE NOT WALL; sealed
        # verdict must carry both sealed outcomes verbatim.
        receipt = load_receipt()
        verdict = receipt["results"]["verdict"]
        self.assertIn("RATE NOT WALL", verdict)
        self.assertIn("DESERT-EXTENDS-TO-CLOUD", verdict)
        q1 = receipt["results"]["q1_rate_vs_wall"]
        self.assertEqual(q1["K"], 8)
        self.assertEqual(q1["crossings"], 3)
        self.assertEqual(q1["crossed_streams"], ["k3", "k5", "k6"])

    def test_q1_crossers_at_bar(self):
        # the three crossings landed at 0.4824 >= BAR; the sealed
        # results.json run rows agree with the receipt table.
        receipt = load_receipt()
        results = load_results()
        for k in ("k3", "k5", "k6"):
            run = results["q1_rate_vs_wall"]["runs"][k]
            self.assertTrue(run["crossed"], k)
            self.assertEqual(run["champion_verify"], 0.4824, k)
            self.assertGreaterEqual(run["champion_verify"], BAR, k)
        for k in ("k3", "k5", "k6"):
            self.assertEqual(receipt["results"]["q1_rate_vs_wall"]
                             ["non_crossed"].get(k), None)

    def test_q1_named_not_hidden(self):
        # the honest-limit streams stay in the sealed table: k4 peaked
        # 0.418 (closest non-crosser), k7 never left 0.0 (dead stream).
        results = load_results()
        non = results["q1_rate_vs_wall"]["runs"]
        self.assertFalse(non["k4"]["crossed"])
        self.assertEqual(non["k4"]["max_verify_seen"], 0.418)
        self.assertFalse(non["k7"]["crossed"])
        self.assertEqual(non["k7"]["max_verify_seen"], 0.0)
        limits = " ".join(load_receipt()["honest_limits"])
        self.assertIn("k4", limits)
        self.assertIn("k7", limits)

    def test_q2_desert_extends_to_cloud(self):
        # outcome (c) of the pre-registered Q2 bands: NO cloud cell
        # reached verify>=0.45 in any of 12 gens, either arm; the
        # opportunity lists are empty and the max cloud verify equals
        # the champion itself (no hidden better cell).
        q2 = load_results()["q2_opportunity_census"]
        for arm in ("incumbent", "tiesample"):
            self.assertFalse(q2[arm]["crossed"], arm)
            self.assertEqual(q2[arm]["cloud_opportunity_gens"], [], arm)
            self.assertEqual(q2[arm]["band_opportunity_gens"], [], arm)
            self.assertEqual(q2[arm]["max_cloud_verify"],
                             q2[arm]["champion_verify"], arm)
            self.assertLess(q2[arm]["max_cloud_verify"], BAR, arm)
            self.assertTrue(q2[arm]["exp020_replicate_ok"], arm)
        self.assertEqual(q2["tiesample"]["champion_verify"], 0.3027)
        self.assertEqual(q2["incumbent"]["champion_verify"], 0.2422)

    def test_q2_telemetry_cloud_capped_below_bar(self):
        # the census telemetry is the receipt: EVERY cloud cell's
        # held-out verify (the whole census, band or not) stays
        # strictly below BAR in both arms, and the final curve agrees
        # with the sealed results.json.
        results = load_results()
        for name in Q2_TELEMETRY:
            rows = load_telemetry(name)
            self.assertEqual(len(rows), 12, name)
            arm = "incumbent" if "incumbent" in name else "tiesample"
            for row in rows:
                cloud = row["census"]["cloud"]
                self.assertEqual(len(cloud), 16, f"{name} gen {row['gen']}")
                for cell in cloud:
                    self.assertLess(cell["verify_p"], BAR,
                                    f"{name} gen {row['gen']}")
                band = [c for c in cloud if c["in_band"]]
                self.assertTrue(band, f"{name} gen {row['gen']} empty band")
                self.assertLess(max(c["verify_p"] for c in band), BAR,
                                f"{name} gen {row['gen']} band")
            final = rows[-1]
            self.assertEqual(final["gen"], 11, name)
            self.assertAlmostEqual(
                final["curve"]["verify_p"],
                results["q2_opportunity_census"][arm]["champion_verify"],
                places=4, msg=name)

    def test_q1_telemetry_final_rows_match_results(self):
        # every Q1 telemetry jsonl's final curve agrees with the sealed
        # results.json run row - telemetry is the receipt.
        results = load_results()
        for k in range(8):
            rows = load_telemetry(f"exp021.telemetry.q1.k{k}.jsonl")
            self.assertTrue(rows)
            self.assertEqual(rows[-1]["gen"], 11, k)
            run = results["q1_rate_vs_wall"]["runs"][f"k{k}"]
            self.assertAlmostEqual(rows[-1]["curve"]["verify_p"],
                                   run["champion_verify"], places=4,
                                   msg=f"k{k}")

    def test_exp020_comparator_pinned(self):
        # the autopsy names its subject: exp020's sealed r31 finals are
        # embedded as a comparator block, cited from MERGED PR #26.
        receipt = load_receipt()
        comp = receipt["results"]["exp020_comparator"]
        self.assertIn("#26", comp["source"])
        self.assertEqual(comp["tiesample_r31"]["final_verify"], 0.3027)
        self.assertFalse(comp["tiesample_r31"]["crossed"])
        self.assertEqual(comp["incumbent_r31"]["final_verify"], 0.2422)
        self.assertIn("MERGED PR #26", receipt["cross_receipts"]["exp020"])

    def test_no_archive_no_retention_stated(self):
        # the load-bearing design fact: census is a passive observer,
        # no archive machinery re-introduced; verdict stays an N/M read.
        receipt = load_receipt()
        self.assertIn("NO archive", receipt["design"])
        self.assertIn("NO retention", receipt["design"])
        self.assertIn("consume NO rng", receipt["design"])
        self.assertIn("N/M", " ".join(receipt["honest_limits"]))

    def test_anchors_merged_only(self):
        # load-bearing anchors name MERGED PRs only (exp012 #17,
        # exp014 #19, exp016 #22, exp018 #24, exp019 #25, exp020 #26).
        cross = load_receipt()["cross_receipts"]
        self.assertIn("#17", cross["exp012"])
        self.assertIn("#19", cross["exp014"])
        self.assertIn("#22", cross["exp016"])
        self.assertIn("#24", cross["exp018"])
        self.assertIn("#25", cross["exp019"])
        self.assertIn("#26", cross["exp020"])


if __name__ == "__main__":
    unittest.main()
