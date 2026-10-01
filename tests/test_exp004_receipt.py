"""Pins for receipts/exp004-jitter-drop.json (qcells lab exp004).

exp003 ablated the mutation classes and found the discrete gate
neighborhood is the engine; exp004 promotes that finding to POLICY.
Same search, same named seeds (root 7, train 101, verify 202, 512
shots), ONE change: the jitter branch is dropped entirely
(`mutate_classed restrict=("replace","indel")`), zero harness change,
reusing exp003's ablation seam as the policy knob.  The control lane
re-run inside this harness still reproduces exp001 byte-for-byte.

Sealed outcome: BOTH arms reach the identical champion [h(1),h(1),x(0)]
at held-out verify 1.000 — but the jitter-dropped policy crosses at
gen 2 vs the control's gen 4.  Jitter was only burning candidate draws
in the mixed neighborhood; the exp003 recommendation holds at the
policy level, not just the ablation level.

FAIL-first: on pristine main (before this branch) both target files
are absent, so the whole file is RED; the tamper demo below trips RED
on a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp004_receipt -v
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
RECEIPT = HERE.parent / "receipts" / "exp004-jitter-drop.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"
EXP003_RECEIPT = HERE.parent / "receipts" / "exp003-mutation-ablation.json"

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


class TestExp004Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp004")
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
        self.assertEqual(results["ledger_head"], "7bffc7144b684ccb")

    def test_sealed_champion_program_executable(self):
        receipt = json.loads(RECEIPT.read_text())
        prog = receipt["results"]["champion"]
        # the policy champion (BOTH arms) is the exp001 genome
        # [h(1),h(1),x(0)] plus the measure surface, executable
        # end-to-end by the vendored engine
        self.assertEqual(prog, [["h", 1], ["h", 1], ["x", 0]])
        counts = _simulate(prog + [["m", 0, 0], ["m", 1, 1]],
                           seed=202, shots=512)
        self.assertEqual(counts, {"01": 512})
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], {"01": 512})

    def test_control_arm_matches_exp001_and_policy_crosses_earlier(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        arms = {a["arm"]: a for a in receipt["results"]["arms"]}
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        # control champion is byte-identical to the exp001 seal ...
        self.assertEqual(arms["control"]["champion"],
                         exp001["results"]["champion"])
        self.assertEqual(arms["control"]["first_verify_perfect_gen"], 4)
        # ... the jitter-dropped arm reaches the SAME champion at gen 2:
        # same honesty, twice the convergence — the policy claim
        self.assertEqual(arms["no_jitter"]["champion"],
                         arms["control"]["champion"])
        self.assertEqual(arms["no_jitter"]["restrict"], ["replace", "indel"])
        self.assertEqual(arms["no_jitter"]["first_verify_perfect_gen"], 2)
        self.assertLess(arms["no_jitter"]["first_verify_perfect_gen"],
                        arms["control"]["first_verify_perfect_gen"])

    def test_same_champion_as_exp003_ablation_cross_receipts(self):
        # the exp003 ablation champion and the exp004 policy champion are
        # the identical genome: the policy seal and the ablation seal
        # agree on WHAT was found; they differ on HOW FAST policy reaches
        # it (exp003 replace-only gen 1 arm is class-restricted, exp004
        # no_jitter keeps indel and crosses at gen 2)
        receipt = json.loads(RECEIPT.read_text())
        exp003 = json.loads(EXP003_RECEIPT.read_text())
        arms4 = {a["arm"]: a for a in receipt["results"]["arms"]}
        arms3 = {a["arm"]: a for a in exp003["results"]["arms"]}
        self.assertEqual(arms4["no_jitter"]["champion"],
                         arms3["replace_only"]["champion"])
        self.assertEqual(arms4["control"]["champion"],
                         arms3["control"]["champion"])

    def test_honest_limits_present_and_scoped(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        # the policy verdict must carry its scope limits, not read as a
        # universal 'drop jitter' law
        self.assertIn("single root seed", limits)
        self.assertIn("PRODUCT", limits)

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
