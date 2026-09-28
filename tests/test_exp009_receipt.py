"""Pins for receipts/exp009-budget-length-control.json (qcells lab exp009).

exp009 is the doctrine's CEILING-ISOLATION test. Every frozen-unaided
verdict (exp005-008) and the seeded crossing were recorded under a
6-gate budget. exp009 sweeps budget 6 -> 8 -> 12 on the one lane that
reliably crosses (doctrine lane: seedA GHZ3 skeleton, n=4 GHZ balance,
restrict=('replace','indel'), same named seeds root 7 / train 101 /
verify 202 / 512 shots) with everything else identical:

  budget 6   -> champion [h(0),cx(0,1),crx(1.0,1,3),cx(1,2)]
                (the exp008 NON-canonical route), crosses gen 5,
                held-out verify 0.4824, max_champion_len_seen=4
  budget 8   -> byte-identical outcome
  budget 12  -> byte-identical outcome

Sealed outcome: the ceiling is NOT binding on this target class at
n=4 — the no-op is proven from telemetry (max_champion_len_seen=4 at
every budget; budget only gates the move choice at len>=budget, which
never occurs), so the exp005-008 frozen-unaided verdicts stand as
engine laws, not artifacts of a short leash. The no-op is the honest
result, not a harness bug; the anti-laundering rationale is recorded
in the receipt's budget_invariance note.

The crx pi-expansion honesty pin is load-bearing (exp006 class):
genome thetas are search-space units multiplied by pi at circuit
build. Simulating crx(1.0) as a raw 1.0-radian turn does NOT
reproduce the sealed champion.

FAIL-first: on pristine main (before this branch) the receipt is
absent, so the whole file is RED; the tamper demo below trips RED on
a mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp009_receipt -v
"""
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth  # repo-root vendored engine (the engine the receipt names)

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp009-budget-length-control.json"
EXP001_RECEIPT = HERE.parent / "receipts" / "exp001-bias-search.json"

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1
TARGETS = ("0000", "1111")
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


def _genome_circuit(genome):
    """The lab's genome_circuit encoding: crx thetas are search-space
    units multiplied by pi at build time (exp006 pi-expansion)."""
    qc = micromoth.QuantumCircuit(4, 4)
    for g in genome:
        op = g[0]
        if op == "x":
            qc.x(g[1])
        elif op == "h":
            qc.h(g[1])
        elif op == "cx":
            qc.cx(g[1], g[2])
        elif op == "swap":
            qc.swap(g[1], g[2])
        elif op == "crx":
            qc.crx(g[1] * PI, g[2], g[3])
        else:
            raise ValueError(f"unknown op {op}")
    for q in range(4):
        qc.measure(q, q)
    return qc


def _simulate(genome, seed=202, shots=512):
    qc = _genome_circuit(genome)
    random.seed(seed)
    return micromoth.simulate(qc, shots=shots, get="counts")


CHAMPION = [["h", 0], ["cx", 0, 1], ["crx", 1.0, 1, 3], ["cx", 1, 2]]
SEED_GENOME = [["h", 0], ["cx", 0, 1], ["cx", 1, 2]]


class TestExp009Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp009")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
        self.assertIn("targets=('0000','1111')", receipt["protocol"])
        self.assertIn("budget swept 6/8/12", receipt["protocol"])
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
        self.assertEqual(results["ledger_head"], "ef538852ee95f4ad")

    def test_sealed_champion_program_executable(self):
        receipt = json.loads(RECEIPT.read_text())
        self.assertEqual(receipt["results"]["champion"], CHAMPION)
        qc = _genome_circuit(CHAMPION)
        prog = [list(t) for t in qc.data]
        self.assertEqual(prog, receipt["results"]["champion_expanded_program"])
        # held-out verify: the receipt's own ledger WORLD row
        random.seed(202)
        counts = micromoth.simulate(qc, shots=512, get="counts")
        self.assertEqual(counts, {"0000": 247, "1111": 265})
        self.assertEqual(_balance(counts), 0.482421875)
        self.assertGreaterEqual(_balance(counts), 0.45)
        world = [r for r in receipt["ledger"] if r["op"] == "WORLD"][0]
        self.assertEqual(world["witness"]["counts"], counts)
        # train seed reproduces the sealed train balance
        train_counts = _simulate(CHAMPION, seed=101)
        self.assertEqual(train_counts, {"0000": 255, "1111": 257})
        self.assertEqual(_balance(train_counts), 0.498046875)

    def test_crx_pi_expansion_is_load_bearing(self):
        # honesty pin (exp006 class): simulating the champion with crx
        # theta taken as a RAW 1.0-radian turn must NOT reproduce the
        # sealed balance — the x-pi search-space encoding is the delta
        qc = micromoth.QuantumCircuit(4, 4)
        qc.data = [("h", 0), ("cx", 0, 1), ("crx", 1.0, 1, 3), ("cx", 1, 2),
                   ("m", 0, 0), ("m", 1, 1), ("m", 2, 2), ("m", 3, 3)]
        random.seed(202)
        counts = micromoth.simulate(qc, shots=512, get="counts")
        self.assertNotEqual(_balance(counts), 0.482421875,
                            "raw-theta simulation reproduced the seal — "
                            "the pi expansion stopped being load-bearing")

    def test_control_guard_reproduces_exp001(self):
        receipt = json.loads(RECEIPT.read_text())
        exp001 = json.loads(EXP001_RECEIPT.read_text())
        self.assertTrue(receipt["results"]["control_reproduces_exp001"])
        self.assertEqual(exp001["results"]["champion"],
                         [["h", 1], ["h", 1], ["x", 0]])
        # the sealed n=4 crossing champion is NOT the 2-qubit home
        # champion: the harness is unchanged, the birth seed is the delta
        self.assertNotEqual(receipt["results"]["champion"],
                            exp001["results"]["champion"])

    def test_budget_sweep_is_a_proven_noop(self):
        receipt = json.loads(RECEIPT.read_text())
        budgets = receipt["results"]["budgets"]
        self.assertEqual(set(budgets), {"6", "8", "12"})
        for arm in budgets.values():
            self.assertEqual(arm["champion_genome"], CHAMPION)
            self.assertEqual(arm["champion_len"], 4)
            self.assertEqual(arm["champion_train_balance"], 0.498046875)
            self.assertEqual(arm["champion_verify_balance"], 0.482421875)
            self.assertEqual(arm["first_verify_ge_045_gen"], 5)
            # the no-op mechanism, from telemetry not assumption: the
            # champion never grew past 4 gates, and a 4-gate champion's
            # indel children top out at 5 gates < 6 — the budget only
            # enters the move choice at len>=budget, which never occurs
            self.assertEqual(arm["max_champion_len_seen"], 4)
            self.assertLess(arm["max_champion_len_seen"], 6)
            for row in arm["fitness_by_generation"]:
                self.assertLessEqual(len(row["champion_genome"]), 5)
                if row["gen"] >= 5:
                    self.assertGreaterEqual(row["verify_balance"], 0.45)
        # byte-identical across budgets: same curves, same everything
        c6 = json.dumps(budgets["6"]["fitness_by_generation"], sort_keys=True)
        c8 = json.dumps(budgets["8"]["fitness_by_generation"], sort_keys=True)
        c12 = json.dumps(budgets["12"]["fitness_by_generation"], sort_keys=True)
        self.assertEqual(c6, c8)
        self.assertEqual(c8, c12)
        inv = receipt["results"]["budget_invariance"]
        self.assertTrue(inv["byte_identical_outcomes"])
        self.assertIn("max_champion_len_seen=4", inv["note"])

    def test_seed_genome_birth_is_zero_fitness(self):
        # the lane is born at balance 0.0 (GHZ3 on qubits 0-2 tensor |0>:
        # the n=4 targets never fire) — the crossing is search, not birth
        receipt = json.loads(RECEIPT.read_text())
        seed_birth = _simulate(SEED_GENOME, seed=101)
        self.assertEqual(set(seed_birth), {"0000", "0111"})
        self.assertEqual(_balance(seed_birth), 0.0)
        for arm in receipt["results"]["budgets"].values():
            self.assertEqual(arm["seed_genome"], SEED_GENOME)
            self.assertEqual(arm["fitness_by_generation"][0]["champion_genome"],
                             SEED_GENOME)
            self.assertEqual(arm["fitness_by_generation"][0]["train_balance"],
                             0.0)
            self.assertEqual(arm["fitness_by_generation"][0]["verify_balance"],
                             0.0)

    def test_honest_limits_scope(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("single root", limits)
        self.assertIn("no-op", limits)
        self.assertIn("max_champion_len_seen=4", limits)
        self.assertIn("NOT generalize", limits)
        self.assertIn("exp012-exp014", limits)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[5]["args"] = dict(ledger[5]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))),                     f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
