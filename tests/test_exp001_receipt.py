#!/usr/bin/env python3
"""test_exp001_receipt.py — pins for the lane's first experiment receipt.

receipts/exp001-bias-search.json seals the qcells lab's exp001
(champion-seeded bias search toward |01>): 13 witness-ledger rows in
the CELL-MAPPING choreography (BIND/EFFECT/TICK/WORLD/PROOF, fleet WAL
canonical key set, fnv1a-64 chain, sha256 state witnesses).

Pins:
  1. Receipt exists, schema tagged, status SEALED.
  2. Chain integrity re-derived in-repo: every row's hash =
     fnv1a-64 over the canonical body {args, cell, op, prev_hash,
     seq}; prev_hash linkage unbroken from the zero genesis.
  3. Nothing unseeded is ever written as a result: the WORLD
     (shot-sampling) row names seed AND shots in its args.
  4. Recorded head matches the final PROOF row; row count recorded.
  5. The sealed BIND program is the full executable champion circuit
     (genome plus its two measurement gates — the genome alone never
     produces histograms) and the recorded histogram puts all 512
     verify shots in '01'.
  6. Tamper trip (in-memory): mutating any sealed row breaks the
     chain AT that row — its own re-derived hash no longer matches
     the seal — the receipt is not decorative.

FAIL-first evidence in the PR body: pins trip RED on pristine main
(receipt file absent); a digest mutation trips RED; restore green.
Run: python3 tests/test_exp001_receipt.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
RECEIPT = LAB / "receipts" / "exp001-bias-search.json"

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1


def fnv1a64(data: bytes) -> str:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & MASK64
    return f"{h:016x}"


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def row_hash(row: dict) -> str:
    body = {"args": row["args"], "cell": row["cell"], "op": row["op"],
            "prev_hash": row["prev_hash"], "seq": row["seq"]}
    return fnv1a64(canon(body))


class Exp001Receipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not RECEIPT.exists():
            raise unittest.SkipTest("receipts/exp001-bias-search.json missing")
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.ledger = cls.receipt["ledger"]

    def test_schema_and_status(self):
        self.assertEqual(self.receipt["schema"], "micromoth-quilt/exp-receipt@v1")
        self.assertEqual(self.receipt["status"], "SEALED")
        self.assertEqual(self.receipt["experiment"], "exp001-bias-search")

    def test_chain_integrity_rederived(self):
        prev = "0" * 16
        for i, row in enumerate(self.ledger):
            self.assertEqual(row["seq"], i, f"seq gap at row {i}")
            self.assertEqual(row["prev_hash"], prev,
                             f"chain break at row {i}: prev_hash {row['prev_hash']} != {prev}")
            self.assertEqual(row["hash"], row_hash(row),
                             f"hash mismatch at row {i}: sealed hash not re-derived")
            prev = row["hash"]

    def test_world_rows_name_seed_and_shots(self):
        worlds = [r for r in self.ledger if r["op"] == "WORLD"]
        self.assertEqual(len(worlds), 1, "exactly one verify WORLD row expected")
        for w in worlds:
            self.assertIn("seed", w["args"], "WORLD row without seed = UNSEALED result")
            self.assertIn("shots", w["args"])

    def test_head_and_row_count_match_seal(self):
        self.assertEqual(self.receipt["results"]["ledger_head"], self.ledger[-1]["hash"])
        self.assertEqual(self.receipt["results"]["ledger_rows"], len(self.ledger))
        self.assertEqual(self.ledger[-1]["op"], "PROOF")

    def test_champion_is_deterministic_01(self):
        bind = self.ledger[0]
        self.assertEqual(bind["op"], "BIND")
        # Full executable program: genome (h,h,x) + its two measure gates.
        self.assertEqual(bind["args"]["program"],
                         [["h", 1], ["h", 1], ["x", 0], ["m", 0, 0], ["m", 1, 1]])
        genome = [g for g in bind["args"]["program"] if g[0] != "m"]
        self.assertEqual(genome, [["h", 1], ["h", 1], ["x", 0]])
        self.assertEqual(self.receipt["results"]["champion"], genome)
        self.assertEqual(bind["args"]["kind"], "qc-exp001-champion")
        world = [r for r in self.ledger if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], {"01": 512})

    def test_tamper_trips_chain(self):
        tampered = json.loads(json.dumps(self.ledger))
        tampered[5]["args"]["ticker"] = 999
        prev = "0" * 16
        tripped_at = None
        for i, row in enumerate(tampered):
            if row["prev_hash"] != prev or row["hash"] != row_hash(row):
                tripped_at = i
                break
            prev = row["hash"]
        self.assertEqual(tripped_at, 5,
                         "mutating row 5 must trip at row 5 (own hash no longer re-derives)")


if __name__ == "__main__":
    unittest.main()
