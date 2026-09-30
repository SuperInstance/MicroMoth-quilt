"""Pins for receipts/exp022-desert-break.json (qcells lab exp022).

exp022 is the CROSSING-STREAM CENSUS. exp021's Q2 opportunity census
ran on exactly one stream — the canonical NON-crossing one (seed 31).
exp022 runs the SAME passive census on the crossing band k3/k5/k6
(exp021 Q1 salts 31003/31005/31006) plus the two named contrast
non-crossers (k4 near-miss 0.418, k7 dead 0.0), asking: on streams
that DID cross, where did the >=0.45 cell come from and how was it
promoted?

Pinned BEFORE running, two outcomes:
  (a) DESERT-FLOOR TIE-BAND LOTTERY — the crossing cell appeared with
      train=0 inside an all-floor tie band and was promoted purely by
      the tie-sample rng draw (TIE-BAND-DIVERSITY refines to lottery
      odds; window length reported per stream).
  (b) TRAIN-VISIBLE CROSSING — the crossing cell carried train > 0 in
      its promotion gen (exp018's desert is root-specific, not
      stream-specific).
Contrast expectation (not a verdict condition): k4 cloud tops out
under BAR, k7 cloud holds nothing.

Sealed outcome: (b) FIRED, sharpened by telemetry — all three crossing
streams birthed the >=0.45 cell (train 0.498 / verify 0.482) at a
single desert-break gen as the gen-max, n_tied=1 on k3/k5 and n_tied=2
on k6 (either draw crosses), pick window 0 gens. READ: r31 crossing is
a per-stream DESERT-BREAK RATE (5/8 never birth one), NOT a tie-band
lottery; RETENTION-ASSEMBLY (exp019) stands as the only no-break
mechanism.

Integrity pins are load-bearing: results-style receipt — sealed
artifacts are results.json + 5 telemetry jsonl + the runner; the
sha256 table must match byte-for-byte or the seal is void.

Cross-receipt anchors on MERGED receipts only carry PR numbers
(exp016 #22, exp018 #24, exp019 #25, exp020 #26); exp021 (PR #27) is
OPEN on this branch stack and is referenced as such, never as merged.

FAIL-first: this module is absent on main — the suite trips on
discovery of a missing receipt on pristine main.

Run: python3 -m unittest tests.test_exp022_receipt -v
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent.parent
RECEIPT = HERE / "receipts" / "exp022-desert-break.json"
ARTIFACTS = HERE / "receipts" / "exp022-desert-break"
RESULTS = ARTIFACTS / "exp022.results.json"

BAR = 0.45
ARTIFACT_NAMES = [
    "exp022.results.json",
    "exp022.telemetry.k3.jsonl",
    "exp022.telemetry.k4.jsonl",
    "exp022.telemetry.k5.jsonl",
    "exp022.telemetry.k6.jsonl",
    "exp022.telemetry.k7.jsonl",
    "exp022_crossing_stream_census.py",
]
STREAMS = ["k3", "k4", "k5", "k6", "k7"]
CROSSERS = {"k3": 0, "k5": 3, "k6": 8}  # stream -> pick gen
N_TIED = {"k3": 1, "k5": 1, "k6": 2}
N_BAR_CELLS = {"k3": 54, "k5": 50, "k6": 14}


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


class TestExp022Receipt(unittest.TestCase):
    """Pins for the exp022 crossing-stream census receipt."""

    def test_seal_schema(self):
        receipt = load_receipt()
        self.assertEqual(receipt["schema"],
                         "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["experiment"],
                         "exp022-crossing-stream-census")
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
                         sorted(f"receipts/exp022-desert-break/{n}"
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
        # verdict must be outcome (b), not a retro-fit.
        pin = load_receipt()["pre_run_pin"]
        self.assertIn("DESERT-FLOOR TIE-BAND LOTTERY", pin)
        self.assertIn("TRAIN-VISIBLE CROSSING", pin)
        self.assertIn("OPPORTUNITY-MISSED", pin)

    def test_verdict_is_outcome_b_train_visible(self):
        receipt = load_receipt()
        verdict = receipt["results"]["verdict"]
        self.assertIn("TRAIN-VISIBLE CROSSING", verdict)
        self.assertIn("TIE-BREAK-INVARIANT", verdict)
        self.assertIn("DESERT-BREAK RATE", verdict)
        # the lottery outcome (a) did NOT fire: the crossing cell was
        # never a desert-floor (train=0) cell.
        self.assertNotIn("outcome (a) fired", verdict)

    def test_replicate_pins_match_exp021(self):
        # census-inertness proven per stream, not assumed: every
        # stream's champion matches its exp021 Q1 final verbatim.
        results = load_results()
        expected = {"k3": (True, 0.4824), "k4": (False, 0.418),
                    "k5": (True, 0.4824), "k6": (True, 0.4824),
                    "k7": (False, 0.0)}
        for k, (crossed, final) in expected.items():
            run = results["streams"][k]
            self.assertTrue(run["exp021_replicate_ok"], k)
            self.assertEqual(run["crossed"], crossed, k)
            self.assertEqual(run["champion_verify"], final, k)
        for k in STREAMS:
            rows = load_telemetry(f"exp022.telemetry.{k}.jsonl")
            self.assertEqual(len(rows), 12, k)
            self.assertEqual(rows[-1]["gen"], 11, k)
            self.assertAlmostEqual(rows[-1]["curve"]["verify_p"],
                                   expected[k][1], places=4, msg=k)

    def test_crossing_streams_single_desert_break_gen(self):
        # on each crossing stream the >=0.45 cell appears at exactly
        # one birth gen as the gen-max, train-visible, and the pick
        # happens THAT gen (window 0): k3 g0, k5 g3, k6 g8.
        results = load_results()
        for k, pick_gen in CROSSERS.items():
            run = results["streams"][k]
            self.assertEqual(run["pick_gen"], pick_gen, k)
            self.assertEqual(run["first_bar_cell_gen"], pick_gen, k)
            self.assertEqual(run["window_gens"], 0, k)
            rows = load_telemetry(f"exp022.telemetry.{k}.jsonl")
            bar_gens = [r["gen"] for r in rows
                        if any(c["verify_p"] >= BAR
                               for c in r["census"]["cloud"])]
            self.assertEqual(bar_gens[0], pick_gen, k)
            self.assertEqual(len(bar_gens),
                             12 - pick_gen, k)

    def test_pick_gen_band_is_the_bar_cell(self):
        # telemetry is the receipt: at each pick gen the tie band
        # holds ONLY the >=BAR cell(s) — k3/k5 unique max (n_tied=1,
        # ANY tie rule picks it), k6 two identical twins (n_tied=2,
        # either draw crosses). No lottery at the pick.
        for k, pick_gen in CROSSERS.items():
            rows = load_telemetry(f"exp022.telemetry.{k}.jsonl")
            row = rows[pick_gen]
            self.assertEqual(row["census"]["n_tied"], N_TIED[k], k)
            self.assertGreaterEqual(row["census"]["gen_max"], BAR, k)
            band = [c for c in row["census"]["cloud"] if c["in_band"]]
            self.assertEqual(len(band), N_TIED[k], k)
            for cell in band:
                self.assertGreaterEqual(cell["verify_p"], BAR, k)
                self.assertGreater(cell["train_p"], 0.0, k)
            self.assertEqual(row["curve"]["promoted"], True, k)
            self.assertAlmostEqual(row["curve"]["train_p"], 0.498,
                                   places=3, msg=k)
            self.assertAlmostEqual(row["curve"]["verify_p"], 0.4824,
                                   places=4, msg=k)

    def test_contrast_streams_cloud_below_bar(self):
        # the contrast expectation fired: k4's cloud tops out under
        # BAR (near-miss), k7's cloud holds nothing (dead stream).
        receipt = load_receipt()
        k4 = receipt["results"]["streams"]["k4"]
        self.assertLess(k4["max_cloud_verify"], BAR)
        self.assertGreater(k4["max_cloud_train"], 0.0)
        k7 = receipt["results"]["streams"]["k7"]
        self.assertEqual(k7["max_cloud_verify"], 0.0)
        self.assertEqual(k7["max_cloud_train"], 0.0)
        results = load_results()
        for k in ("k4", "k7"):
            self.assertEqual(results["streams"][k]["n_bar_cells_total"],
                             0, k)
            rows = load_telemetry(f"exp022.telemetry.{k}.jsonl")
            for row in rows:
                for cell in row["census"]["cloud"]:
                    self.assertLess(cell["verify_p"], BAR,
                                    f"{k} gen {row['gen']}")

    def test_no_archive_no_retention_stated(self):
        # the load-bearing design fact: census is a passive observer,
        # no archive machinery anywhere in this experiment.
        receipt = load_receipt()
        self.assertIn("NO archive", receipt["design"])
        self.assertIn("NO retention", receipt["design"])
        self.assertIn("consume NO rng", receipt["design"])
        honesty = load_results()["honesty"]
        self.assertIn("no archive", honesty)
        self.assertIn("no retention", honesty)

    def test_exp021_comparator_named_honestly(self):
        # the census names its parent receipt: exp021 PR #27 is OPEN
        # on this branch stack — it must be referenced as such, never
        # as MERGED (anchors-merged-only doctrine).
        receipt = load_receipt()
        comp = receipt["results"]["exp021_comparator"]
        self.assertIn("PR #27", comp["source"])
        self.assertNotIn("MERGED", comp["source"])
        self.assertEqual(comp["q1_crossed_streams"], ["k3", "k5", "k6"])
        self.assertEqual(comp["q1_non_crossed"],
                         {"k0": 0.2422, "k1": 0.2422, "k2": 0.2422,
                          "k4": 0.418, "k7": 0.0})
        self.assertIn("OPEN", receipt["cross_receipts"]["exp021"])

    def test_anchors_merged_only(self):
        # load-bearing anchors name MERGED PRs only (exp016 #22,
        # exp018 #24, exp019 #25, exp020 #26).
        cross = load_receipt()["cross_receipts"]
        self.assertIn("#22", cross["exp016"])
        self.assertIn("#24", cross["exp018"])
        self.assertIn("#25", cross["exp019"])
        self.assertIn("#26", cross["exp020"])

    def test_k0_k1_k2_not_censused_stated(self):
        # honest limit: only k3-k7 carry the per-gen cloud census;
        # the k0/k1/k2 cloud interior stays unobserved, stated.
        limits = " ".join(load_receipt()["honest_limits"])
        self.assertIn("k0/k1/k2 NOT CENSUSED HERE", limits)
        self.assertEqual(sorted(load_receipt()["integrity"]),
                         sorted(ARTIFACT_NAMES))


if __name__ == "__main__":
    unittest.main()
