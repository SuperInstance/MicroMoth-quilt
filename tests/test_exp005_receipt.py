"""Pins for receipts/exp005-ghz-balance.json (qcells lab exp005).

exp005 asks the queue's generalization question: the exp004 policy
engine that converged on 2-qubit |01> is pointed at an ENTANGLED
target — n=3 balanced GHZ {|000>,|111>}.  Anti-laundering design pin
recorded before the lab run: a bare counts-set target is satisfied by
any deterministic product state (|000> is in the set), so the fitness
is the BALANCE witness min(c000,c111)/shots.  The prelude must show
the witness gates entanglement (hand GHZ > 0, product == 0); the
search itself must stay frozen at 0.000 or the 'engine does not
generalize as-is' verdict is wrong.

Sealed outcome: FROZEN.  The exp001 control guard re-run inside this
harness reproduces exp001 byte-for-byte, while the n=3 GHZ lane sits
at train/verify balance 0.000 for all 12 generations.  The sealed
champion [h(1),cx(2,0),x(2)] is executable end-to-end by the vendored
engine and lands only in {'100','110'} on the named verify seed —
zero shots in either GHZ branch.

FAIL-first: on pristine main (before this branch) both target files
are absent, so the whole file is RED; the tamper demo below trips RED
on a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp005_receipt -v
"""
import hashlib
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth  # repo-root vendored engine (the engine the receipt names)

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp005-ghz-balance.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"

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


def _simulate(program, seed, shots, n=3, m=3):
    qc = micromoth.QuantumCircuit(n, m)
    qc.data = [tuple(t) for t in program]
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


def _balance(counts, shots=512):
    return min(counts.get(t, 0) for t in TARGETS) / shots


class TestExp005Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp005")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
        self.assertIn("balance", receipt["protocol"])
        self.assertIn("n_qubits=3", receipt["protocol"])
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

    def test_every_world_row_named_seed(self):
        receipt = json.loads(RECEIPT.read_text())
        worlds = [r for r in receipt["ledger"] if r["op"] == "WORLD"]
        self.assertEqual(len(worlds), 1)
        for row in worlds:
            self.assertIn("seed", row["args"], "UNSEALED WORLD row: no seed")
        self.assertEqual(worlds[0]["args"]["seed"], receipt["seeds"]["verify"])
        self.assertEqual(worlds[0]["args"]["shots"], receipt["seeds"]["shots"])

    def test_head_and_row_count_match_results(self):
        receipt = json.loads(RECEIPT.read_text())
        results = receipt["results"]
        ledger = receipt["ledger"]
        self.assertEqual(results["ledger_rows"], len(ledger))
        self.assertEqual(results["ledger_head"], ledger[-1]["hash"])
        self.assertEqual(results["ledger_head"], "eaba19fd5cc1c15e")

    def test_frozen_champion_program_executable(self):
        receipt = json.loads(RECEIPT.read_text())
        prog = receipt["results"]["champion"]
        self.assertEqual(prog, [["h", 1], ["cx", 2, 0], ["x", 2]])
        counts = _simulate(prog + [["m", 0, 0], ["m", 1, 1], ["m", 2, 2]],
                           seed=202, shots=512)
        self.assertEqual(counts, {"100": 247, "110": 265})
        self.assertEqual(_balance(counts), 0.0)
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], counts)

    def test_control_guard_reproduces_exp001(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        self.assertEqual(exp001["results"]["champion"],
                         [["h", 1], ["h", 1], ["x", 0]])
        # the frozen entanglement champion is not the 2-qubit home champion:
        # the guard says the harness is unchanged, the lane is what failed
        self.assertNotEqual(receipt["results"]["champion"],
                            exp001["results"]["champion"])

    def test_prelude_witness_gates_entanglement_live(self):
        receipt = json.loads(RECEIPT.read_text())
        prelude = receipt["results"]["prelude"]
        self.assertEqual(prelude["hand_ghz_balance"], 0.4824)
        self.assertEqual(prelude["product_h0_balance"], 0.0)
        self.assertTrue(prelude["witness_gates_entanglement"])
        hand = [["h", 0], ["cx", 0, 1], ["cx", 1, 2],
                ["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]
        product = [["h", 0], ["m", 0, 0], ["m", 1, 1], ["m", 2, 2]]
        hand_counts = _simulate(hand, seed=202, shots=512)
        product_counts = _simulate(product, seed=202, shots=512)
        self.assertEqual(_balance(hand_counts), 0.482421875)
        self.assertEqual(_balance(product_counts), 0.0)

    def test_frozen_curve_and_honest_limits(self):
        receipt = json.loads(RECEIPT.read_text())
        results = receipt["results"]
        self.assertEqual(results["champion_train_balance"], 0.0)
        self.assertEqual(results["champion_verify_balance"], 0.0)
        self.assertIsNone(results["first_verify_ge_045_gen"])
        curve = results["fitness_by_generation"]
        self.assertEqual(len(curve), 12)
        for row in curve:
            self.assertEqual(row["train_balance"], 0.0)
            self.assertEqual(row["verify_balance"], 0.0)
            self.assertEqual(row["champion_genome"], results["champion"])
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("single root seed", limits)
        self.assertIn("champion", limits)
        self.assertIn("balance witness", limits)
        self.assertIn("post-dates", limits)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[5]["args"] = dict(ledger[5]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))),                     f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
