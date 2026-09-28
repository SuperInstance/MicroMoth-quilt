"""Pins for receipts/exp003-mutation-ablation.json (qcells lab exp003).

exp001 stalled at 0.502 for gens 1-3 and crossed at gen 4; exp003
ablated the mutation classes to find what crosses the plateau.  Four
arms on identical named seeds (root 7, train 101, verify 202, 512
shots): control (full mutate), replace-only, indel-only, jitter-only.
The mutate_classed seam draws the SAME move value from the same rng
stream and only restricts application; a non-applicable class is
RESAMPLED, never silently replaced; a hard no-move raises
MutationDeadlock, which is recorded as that arm's result.

Sealed outcome: control reproduces exp001 byte-for-byte; replace-only
hits the identical champion but crosses at gen 1 vs gen 4 (the control
stall was other classes burning draws, not search difficulty);
indel-only never crosses (champion verify P(01) = 265/512, pinned live
below); jitter-only DEADLOCKS at gen 0 (no rotation gate in the seed
champion).  Conclusion carried to the lab FINDINGS: the discrete gate
neighborhood is the engine.

FAIL-first: on pristine main (before this branch) both target files
are absent, so the whole file is RED; the tamper demo below trips RED
on a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp003_receipt -v
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
RECEIPT = HERE.parent / "receipts" / "exp003-mutation-ablation.json"
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


def _simulate(program, seed, shots):
    qc = micromoth.QuantumCircuit(2, 2)
    qc.data = [tuple(t) for t in program]
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


class TestExp003Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp003")
        self.assertEqual(receipt["status"], "SEALED")
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
        self.assertEqual(results["ledger_head"], "ade3dc62f7e589e9")

    def test_sealed_champion_program_executable(self):
        receipt = json.loads(RECEIPT.read_text())
        prog = receipt["results"]["program"]
        # the ablation champion (control AND replace arms) is the
        # exp001 genome [h(1),h(1),x(0)] plus the measure surface,
        # executable end-to-end by the vendored engine
        self.assertEqual(prog, [["h", 1], ["h", 1], ["x", 0],
                                ["m", 0, 0], ["m", 1, 1]])
        counts = _simulate(prog, seed=202, shots=512)
        self.assertEqual(counts, {"01": 512})
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], {"01": 512})

    def test_control_arm_matches_exp001_and_replace_crosses_earlier(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        arms = {a["arm"]: a for a in receipt["results"]["arms"]}
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        # control champion is byte-identical to the exp001 seal ...
        self.assertEqual(arms["control"]["champion"],
                         exp001["results"]["champion"])
        self.assertEqual(arms["control"]["first_verify_perfect_gen"], 4)
        # ... and replace-only reaches the SAME champion at gen 1:
        # the control stall was other classes burning draws
        self.assertEqual(arms["replace_only"]["champion"],
                         arms["control"]["champion"])
        self.assertEqual(arms["replace_only"]["first_verify_perfect_gen"], 1)

    def test_indel_arm_never_crosses_and_champion_rederived_live(self):
        receipt = json.loads(RECEIPT.read_text())
        arms = {a["arm"]: a for a in receipt["results"]["arms"]}
        indel = arms["indel_only"]
        self.assertIsNone(indel["first_verify_perfect_gen"])
        # the sealed non-crossing champion is re-derived live: 265/512
        # verify shots in 01 == the sealed 0.517578125 verify figure
        counts = _simulate(indel["champion"] + [["m", 0, 0], ["m", 1, 1]],
                           seed=202, shots=512)
        self.assertEqual(counts.get("01", 0), 265)
        self.assertAlmostEqual(counts.get("01", 0) / 512,
                               indel["champion_verify_p"], places=6)

    def test_jitter_arm_deadlock_recorded_not_worked_around(self):
        receipt = json.loads(RECEIPT.read_text())
        arms = {a["arm"]: a for a in receipt["results"]["arms"]}
        jitter = arms["jitter_only"]
        self.assertIn("deadlock", jitter)
        self.assertIn("no applicable mutation", jitter["deadlock"])
        # the deadlock IS the result: no champion was manufactured to
        # make the arm look like it ran
        self.assertNotIn("champion", jitter)
        self.assertNotIn("champion_verify_p", jitter)

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
