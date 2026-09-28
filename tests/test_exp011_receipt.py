"""Pins for receipts/exp011-nonchampion-parent.json (qcells lab exp011).

exp011 is the doctrine's REACH-MUTATOR test. exp005 froze the unaided
n=3 GHZ-balance search at pop 16 (champion 0.000); exp009 (budget) and
exp010 (pop 16/32/64) verified the freeze is not a leash artifact —
draws alone don't fix it. This receipt seals the two remaining
reach-class candidates on the exact exp005 unaided lane (targets
("000","111"), mode="balance", jitter-dropped replace/indel classes,
same named seeds root 7 / train 101 / verify 202 / 512 shots), 12 gens
x pop 16, three arms:

  two_move    -> champion [h(2),cx(0,1),h(1),cx(2,0),rx(1.0,1)],
                 verify 0.2422, never crossed — FROZEN at the partial
                 plateau (Finding 4 class)
  parent_pool -> champion [swap(2,1),rx(0.5,2),cx(1,2),cx(2,1),
                 rz(0.5,0),cx(1,0)], verify 0.4824 at gen 5, frozen
                 there through gen 11 — FIRST UNAIDED CROSSING
  both        -> champion [h(1),cx(1,0),rx(0.5,2),x(2)],
                 verify 0.2422, never crossed — FROZEN

Sealed outcome: the NON-CHAMPION-PARENT cloud crosses UNSEEDED — the
first unaided crossing in the lab. Diversity via genealogy (parents
sampled uniformly from champion + already-generated children), not via
move count: the two-move arm, doubling neighborhood diameter per draw,
stayed frozen. The load-bearing honesty context: the crossing is a
ROOT-LOTTERY, not a reach law — exp012 replicated the parent_pool arm
across 3 fresh root seeds and crossed 0/3 (quote as 1-in-4 rate).

The pi-expansion pin is load-bearing (exp008 honesty pin): genome
thetas are stored in units of pi; the executable program expands
rx/rz/crx by pi. The RAW 0.5-radian execution does NOT reproduce the
sealed balances and is pinned non-reproducing below.

The cross-receipt pins are load-bearing: (a) both-arm gen-0 genome is
byte-identical to the exp005/exp010 frozen champion — the cloud was
born at the freeze and walked away; (b) the parent_pool crossing lands
on the SAME held-out balance 0.482421875 (247/512) as exp006's seeded
GHZ-prefix crossing — two independent routes to the same GHZ witness.

FAIL-first: on pristine main (before this branch) the receipt is
absent, so the whole file is RED; the tamper demo below trips RED on
a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp011_receipt -v
"""
import json
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth  # repo-root vendored engine (the engine the receipt names)

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp011-nonchampion-parent.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"
EXP006_RECEIPT = HERE.parent / "receipts" / "exp006-ghz-seeded.json"

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1
TARGETS = ("000", "111")
PI = math.pi

CHAMPION = [["swap", 2, 1], ["rx", 0.5, 2], ["cx", 1, 2],
            ["cx", 2, 1], ["rz", 0.5, 0], ["cx", 1, 0]]
# genome thetas are in UNITS OF PI (exp008 pi-expansion honesty pin)
CHAMPION_EXPANDED = [
    ["swap", 2, 1], ["rx", 0.5 * PI, 2], ["cx", 1, 2], ["cx", 2, 1],
    ["rz", 0.5 * PI, 0], ["cx", 1, 0],
    ["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]
TRAIN_COUNTS = {"111": 257, "000": 255}
VERIFY_COUNTS = {"111": 265, "000": 247}
FROZEN_CHAMPION = [["h", 1], ["cx", 2, 0], ["x", 2]]  # exp005/exp010 freeze


def fnv1a64(data: bytes) -> str:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & MASK64
    return f"{h:016x}"


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def row_body(row):
    return {k: row[k] for k in ("args", "cell", "op", "prev_hash", "seq")}


def _balance(counts, shots=512):
    return min(counts.get(t, 0) for t in TARGETS) / shots


def _simulate(program, seed=202, shots=512):
    qc = micromoth.QuantumCircuit(3, 3)
    qc.data = [tuple(t) for t in program]
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


class TestExp011Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp011")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
        self.assertIn("parent_pool", receipt["protocol"])
        ledger = receipt["ledger"]
        self.assertEqual(ledger[0]["op"], "BIND")
        self.assertEqual(ledger[-1]["op"], "PROOF")

    def test_chain_rederived_in_repo(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = receipt["ledger"]
        self.assertEqual(ledger[0]["prev_hash"], "0" * 16,
                         "genesis prev_hash must be zero")
        for i, row in enumerate(ledger):
            self.assertEqual(row["hash"], fnv1a64(_canon(row_body(row))),
                             f"row {i} ({row['op']}) hash does not re-derive")
            if i:
                self.assertEqual(row["prev_hash"], ledger[i - 1]["hash"],
                                 f"row {i} breaks prev_hash linkage")

    def test_world_row_named_seed(self):
        receipt = json.loads(RECEIPT.read_text())
        worlds = [r for r in receipt["ledger"] if r["op"] == "WORLD"]
        self.assertEqual(len(worlds), 1)
        self.assertIn("seed", worlds[0]["args"], "UNSEALED WORLD row: no seed")
        self.assertEqual(worlds[0]["args"]["seed"], receipt["seeds"]["verify"])
        self.assertEqual(worlds[0]["args"]["shots"], receipt["seeds"]["shots"])

    def test_head_and_row_count_match_results(self):
        receipt = json.loads(RECEIPT.read_text())
        results = receipt["results"]
        ledger = receipt["ledger"]
        self.assertEqual(results["ledger_rows"], len(ledger))
        self.assertEqual(results["ledger_head"], ledger[-1]["hash"])
        self.assertEqual(results["ledger_head"], "d270d30e9de8ab84")

    def test_crossing_champion_executable_and_pi_expansion(self):
        receipt = json.loads(RECEIPT.read_text())
        arm = receipt["results"]["arms"]["parent_pool"]
        self.assertEqual(arm["champion_genome"], CHAMPION)
        self.assertEqual(arm["champion_expanded_program"], CHAMPION_EXPANDED)
        # pi-expanded execution reproduces the sealed balances exactly
        self.assertEqual(_simulate(CHAMPION_EXPANDED, seed=101), TRAIN_COUNTS)
        self.assertEqual(_simulate(CHAMPION_EXPANDED, seed=202), VERIFY_COUNTS)
        self.assertEqual(_balance(TRAIN_COUNTS), 0.498046875)
        self.assertEqual(_balance(VERIFY_COUNTS), 0.482421875)
        self.assertEqual(arm["champion_train_balance"], 0.498046875)
        self.assertEqual(arm["champion_verify_balance"], 0.482421875)
        self.assertEqual(arm["verify_counts"], VERIFY_COUNTS)
        self.assertEqual(arm["train_counts"], TRAIN_COUNTS)
        self.assertGreaterEqual(arm["champion_verify_balance"], 0.45)
        self.assertEqual(arm["first_verify_ge_045_gen"], 5)
        # frozen there through gen 11
        curve = arm["fitness_by_generation"]
        self.assertEqual(len(curve), 12)
        for row in curve[5:]:
            self.assertEqual(row["verify_p"], 0.4824,
                             f"gen {row['gen']} left the crossing value")
        # RAW 0.5-radian execution does NOT reproduce (anti-laundering)
        raw = [list(g) for g in CHAMPION] + [["m", 0, 0], ["m", 1, 1],
                                             ["m", 2, 2]]
        self.assertNotEqual(_balance(_simulate(raw, seed=202)),
                            0.482421875)
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], VERIFY_COUNTS)

    def test_two_move_and_both_arms_frozen_at_plateau(self):
        receipt = json.loads(RECEIPT.read_text())
        arms = receipt["results"]["arms"]
        self.assertEqual(receipt["results"]["crossing_arm"], "parent_pool")
        self.assertEqual(receipt["results"]["frozen_arms"],
                         ["two_move", "both"])
        for name in ("two_move", "both"):
            arm = arms[name]
            self.assertEqual(arm["champion_verify_balance"], 0.2421875)
            self.assertIsNone(arm["first_verify_ge_045_gen"])
            self.assertEqual(len(arm["fitness_by_generation"]), 12)
        # doubling the neighborhood diameter (two_move) stays frozen:
        # reach via move-count is NOT the fix; genealogy is
        self.assertEqual(receipt["results"]["frozen_plateau_balance"],
                         0.2421875)

    def test_both_arm_born_at_the_exp005_freeze_cross_receipt(self):
        # load-bearing: the 'both' arm's cloud was seeded by the frozen
        # champion at gen 0 and WALKED AWAY from it — genealogy, not
        # the champion's neighborhood, found the crossing elsewhere
        receipt = json.loads(RECEIPT.read_text())
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(exp005["results"]["champion"], FROZEN_CHAMPION)
        both = receipt["results"]["arms"]["both"]
        self.assertEqual(both["fitness_by_generation"][0]["genome"],
                         FROZEN_CHAMPION)
        self.assertNotEqual(both["champion_genome"], FROZEN_CHAMPION)
        # the crossing champion is a genuinely different program
        self.assertNotEqual(
            receipt["results"]["arms"]["parent_pool"]["champion_genome"],
            FROZEN_CHAMPION)

    def test_crossing_matches_exp006_ghz_witness_cross_receipt(self):
        # two independent routes to the SAME held-out GHZ witness:
        # seeding (exp006, gen 2) and genealogy (exp011, gen 5)
        receipt = json.loads(RECEIPT.read_text())
        exp006 = json.loads(EXP006_RECEIPT.read_text())
        self.assertEqual(exp006["results"]["champion_verify_balance"],
                         0.482421875)
        self.assertEqual(receipt["results"]["crossing_verify_balance"],
                         exp006["results"]["champion_verify_balance"])
        self.assertNotEqual(
            receipt["results"]["arms"]["parent_pool"]["champion_genome"],
            exp006["results"]["champion"])

    def test_control_guard_reproduces_exp001(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        self.assertEqual(exp001["results"]["champion"],
                         [["h", 1], ["h", 1], ["x", 0]])

    def test_honest_limits_scope(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("single root seed", limits)
        self.assertIn("ROOT-LOTTERY", limits)
        self.assertIn("0/3", limits)
        self.assertIn("1-in-4", limits)
        self.assertIn("promoted (champion) rows only", limits)
        self.assertIn("plateau", limits)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[4]["args"] = dict(ledger[4]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))),                    f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
