"""Pins for receipts/exp006-ghz-seeded.json (qcells lab exp006).

exp006 is Finding 3 candidate (a): exp005 froze the UNSEEDED engine on
n=3 balanced GHZ, and the ranked first fix was a GHZ-prefix seeded
restart (loadCoev doctrine — seeds around champs — applied at birth).
Two seeded lanes on identical named seeds and the exp004 policy:

  lane A seed [h(0),cx(0,1)]      — bare skeleton, birth balance 0.0
  lane B seed [h(0),cx(0,1),h(2)] — partial entangler, birth 0.2422

Anti-laundering design pin recorded before the lab run: lane B is the
seed-choice control. Sealed outcome: lane A CROSSES — verify balance
0.4824 by gen 2 via a non-canonical crx route the unaided search never
found; lane B TRAPS — never samples above its 0.2422 birth fitness in
8 gens x pop 16 = 120 draws. Seed CHOICE beats seed FITNESS (born
here as Finding 4). The exp001 control guard re-ran in-harness
byte-identical, so the harness is not the delta — the birth genome is.

FAIL-first: on pristine main (before this branch) both target files
are absent, so the whole file is RED; the tamper demo below trips RED
on a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp006_receipt -v
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
RECEIPT = HERE.parent / "receipts" / "exp006-ghz-seeded.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1
TARGETS = ("000", "111")
PI = 3.141592653589793


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


def _champion_circuit():
    # genome-circuit expansion (qcell.search.genome_circuit semantics):
    # crx angle is stored in units of pi and expanded at build time.
    qc = micromoth.QuantumCircuit(3, 3)
    qc.h(0)
    qc.crx(PI, 0, 2)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    qc.measure(2, 2)
    return qc


def _simulate_seed(seed_genome, seed=202, shots=512):
    qc = micromoth.QuantumCircuit(3, 3)
    qc.data = [tuple(t) for t in seed_genome]
    for q in range(3):
        qc.measure(q, q)
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


class TestExp006Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp006")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
        self.assertIn("seed_genome", receipt["protocol"])
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
        self.assertEqual(results["ledger_head"], "bfe7bd25cd7b6f79")

    def test_sealed_champion_program_executable(self):
        receipt = json.loads(RECEIPT.read_text())
        self.assertEqual(receipt["results"]["champion"],
                         [["h", 0], ["crx", 1.0, 0, 2], ["cx", 0, 1]])
        qc = _champion_circuit()
        prog = [list(t) for t in qc.data]
        self.assertEqual(prog, receipt["results"]["champion_expanded_program"])
        random.seed(202)
        counts = micromoth.simulate(qc, shots=512, get="counts")
        self.assertEqual(counts, {"000": 247, "111": 265})
        self.assertEqual(_balance(counts), 0.482421875)
        self.assertGreaterEqual(_balance(counts), 0.45)
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], counts)

    def test_control_guard_reproduces_exp001(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        self.assertEqual(exp001["results"]["champion"],
                         [["h", 1], ["h", 1], ["x", 0]])
        # the sealed crossing champion is NOT the 2-qubit home champion:
        # the guard says the harness is unchanged, the birth seed is the delta
        self.assertNotEqual(receipt["results"]["champion"],
                            exp001["results"]["champion"])

    def test_seed_choice_control_live(self):
        receipt = json.loads(RECEIPT.read_text())
        prelude = receipt["results"]["prelude"]
        # lane A birth: zero-fitness skeleton, balance 0.0, one move from
        # correlation (an h(2) or cx(1,2) indel completes GHZ)
        seed_a = _simulate_seed([["h", 0], ["cx", 0, 1]])
        self.assertEqual(seed_a, prelude["seedA_birth_counts"])
        self.assertEqual(_balance(seed_a), prelude["seedA_birth_balance"])
        self.assertEqual(prelude["seedA_birth_balance"], 0.0)
        # lane B birth: partial entangler ALREADY at 0.2422 — the slope
        # the trap could not climb past in 120 draws
        seed_b = _simulate_seed([["h", 0], ["cx", 0, 1], ["h", 2]])
        self.assertEqual(seed_b, prelude["seedB_birth_counts"])
        self.assertEqual(_balance(seed_b), prelude["seedB_birth_balance"])
        self.assertEqual(prelude["seedB_birth_balance"], 0.2421875)

    def test_lane_a_crosses_lane_b_traps(self):
        receipt = json.loads(RECEIPT.read_text())
        lanes = receipt["results"]["lanes"]
        lane_a = lanes["seedA_ghz_prefix"]
        lane_b = lanes["seedB_partial_entangler"]
        # lane A: skeleton seed crosses at gen 2 and holds >= 0.45 to the end
        self.assertEqual(lane_a["first_verify_ge_045_gen"], 2)
        self.assertEqual(lane_a["champion_verify_balance"], 0.482421875)
        for row in lane_a["fitness_by_generation"]:
            if row["gen"] >= 2:
                self.assertGreaterEqual(row["verify_balance"], 0.45)
        # lane B: partial entangler never sampled above birth fitness
        self.assertIsNone(lane_b["first_verify_ge_045_gen"])
        self.assertEqual(lane_b["champion_verify_balance"], 0.2421875)
        self.assertEqual(lane_b["champion_genome"],
                         [["h", 0], ["cx", 0, 1], ["h", 2]])
        for row in lane_b["fitness_by_generation"]:
            self.assertLessEqual(row["verify_balance"], 0.2422)
        # and the birth-fitness seed is the one that never improved:
        # seed CHOICE (0.0) beat seed FITNESS (0.2422)
        self.assertEqual(lane_b["champion_genome"], lane_b["seed_genome"])

    def test_honest_limits_scope(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("single root seed", limits)
        self.assertIn("SEEDING", limits)
        self.assertIn("post-dates", limits)
        self.assertIn("120-draw", limits)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[5]["args"] = dict(ledger[5]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))),                     f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
