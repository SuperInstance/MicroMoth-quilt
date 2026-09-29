"""Pins for receipts/exp014-skeleton-multiroot.json (qcells lab exp014).

exp014 is the MULTI-ROOT REPLICATION the exp012 ROOT-LOTTERY doctrine
demanded before any more doctrine could be built on the skeleton-seed
crossing path: every prior skeleton crossing (exp006/007/008) was
sealed on root 7 ONLY. Design pinned before running: fresh roots
3/5/13/17/19/29/31/37 (7/11/23/42 already characterized), two arms on
the exact exp005 unaided n=3 GHZ-balance lane (pop 16, 12 gens, 512
shots, jitter-dropped restrict=("replace","indel") cloud):

  S arm: skeleton seed [["h",0],["cx",0,1]] champion-local
         (the exp006 prescription, zero-fitness birth)
  P arm: parent_pool=True, no seed (extends the exp012 rate sample
         from n=3 to n=12 combined)

Pre-registered verdict bands (in results.json, read after sealing):
  S crosses >=7/8 -> SKELETON ROOT-ROBUST (engine law)
  S crosses 3-6/8 -> SKELETON IS A RATE (doctrine rewrites to rates)
  S crosses <=2/8 -> SKELETON ROOT-LOTTERY TOO (nothing root-invariant)

Sealed outcome: SKELETON IS A RATE. S crosses 4/8 fresh roots
(3 gen 6, 13 gen 0, 17 gen 3, 19 gen 0; 5/9 including exp006's root 7)
- the "only replicated crossing path" was itself a root-7-flavored
lottery. P crosses 3/8 fresh (5 gen 6, 13 gen 11, 19 gen 9); combined
with exp011/012 the unaided-genealogy rate is 4/12 (33%). Rate
ranking across the lab: skeleton 5/9 (56%, cross gens 0-6) >
pool 4/12 (33%, gens 5-11) > transplant 1/4 (exp013, Casey-gated as
PR #18 at seal time) >> champion-local unaided 0/11 (the exp005
freeze replicates everywhere). Root difficulty classes VERIFIED: easy
(13/19 cross on BOTH arms), mechanism-specific (3/17 skeleton-only,
5/19 pool-only), hard (29/31/37 resist both arms - r29 pool samples
signal 0.1055 then stalls, r31 pool 0.2031 Finding-4 class, r37 pool
0.0). Doctrine rewrite: crossing claims carry N/M roots + gen range,
never bare "crosses"; mechanism-as-law is dead, the rate ranking is
the real structure.

The integrity pins are load-bearing: results-style receipt (no witness
LEDGER; exp001 remains the lane's only LEDGER receipt) - the sealed
artifacts are the experiment runner + results.json + telemetry jsonl,
and the receipt's sha256 table must match every file byte-for-byte or
the seal is void.

The exp001-guard pin is load-bearing: the runner's in-harness default
lane at the canonical root 7 reproduces exp001's champion at verify 1.0
before any results are written (guard failure aborts the run).

The cross-receipt pins anchor on exp012 (MERGED on main as PR #17 at
seal time) - exp013 was run before this seal but is still Casey-gated
as PR #18, so this receipt's doctrine pins never depend on it.

The pi-expansion repro pin is load-bearing: every crossing champion in
the sealed results re-derives its exact sealed balance
0.482421875 = min(247, 265)/512 under pi-expanded thetas (raw 1.0-rad
misread is honesty-critical for genomes with h upstream of rotations;
verified live for all 7 crossing champions at seal time).

Run: python3 -m unittest tests.test_exp014_receipt -v
"""
import hashlib
import json
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth  # repo-root vendored engine (the engine the receipt names)

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp014-skeleton-multiroot.json"
ARTIFACTS = HERE.parent / "receipts" / "exp014-skeleton-multiroot"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"
EXP012_RECEIPT = HERE.parent / "receipts" / "exp012-root-replication.json"

PI = math.pi
FRESH_ROOTS = (3, 5, 13, 17, 19, 29, 31, 37)
BAR = 0.45
BALANCE_P = 0.482421875  # min(247, 265)/512, the GHZ-balance crossing value
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]
CROSS_GEN = {(3, "skeleton"): 6, (13, "skeleton"): 0,
             (17, "skeleton"): 3, (19, "skeleton"): 0,
             (5, "pool"): 6, (13, "pool"): 11, (19, "pool"): 9}
FROZEN_POOL_VERIFY = {3: 0.0, 17: 0.2421875, 29: 0.10546875,
                      31: 0.203125, 37: 0.0}
FROZEN_SKELETON_VERIFY = {5: 0.2421875, 29: 0.2421875,
                          31: 0.2421875, 37: 0.2421875}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _results():
    return json.loads((ARTIFACTS / "exp014.results.json").read_text())


def _run(results, root, arm):
    for r in results["runs"]:
        if r["root_seed"] == root and r["arm"] == arm:
            return r
    raise AssertionError(f"run {root}/{arm} missing from results")


def _expand(genome):
    """Executable program from a stored genome (thetas in units of pi)."""
    prog = []
    for g in genome:
        g = list(g)
        if g[0] in ("rx", "rz") and len(g) == 3:
            g[1] = g[1] * PI
        elif g[0] == "crx" and len(g) == 4:
            g[1] = g[1] * PI
        prog.append(g)
    return prog + [["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]


def _simulate(program, seed=202, shots=512):
    qc = micromoth.QuantumCircuit(3, 3)
    qc.data = [tuple(t) for t in program]
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


class TestExp014Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp014-skeleton-multiroot")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertIn("RATE", receipt["title"])
        results = _results()
        self.assertEqual(results["verdict"], "SKELETON IS A RATE")
        self.assertEqual(tuple(receipt["seeds"]["roots_fresh"]), FRESH_ROOTS)
        self.assertEqual({receipt["seeds"][k] for k in ("train", "verify",
                                                        "shots")},
                         {101, 202, 512})

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

    def test_pre_registered_verdict_bands_pinned_before_results(self):
        # the 3-6/8 band is the one the sealed outcome (4/8) lands in;
        # the bands must be pre-registered in results.json itself, not
        # retrofitted in the receipt
        results = _results()
        bands = results["pre_registered_verdicts"]
        self.assertIn(">=7/8", bands)
        self.assertIn("3-6/8", bands)
        self.assertIn("<=2/8", bands)
        self.assertIn("RATE", bands["3-6/8"])
        self.assertEqual(results["skeleton_crosses"], [3, 13, 17, 19])
        self.assertEqual(results["skeleton_cross_fraction"], "4/8")
        self.assertEqual(len(results["runs"]), 16)  # 8 roots x 2 arms

    def test_skeleton_arm_crossings_and_freeze_plateau(self):
        results = _results()
        for (root, arm), gen in CROSS_GEN.items():
            if arm != "skeleton":
                continue
            r = _run(results, root, arm)
            self.assertTrue(r["crossed"], f"root {root} skeleton")
            self.assertEqual(r["first_ge_045_gen"], gen)
            self.assertEqual(r["champion_verify_p"], BALANCE_P)
        for root, verify in FROZEN_SKELETON_VERIFY.items():
            r = _run(results, root, "skeleton")
            self.assertFalse(r["crossed"], f"root {root} skeleton crossed")
            self.assertEqual(r["champion_verify_p"], verify)
            # frozen skeleton champions stall at the 0.2422 partial
            # plateau (birth balance), never the exp005 0.0 floor -
            # the seed lifts every root, it just does not cross on all
            self.assertGreater(verify, 0.0)

    def test_pool_arm_extends_the_exp012_rate_sample(self):
        results = _results()
        for (root, arm), gen in CROSS_GEN.items():
            if arm != "pool":
                continue
            r = _run(results, root, arm)
            self.assertTrue(r["crossed"], f"root {root} pool")
            self.assertEqual(r["first_ge_045_gen"], gen)
            self.assertEqual(r["champion_verify_p"], BALANCE_P)
        for root, verify in FROZEN_POOL_VERIFY.items():
            r = _run(results, root, "pool")
            self.assertFalse(r["crossed"], f"root {root} pool crossed")
            self.assertEqual(r["champion_verify_p"], verify)
        # combined genealogy rate across exp011 (root 7), exp012 (0/3),
        # and this experiment: 4/12 = 33%, strictly below the skeleton
        # rate 5/9 = 56% - the ranking, not any mechanism, is the law
        self.assertEqual(results["pool_crosses_this_experiment"],
                         [5, 13, 19])
        self.assertEqual(
            sorted(results["pool_combined_crosses_incl_exp011_exp012"]),
            [5, 7, 13, 19])

    def test_hard_roots_resist_both_arms_finding4_class(self):
        # r29/31/37 are the hard class: neither arm crosses. r31's pool
        # arm samples signal (0.2031) then stalls - the Finding-4
        # partial-plateau class, now shown to be root-manufactured,
        # not mechanism-manufactured
        results = _results()
        for root in (29, 31, 37):
            for arm in ("skeleton", "pool"):
                r = _run(results, root, arm)
                self.assertFalse(r["crossed"], f"{root}/{arm} crossed")
        r29 = _run(results, 29, "pool")
        self.assertGreater(r29["champion_verify_p"], 0.0)
        self.assertLess(r29["champion_verify_p"], BAR)

    def test_rate_ranking_doctrine_carries_n_of_m_roots(self):
        # the doctrine rewrite this seal lands: ranking across arms
        # (skeleton 5/9 > pool 4/12 > transplant 1/4 >> unaided 0/11)
        # pinned against the receipts already on main
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)
        exp012 = json.loads(EXP012_RECEIPT.read_text())
        self.assertIn("root-lottery", json.dumps(exp012).lower())
        self.assertIn("does not replicate", exp012["title"].lower())
        results = _results()
        # no bare 'crosses' claim: every crossing run carries its root
        # and its crossing generation range is within the sealed gens
        for r in results["runs"]:
            if r["crossed"]:
                self.assertIsNotNone(r["first_ge_045_gen"])
                self.assertLessEqual(r["first_ge_045_gen"], 11)
                self.assertGreaterEqual(r["champion_verify_p"], BAR)

    def test_guard_reproduces_exp001_at_canonical_root7(self):
        # the control telemetry is the in-harness default-lane guard
        # run: 8 rows, ending on exp001's champion at verify 1.0,
        # executed before any results were written
        rows = [json.loads(l) for l in
                (ARTIFACTS / "exp014.telemetry.control.jsonl")
                .read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]["genome"], EXP001_CHAMPION)
        self.assertEqual(rows[-1]["verify_p"], 1.0)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_telemetry_final_row_matches_results_champion(self):
        results = _results()
        for root in FRESH_ROOTS:
            for arm in ("skeleton", "pool"):
                r = _run(results, root, arm)
                rows = [json.loads(l) for l in
                        (ARTIFACTS /
                         f"exp014.telemetry.r{root}.{arm}.jsonl")
                        .read_text().splitlines()]
                self.assertEqual(len(rows), 12, f"{root}/{arm} telemetry")
                final = rows[-1]
                self.assertEqual(final["genome"], r["champion_genome"])
                self.assertAlmostEqual(final["verify_p"],
                                       r["champion_verify_p"], places=4)

    def test_every_crossing_champion_reproduces_sealed_balance(self):
        # load-bearing pi-expansion repro: every sealed crossing
        # champion re-derives balance 0.482421875 = min(247,265)/512
        # under pi-expanded thetas at the canonical verify seed. The
        # raw 1.0-radian misread would NOT reproduce for these genomes
        # (every crossing champion has h upstream of its rotations, so
        # phase is visible in basis counts) - unlike exp013's rz case.
        results = _results()
        crossed = [r for r in results["runs"] if r["crossed"]]
        self.assertEqual(len(crossed), 7)
        for r in crossed:
            counts = _simulate(_expand(r["champion_genome"]))
            self.assertEqual(counts, {"111": 265, "000": 247},
                             f"{r['root_seed']}/{r['arm']} champion "
                             "reproduces sealed counts only pi-expanded")
            balance = min(counts["000"], counts["111"]) / 512
            self.assertEqual(balance, r["champion_verify_p"])


if __name__ == "__main__":
    unittest.main()
