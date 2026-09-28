"""Pins for receipts/exp002-parsimony-sweep.json (qcells lab exp002).

exp001 sealed the bias-search champion but left Finding 1 open: the
[h,h,x] champion carries a dead identity pair and nothing penalizes
genome length.  exp002 adds a per-gate parsimony penalty to the TRAIN
selection score only (verify promotion gate untouched) and sweeps
lambda 0.00 / 0.02 / 0.05 on identical named seeds.  The sealed
result: control reproduces exp001 byte-for-byte; both pressure arms
collapse to the len-1 champion [x(0)] at verify 1.0.  This file pins
the receipt, the witness-ledger chain, and the executable champion.

FAIL-first: on pristine main (before this branch) both target files
are absent, so the whole file is RED; the tamper demo below trips RED
on a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp002_receipt -v
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
RECEIPT = HERE.parent / "receipts" / "exp002-parsimony-sweep.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1


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


class TestExp002Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp002")
        self.assertEqual(receipt["status"], "SEALED")
        # named seeds carry through into the WORLD row unchanged
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
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
        self.assertEqual(results["ledger_head"], "c5e9be966abaf0db")

    def test_sealed_champion_program_executable(self):
        receipt = json.loads(RECEIPT.read_text())
        prog = receipt["results"]["program"]
        # the parsimony champion is the len-1 genome [x(0)] plus the
        # measure surface, executable end-to-end by the vendored engine
        self.assertEqual(prog, [["x", 0], ["m", 0, 0], ["m", 1, 1]])
        qc = micromoth.QuantumCircuit(2, 2)
        qc.data = [tuple(t) for t in prog]
        random.seed(202)
        counts = micromoth.simulate(qc, shots=512, get="counts")
        self.assertEqual(counts, {"01": 512})
        # and the WORLD row in the ledger agrees with live re-simulation
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], {"01": 512})

    def test_control_arm_matches_exp001_champion(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        arms = {a["parsimony"]: a for a in receipt["results"]["arms"]}
        # parsimony=0.00 is the control: same champion as exp001's seal
        self.assertEqual(arms[0.0]["champion"], exp001["results"]["champion"])
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        # both pressure arms seal the identical len-1 champion
        for pen in (0.02, 0.05):
            self.assertEqual(arms[pen]["champion"], [["x", 0]])
            self.assertEqual(arms[pen]["champion_len"], 1)
            self.assertEqual(arms[pen]["champion_verify_p"], 1.0)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[3]["args"] = dict(ledger[3]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))), \
                    f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
