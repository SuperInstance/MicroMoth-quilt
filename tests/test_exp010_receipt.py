"""Pins for receipts/exp010-pop-scale.json (qcells lab exp010).

exp010 is the doctrine's POP-ISOLATION test. exp005 froze the unaided
n=3 GHZ-balance lane at pop 16 (12 gens, champion 0.000). Finding 3's
candidate (b) — pop 64 — was ranked but never run. This receipt seals
the sweep: the exact exp005 unaided lane (no seed, targets ('000','111'),
mode='balance', exp004 jitter-dropped replace/indel policy, same named
seeds root 7 / train 101 / verify 202 / 512 shots) at pop 16 (re-run,
in-sweep anchor) / 32 / 64, 12 gens each:

  pop 16   -> champion [h(1),cx(2,0),x(2)], train 0.000, verify 0.000,
              all 12 promoted gens at 0.0
  pop 32   -> byte-identical outcome
  pop 64   -> byte-identical outcome

Sealed outcome: POP-INVARIANT FREEZE. Population multiplies draws, not
reach — max_champion_train_p_seen=0.0 at every pop across all 12 gens
(zero promotions at 4x the draw budget), so the locality verdict gains
its pop boundary condition: draws alone don't fix it; the working fixes
are reach-class (exp011 genealogy doctrine). The freeze contributes 3
configs to the unaided 0/11 crossing-rate table (exp012-exp014 doctrine:
the freeze is the law, the crossing is always a rate).

The cross-receipt pin is load-bearing: this lane's sealed champion is
the SAME PROGRAM as exp005's freeze — the per-gate statevector digests
and the seeded WORLD histogram re-derive byte-identical to exp005's
ledger (only the BIND kind label and its derived cell id differ). The
pop invariance is program-level, not just score-level.

FAIL-first: on pristine main (before this branch) the receipt is
absent, so the whole file is RED; the tamper demo below trips RED on
a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp010_receipt -v
"""
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth  # repo-root vendored engine (the engine the receipt names)

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp010-pop-scale.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP005_RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1
TARGETS = ("000", "111")


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


def _simulate(genome, seed=202, shots=512):
    qc = micromoth.QuantumCircuit(3, 3)
    qc.data = [tuple(t) for t in genome + [["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]]
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


CHAMPION = [["h", 1], ["cx", 2, 0], ["x", 2]]
EXPANDED = CHAMPION + [["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]
FROZEN_COUNTS = {"100": 247, "110": 265}


class TestExp010Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp010")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
        self.assertIn("pop in {16,32,64}", receipt["protocol"])
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
        self.assertEqual(results["ledger_head"], "5b7e7dd7b67d9542")

    def test_frozen_champion_executable_and_zero_balance(self):
        receipt = json.loads(RECEIPT.read_text())
        self.assertEqual(receipt["results"]["champion"], CHAMPION)
        self.assertEqual(receipt["results"]["champion_expanded_program"],
                         EXPANDED)
        counts = _simulate(CHAMPION)
        self.assertEqual(counts, FROZEN_COUNTS)
        self.assertEqual(_balance(counts), 0.0)
        for t in TARGETS:
            self.assertNotIn(t, counts, "frozen champion fired a target")
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], counts)
        # held-out is honest: the receipt's sealed balances are live zeros
        self.assertEqual(receipt["results"]["champion_train_balance"], 0.0)
        self.assertEqual(receipt["results"]["champion_verify_balance"], 0.0)
        self.assertIsNone(receipt["results"]["first_verify_ge_045_gen"])

    def test_all_three_pop_arms_frozen(self):
        receipt = json.loads(RECEIPT.read_text())
        arms = receipt["results"]["pop_arms"]
        self.assertEqual(set(arms), {"16", "32", "64"})
        for pop, arm in arms.items():
            self.assertFalse(arm["seeded"], f"pop{pop} arm was seeded")
            self.assertEqual(arm["champion_genome"], CHAMPION)
            self.assertEqual(arm["champion_len"], 3)
            self.assertEqual(arm["champion_train_balance"], 0.0)
            self.assertEqual(arm["champion_verify_balance"], 0.0)
            self.assertIsNone(arm["first_verify_ge_045_gen"])
            self.assertEqual(arm["max_champion_train_p_seen"], 0.0)
            self.assertEqual(len(arm["fitness_by_generation"]), 12)
            for row in arm["fitness_by_generation"]:
                self.assertEqual(row["train_balance"], 0.0,
                                 f"pop{pop} gen {row['gen']} promoted above 0")
                self.assertEqual(row["verify_balance"], 0.0)

    def test_pop_invariance_is_byte_identical(self):
        receipt = json.loads(RECEIPT.read_text())
        arms = receipt["results"]["pop_arms"]
        c16 = json.dumps(arms["16"]["fitness_by_generation"], sort_keys=True)
        c32 = json.dumps(arms["32"]["fitness_by_generation"], sort_keys=True)
        c64 = json.dumps(arms["64"]["fitness_by_generation"], sort_keys=True)
        self.assertEqual(c16, c32)
        self.assertEqual(c32, c64)
        inv = receipt["results"]["pop_invariance"]
        self.assertTrue(inv["byte_identical_outcomes"])
        self.assertIn("max_champion_train_p_seen=0.0", inv["note"])
        self.assertIn("draws, not reach", inv["note"])

    def test_same_program_as_exp005_freeze_cross_receipt(self):
        # load-bearing cross-receipt pin: the pop arms' sealed champion is
        # the SAME PROGRAM as exp005's freeze — per-gate statevector
        # digests and the seeded WORLD histogram re-derive byte-identical;
        # only the BIND kind label (and its derived cell id) may differ
        receipt = json.loads(RECEIPT.read_text())
        exp005 = json.loads(EXP005_RECEIPT.read_text())
        self.assertEqual(receipt["results"]["champion"],
                         exp005["results"]["champion"])
        for a, b in zip(receipt["ledger"][1:], exp005["ledger"][1:]):
            if "witness" not in a and "witness" not in b:
                continue  # PROOF head row carries no witness
            self.assertEqual(a["witness"], b["witness"],
                             f"row {a['seq']} diverged from exp005 freeze")
        world_a = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        world_b = [r for r in exp005["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world_a["witness"]["counts"],
                         world_b["witness"]["counts"])
        self.assertEqual(world_a["witness"]["counts"], FROZEN_COUNTS)
        self.assertNotEqual(receipt["ledger"][0]["args"]["kind"],
                            exp005["ledger"][0]["args"]["kind"])

    def test_control_guard_reproduces_exp001(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        self.assertEqual(exp001["results"]["champion"],
                         [["h", 1], ["h", 1], ["x", 0]])
        # the sealed frozen champion is NOT the home-turf champion: the
        # harness is unchanged, the lane (target + witness) is the delta
        self.assertNotEqual(receipt["results"]["champion"],
                            exp001["results"]["champion"])

    def test_honest_limits_scope(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("single root", limits)
        self.assertIn("promoted (champion) rows only", limits)
        self.assertIn("0/11", limits)
        self.assertIn("exp012-exp014", limits)
        self.assertIn("reach", limits)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[4]["args"] = dict(ledger[4]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))),                     f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
