"""Pins for receipts/exp012-root-replication.json (qcells lab exp012).

exp012 is the ROOT-LOTTERY replication of exp011's unaided crossing.
exp011 arm B (parent_pool genealogy) crossed UNSEEDED on exactly one
root seed (7) — its honest limit pre-named this experiment BEFORE any
doctrine-hardening. exp012 varies ONLY the root seed (new roots 11,
23, 42; train=101 verify=202 shots=512, targets ("000","111"), n=3
balance, pop 16, gens 12, jitter-dropped replace/indel one-move cloud
— the named exp005 lane values) and runs two arms per root:

  unaided (parent_pool=False)  -> per-seed freeze baseline
  poolB   (parent_pool=True)   -> the exp011 arm B claim

Sealed outcome: ROOT-LOTTERY. Zero crossings on any new root in either
arm (unaided 0/3, poolB 0/3); total poolB crossings across the lab
stay 1-in-4 (root 7 only). The exp011 crossing was a favorable
genealogy draw, not a reach law: doctrine keeps seeding primary. The
unaided freeze itself replicates 3/3 (exp005 freeze not a root-7
artifact).

The integrity pins are load-bearing: this is a results-style receipt
(no witness LEDGER; exp001 remains the lane's only LEDGER receipt) —
the sealed artifacts are the experiment runner + results.json +
telemetry jsonl, and the receipt's sha256 table must match every file
byte-for-byte or the seal is void.

The exp001-guard pin is load-bearing: the runner reproduces the
default lane byte-identical in-harness; the control telemetry's final
row must be exp001's champion at verify 1.0.

The cross-receipt pins are load-bearing: exp012's root set must be
disjoint from exp011's root (7), and exp011's honest_limits must
already name the 0/3 replication this receipt seals (pre-registered,
not retrofitted).

Run: python3 -m unittest tests.test_exp012_receipt -v
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
RECEIPT = HERE.parent / "receipts" / "exp012-root-replication.json"
ARTIFACTS = HERE.parent / "receipts" / "exp012-root-replication"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"
EXP011_RECEIPT = HERE.parent / "receipts" / "exp011-nonchampion-parent.json"

TARGETS = ("000", "111")
PI = math.pi
NEW_ROOTS = (11, 23, 42)
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _simulate(program, seed=202, shots=512):
    qc = micromoth.QuantumCircuit(3, 3)
    qc.data = [tuple(t) for t in program]
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


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


class TestExp012Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp012-root-replication")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"]["root"], 7,
                         "named root stays 7; NEW roots live in results.json")
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
        # and every artifact on disk is named by the seal (no strays)
        sealed = set(receipt["integrity"])
        on_disk = {p.name for p in ARTIFACTS.iterdir() if p.is_file()}
        self.assertEqual(sealed, on_disk)

    def test_results_seal_root_lottery_verdict(self):
        results = json.loads((ARTIFACTS / "exp012.results.json")
                             .read_text())
        self.assertEqual(results["replication_verdict"], "ROOT-LOTTERY")
        self.assertEqual(results["unaided_crosses"], [])
        self.assertEqual(results["poolB_crosses_new_roots"], [])
        self.assertEqual(results["poolB_total_crosses_incl_exp011"], [7])
        self.assertEqual(results["success_threshold"], 0.45)
        # exactly the two arms on exactly the three new roots
        arms = {(r["root_seed"], r["arm"]) for r in results["runs"]}
        self.assertEqual(arms, {(root, arm)
                                for root in NEW_ROOTS
                                for arm in ("unaided", "poolB")})

    def test_every_new_root_frozen_in_both_arms(self):
        results = json.loads((ARTIFACTS / "exp012.results.json")
                             .read_text())
        for run in results["runs"]:
            self.assertFalse(run["crossed"],
                             f"root {run['root_seed']} {run['arm']} crossed "
                             "— the ROOT-LOTTERY verdict would be void")
            self.assertIsNone(run["first_ge_045_gen"])
            self.assertLess(run["champion_verify_p"], 0.45)
            self.assertEqual(len(run["champ_balances"]), 12)
        # the exp005 freeze replicates on every fresh root: unaided
        # champions sit at the 0.000 floor in EVERY generation
        for run in results["runs"]:
            if run["arm"] == "unaided":
                self.assertEqual(run["champion_verify_p"], 0.0)
                self.assertTrue(all(b == 0.0 for b in run["champ_balances"]))

    def test_control_guard_reproduces_exp001(self):
        # the runner's in-harness exp001 guard: default lane (8 gens)
        # ends on exp001's champion at verify 1.0
        rows = [json.loads(l) for l in
                (ARTIFACTS / "exp012.telemetry.control.jsonl")
                .read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        final = rows[-1]
        self.assertEqual(final["genome"], EXP001_CHAMPION)
        self.assertEqual(final["verify_p"], 1.0)
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_exp005_freeze_cross_receipt(self):
        # unaided freeze at 0.000 is the exp005 lane, re-derived
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)
        results = json.loads((ARTIFACTS / "exp012.results.json")
                             .read_text())
        for run in results["runs"]:
            if run["arm"] == "unaided":
                self.assertEqual(run["champion_train_p"], 0.0)
                self.assertEqual(run["champion_verify_p"], 0.0)

    def test_root_disjointness_and_preregistration_cross_receipt(self):
        # exp012 roots must be disjoint from exp011's single root (7)
        exp011 = json.loads(EXP011_RECEIPT.read_text())
        self.assertEqual(exp011["seeds"]["root"], 7)
        self.assertEqual(exp011["results"]["crossing_arm"], "parent_pool")
        results = json.loads((ARTIFACTS / "exp012.results.json")
                             .read_text())
        self.assertNotIn(7, {r["root_seed"] for r in results["runs"]})
        # exp011 pre-registered THIS result in its honest limits before
        # it was sealed (0/3, 1-in-4) — the lottery verdict was named
        # in advance, not retrofitted
        limits = " ".join(exp011["honest_limits"])
        self.assertIn("ROOT-LOTTERY", limits)
        self.assertIn("0/3", limits)
        self.assertIn("1-in-4", limits)
        receipt = json.loads(RECEIPT.read_text())
        self.assertIn("Root-lottery", receipt["title"])

    def test_pi_expansion_honesty_on_best_new_root_champion(self):
        # best new-root poolB champion (root 11, verify 0.203125,
        # train 0.220703125) — the pi-expanded executable program
        # reproduces its sealed counts exactly; the RAW 0.5-radian
        # misread does NOT (exp008 honesty pin class)
        results = json.loads((ARTIFACTS / "exp012.results.json")
                             .read_text())
        best = max((r for r in results["runs"] if r["arm"] == "poolB"),
                   key=lambda r: r["champion_verify_p"])
        self.assertEqual(best["root_seed"], 11)
        self.assertEqual(best["champion_genome"],
                         [["h", 1], ["rz", 1.0, 0], ["rz", 0.5, 2],
                          ["h", 0], ["crx", 0.75, 1, 2], ["rx", 0.25, 0]])
        self.assertEqual(best["champion_verify_p"], 0.203125)
        self.assertEqual(best["champion_train_p"], 0.220703125)
        expanded = _expand(best["champion_genome"])
        self.assertEqual(_simulate(expanded, seed=101),
                         {"110": 113, "000": 140, "111": 113,
                          "001": 115, "010": 15, "011": 16})
        self.assertEqual(_simulate(expanded, seed=202),
                         {"110": 119, "001": 120, "000": 127,
                          "111": 104, "010": 19, "011": 23})
        # RAW 0.5-radian execution does NOT reproduce (anti-laundering)
        raw = [list(g) for g in best["champion_genome"]]
        for g in raw:
            if g[0] in ("rx", "rz") and len(g) == 3:
                g[1] = g[1] * PI
        raw_prog = raw + [["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]
        self.assertNotEqual(_simulate(raw_prog, seed=202),
                            _simulate(expanded, seed=202))


if __name__ == "__main__":
    unittest.main()
