"""Pins for receipts/exp013-curriculum.json (qcells lab exp013).

exp013 is the CURRICULUM transplant: solve the cheap entangled problem
first (2-qubit Bell balance, exp007's home turf, seeded with the exp007
prescription [["h",0],["cx",0,1]]), then TRANSPLANT the earned champion
op-for-op onto qubits {0,1} as the birth seed of the frozen n=3 GHZ
balance lane (exp005's home problem). Design pinned before running:
per-root phase 1 (Bell, bar 0.45), deterministic transplant rule
(qubit 2 enters as |0>, indices unchanged — a zero-fitness structural
prefix earned by solving the smaller problem), then two phase-2 arms on
the exact exp005 lane (pop 16, 12 gens, jitter-dropped
restrict=("replace","indel")): curriculum vs unaided. Multi-root at
birth per exp012 doctrine: roots 7, 11, 23, 42.

Sealed outcome: CURRICULUM IS A TRAP AT THE WRONG SCALE, NOT A LADDER.
Phase 1 crosses on all 4 roots (verify 0.482421875 every time — the
Bell balance is learnable from the exp007 prescription on every root).
Phase 2: unaided frozen at 0.000 all 12 gens on 4/4 roots (the exp005
freeze replicates again). Curriculum lifts 3/4 roots off the floor but
only onto a ~0.242-0.248 plateau (the psi|0> transplant balances
"000" only — earned slope at the WRONG scale); exactly ONE root (42)
crosses (verify 0.482421875). Per the exp012 ROOT-LOTTERY doctrine
(any crossing claim needs 2+ roots agreeing), the single root-42
crossing is a favorable draw, not a curriculum law: the only
REPLICATED crossing class stays seeding (exp006/007/008). The
curriculum's real finding is the plateau itself: 3/4 roots reaching
~0.24 vs 0.0 unaided is the largest non-crossing lift in the lab, and
it is a length-scale illusion (balance on one qubit-pair, not three).

The integrity pins are load-bearing: results-style receipt (no witness
LEDGER; exp001 remains the lane's only LEDGER receipt) — the sealed
artifacts are the experiment runner + results.json + telemetry jsonl,
and the receipt's sha256 table must match every file byte-for-byte or
the seal is void.

The exp001-guard pin is load-bearing: the runner's in-harness default
lane at the canonical root 7 reproduces exp001's champion at verify 1.0
before any results are written (guard failure aborts the run).

The cross-receipt pins are load-bearing: exp013's design must name the
exp012 multi-root doctrine it inherits, and the unaided arm must
re-derive the exp005 freeze at 0.000 (not just "low").

The pi-expansion pin is load-bearing in its positive form: root 42's
curriculum champion reproduces its sealed counts exactly when thetas
are expanded by pi. NOTE (honest limit of the pin class): the raw
1.0-radian misread is count-IDENTICAL for this particular genome,
because its only rotational gate is an rz on a wire that never enters
superposition (no h upstream) — phase is invisible in computational
basis counts. The negative control would be vacuous here, so the pin
asserts the exact-count reproduction instead and records why.

Run: python3 -m unittest tests.test_exp013_receipt -v
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
RECEIPT = HERE.parent / "receipts" / "exp013-curriculum.json"
ARTIFACTS = HERE.parent / "receipts" / "exp013-curriculum"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"
# exp012's ROOT-LOTTERY receipt is still Casey-gated (PR #17) at seal
# time, so the doctrine cross-receipt pins exp011 (merged), whose
# honest_limits pre-registered the lottery verdict this design inherits
EXP011_RECEIPT = HERE.parent / "receipts" / "exp011-nonchampion-parent.json"

PI = math.pi
ROOTS = (7, 11, 23, 42)
EXP001_CHAMPION = [["h", 1], ["h", 1], ["x", 0]]
BAR = 0.45
BELL_P = 0.482421875
PLATEAU = {7: 0.248046875, 11: 0.2421875, 23: 0.2421875}
R42_CHAMPION = [["h", 0], ["cx", 0, 2], ["rz", 1.0, 1], ["cx", 0, 1]]
EXP007_PRESCRIPTION = [["h", 0], ["cx", 0, 1]]


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


class TestExp013Receipt(unittest.TestCase):
    def test_receipt_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "receipt_kind", "experiment", "status",
                    "title", "directive", "engine", "seeds", "artifacts",
                    "integrity", "honest_limits"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(receipt["receipt_kind"], "results")
        self.assertEqual(receipt["experiment"], "exp013-curriculum")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(tuple(receipt["seeds"]["roots"]), ROOTS)
        self.assertEqual({receipt["seeds"][k] for k in ("train", "verify",
                                                        "shots")},
                         {101, 202, 512})
        self.assertIn("trap", receipt["title"].lower())

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

    def test_design_pins_multi_root_doctrine_and_transplant_rule(self):
        results = json.loads((ARTIFACTS / "exp013.results.json")
                             .read_text())
        design = results["design"]
        # the exp012 doctrine is named at birth, not retrofitted
        self.assertIn("exp012", design["multi_root_doctrine"])
        self.assertIn("2+ roots", design["multi_root_doctrine"])
        # deterministic transplant rule pinned before running
        self.assertIn("qubits {0,1}", design["transplant_rule"])
        self.assertIn("|0>", design["transplant_rule"])
        self.assertEqual(design["success_bar_verify_balance"], BAR)
        self.assertEqual(design["curriculum_seed"], EXP007_PRESCRIPTION)
        self.assertEqual(results["seeds"]["roots"], list(ROOTS))

    def test_phase1_bell_crosses_on_all_four_roots(self):
        results = json.loads((ARTIFACTS / "exp013.results.json")
                             .read_text())
        for root in ROOTS:
            d = results["roots"][str(root)]
            self.assertTrue(d["phase1_crossed"], f"root {root} phase 1")
            self.assertEqual(d["phase1_champion_verify_p"], BELL_P)
            # phase-1 telemetry: final row is the crossing champion
            # (telemetry stores verify_p rounded to 4 decimals; the
            # receipt's results.json carries the full float)
            rows = [json.loads(l) for l in
                    (ARTIFACTS / f"exp013.telemetry.r{root}.phase1_bell.jsonl")
                    .read_text().splitlines()]
            self.assertAlmostEqual(rows[-1]["verify_p"], BELL_P, places=4)
            self.assertGreaterEqual(rows[-1]["verify_p"], BAR)

    def test_unaided_arm_is_the_exp005_freeze_on_all_four_roots(self):
        results = json.loads((ARTIFACTS / "exp013.results.json")
                             .read_text())
        for root in ROOTS:
            d = results["roots"][str(root)]
            unaided = d["phase2"]["unaided"]
            self.assertEqual(unaided["champion_verify_p"], 0.0)
            self.assertTrue(all(c["verify_p"] == 0.0
                                for c in unaided["curve"]),
                            f"root {root} unaided not frozen at 0.000")
            self.assertEqual(len(unaided["curve"]), 12)
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion_verify_balance"], 0.0)

    def test_curriculum_plateau_on_three_roots_single_root42_crossing(self):
        results = json.loads((ARTIFACTS / "exp013.results.json")
                             .read_text())
        for root in (7, 11, 23):
            d = results["roots"][str(root)]
            curr = d["phase2"]["curriculum"]
            self.assertLess(curr["champion_verify_p"], BAR,
                            f"root {root} crossed — the single-draw "
                            "verdict would be void")
            self.assertAlmostEqual(curr["champion_verify_p"],
                                   PLATEAU[root], places=7)
            # the plateau is real slope: strictly above the unaided floor
            self.assertGreater(curr["champion_verify_p"], 0.0)
        r42 = results["roots"]["42"]["phase2"]["curriculum"]
        self.assertGreaterEqual(r42["champion_verify_p"], BAR)
        self.assertEqual(r42["champion_verify_p"], BELL_P)
        self.assertEqual(r42["champion_genome"], R42_CHAMPION)
        # exactly one crossing root out of four — per the exp012
        # doctrine named in this receipt's own design, that is a
        # favorable draw, not a curriculum law
        crosses = [r for r in ROOTS
                   if results["roots"][str(r)]["phase2"]["curriculum"]
                   ["champion_verify_p"] >= BAR]
        self.assertEqual(crosses, [42])

    def test_curriculum_telemetry_matches_results_champion(self):
        results = json.loads((ARTIFACTS / "exp013.results.json")
                             .read_text())
        for root in ROOTS:
            d = results["roots"][str(root)]
            rows = [json.loads(l) for l in
                    (ARTIFACTS /
                     f"exp013.telemetry.r{root}.phase2_curriculum.jsonl")
                    .read_text().splitlines()]
            self.assertEqual(len(rows), 12)
            final = rows[-1]
            self.assertEqual(final["genome"],
                             d["phase2"]["curriculum"]["champion_genome"])
            self.assertAlmostEqual(final["verify_p"],
                                   d["phase2"]["curriculum"]
                                   ["champion_verify_p"],
                                   places=4)

    def test_guard_reproduces_exp001_at_canonical_root7(self):
        # the rootless guard file is the canonical seed-7 default-lane
        # run, byte-identical to the r7 guard telemetry, ending on
        # exp001's champion at verify 1.0 — run before any results
        rows = [json.loads(l) for l in
                (ARTIFACTS / "exp013.telemetry.guard.jsonl")
                .read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]["genome"], EXP001_CHAMPION)
        self.assertEqual(rows[-1]["verify_p"], 1.0)
        r7 = (ARTIFACTS / "exp013.telemetry.r7.guard.jsonl").read_bytes()
        self.assertEqual(sha256_of(ARTIFACTS / "exp013.telemetry.guard.jsonl"),
                         sha256_of(ARTIFACTS /
                                   "exp013.telemetry.r7.guard.jsonl"))
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertEqual(exp001["results"]["champion"], EXP001_CHAMPION)

    def test_root_lottery_doctrine_cross_receipt(self):
        # exp011 (merged) pre-registered the ROOT-LOTTERY verdict in its
        # honest_limits BEFORE exp012 sealed it: quote-as-1-in-4-rate,
        # never as 'genealogy fixes the freeze'. exp013's design pins
        # the same 2+-roots doctrine at birth; the single root-42
        # crossing is judged against it (exp012's own receipt remains
        # Casey-gated as PR #17 at seal time, so this pin anchors on
        # the pre-registration that IS on main)
        exp011 = json.loads(EXP011_RECEIPT.read_text())
        limits = " ".join(exp011["honest_limits"])
        self.assertIn("ROOT-LOTTERY", limits)
        self.assertIn("1-in-4", limits)
        results = json.loads((ARTIFACTS / "exp013.results.json")
                             .read_text())
        self.assertIn("exp012", results["design"]["multi_root_doctrine"])
        self.assertIn("2+ roots", results["design"]["multi_root_doctrine"])
        self.assertEqual(exp011["seeds"]["root"], 7)

    def test_pi_expansion_root42_champion_reproduces_sealed_counts(self):
        # root 42's crossing champion (verify balance 0.482421875,
        # balance = MIN of per-target counts / shots) reproduces its
        # sealed counts exactly under pi-expansion. HONEST LIMIT: the
        # raw 1.0-radian misread would give count-IDENTICAL output here
        # (rz on a wire that never enters superposition — phase is
        # invisible in basis counts), so the negative control is vacuous
        # for this genome and only the positive exact-count repro is
        # pinned. See module docstring.
        counts = _simulate(_expand(R42_CHAMPION), seed=202)
        self.assertEqual(counts, {"111": 265, "000": 247})
        balance = min(counts["000"], counts["111"]) / 512
        self.assertEqual(balance, BELL_P,
                         "pi-expanded program must re-derive the sealed "
                         "verify balance exactly")


if __name__ == "__main__":
    unittest.main()
