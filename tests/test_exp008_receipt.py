"""Pins for receipts/exp008-ghz4-scale.json (qcells lab exp008).

exp008 is the doctrine's SCALE test, unblocked by the PROOF statevector
witness cell (qcell/stepper.py made emit O(gates); 'n=4+' was the named
blocker). On n=4 GHZ balance (targets ('0000','1111'), mode='balance'),
three lanes on identical named seeds and the exp004 jitter-dropped
policy:

  unseeded           random 3-gate birth   — FROZEN all 12 gens,
                                              train=verify=0.000
  seedA_ghz3_skeleton [h(0),cx(0,1),cx(1,2)] — GHZ3 structural prefix,
                                              birth balance 0.0, ONE cx
                                              insert from GHZ4; CROSSES
                                              gen 5, verify 0.4824 via a
                                              NON-canonical partial-
                                              rotation route
                                              [h(0),cx(0,1),crx(pi,1,3),cx(1,2)]
  seedB_product4_trap [h,h,h,h] — |++++>     — birth balance 0.0566, the
                                              exp007 Finding-4 trap class;
                                              ESCAPES at n=4 (gen 8) — the
                                              trap SLOWS but does not freeze:
                                              dimension-dependent, not a law

Sealed outcome: the never-solves-entanglement-unaided meta-finding
(Finding 5) generalizes to n=4; zero-fitness structural-prefix seeding
remains the fastest lane at every n tested (2,3,4); Finding 4 is
downgraded from 'never escapes' to 'slows escape' at n>=4.

The crx encoding honesty pin is load-bearing: genome thetas are
search-space units multiplied by pi at circuit build (the exp006
pi-expansion encoding). Simulating crx(1.0) as a raw 1.0-radian turn
does NOT reproduce the sealed champion.

FAIL-first: on pristine main (before this branch) the receipt is
absent, so the whole file is RED; the tamper demo below trips RED on a
mutated copy and is restored green.

Run: python3 -m unittest tests.test_exp008_receipt -v
"""
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth  # repo-root vendored engine (the engine the receipt names)

HERE = Path(__file__).resolve().parent
RECEIPT = HERE.parent / "receipts" / "exp008-ghz4-scale.json"
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
SEEDB_CHAMPION = [["h", 0], ["cx", 0, 1], ["cx", 1, 2], ["cx", 0, 3]]


class TestExp008Receipt(unittest.TestCase):
    def test_receipt_and_ledger_well_formed(self):
        receipt = json.loads(RECEIPT.read_text())
        for key in ("schema", "experiment", "status", "title", "directive",
                    "engine", "seeds", "protocol", "results", "honest_limits",
                    "ledger"):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["schema"], "micromoth-receipt-v1")
        self.assertEqual(receipt["experiment"], "qcells/exp008")
        self.assertEqual(receipt["status"], "SEALED")
        self.assertEqual(receipt["seeds"], {"root": 7, "train": 101,
                                            "verify": 202, "shots": 512})
        self.assertIn("targets=('0000','1111')", receipt["protocol"])
        self.assertIn("n_qubits=4", receipt["protocol"])
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
        self.assertEqual(results["ledger_head"], "f0fdc047b46ae575")

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

    def test_seed_prelude_live(self):
        receipt = json.loads(RECEIPT.read_text())
        prelude = receipt["results"]["prelude"]
        # lane A birth: GHZ3 on qubits 0-2 tensor |0> — the n=4 targets
        # never fire: balance 0.0 by target mismatch, not weakness
        seed_a = _simulate([["h", 0], ["cx", 0, 1], ["cx", 1, 2]], seed=101)
        self.assertEqual(seed_a, prelude["seedA_birth_counts"])
        self.assertEqual(set(seed_a), {"0000", "0111"})
        self.assertEqual(_balance(seed_a), prelude["seedA_birth_balance"])
        self.assertEqual(prelude["seedA_birth_balance"], 0.0)
        # lane B birth: |++++> near-uniform, slope present at 0.0566
        seed_b = _simulate([["h", 0], ["h", 1], ["h", 2], ["h", 3]], seed=101)
        self.assertEqual(seed_b, prelude["seedB_birth_counts"])
        self.assertEqual(_balance(seed_b), prelude["seedB_birth_balance"])
        self.assertAlmostEqual(prelude["seedB_birth_balance"], 0.0566,
                               places=3)

    def test_lanes_freeze_cross_and_trap_escape(self):
        receipt = json.loads(RECEIPT.read_text())
        lanes = receipt["results"]["lanes"]
        lane_a = lanes["seedA_ghz3_skeleton"]
        lane_b = lanes["seedB_product4_trap"]
        lane_u = lanes["unseeded_random_birth"]
        # lane A: GHZ3 skeleton crosses at gen 5 via the non-canonical
        # partial-rotation route and holds >= 0.45
        self.assertEqual(lane_a["first_verify_ge_045_gen"], 5)
        self.assertEqual(lane_a["champion_genome"], CHAMPION)
        self.assertEqual(lane_a["champion_verify_balance"], 0.482421875)
        for row in lane_a["fitness_by_generation"]:
            if row["gen"] >= 5:
                self.assertGreaterEqual(row["verify_balance"], 0.45)
        # lane B: the Finding-4 trap ESCAPES at n=4 — but slower (gen 8
        # vs the skeleton's gen 5), and only after sitting at the 0.2422
        # plateau: slowed, not frozen
        self.assertEqual(lane_b["first_verify_ge_045_gen"], 8)
        self.assertEqual(lane_b["champion_genome"], SEEDB_CHAMPION)
        self.assertEqual(lane_b["champion_verify_balance"], 0.482421875)
        for row in lane_b["fitness_by_generation"]:
            if row["gen"] < 8:
                self.assertLess(row["verify_balance"], 0.45)
        # the escaped trap champion is genuinely entangled: live held-out
        # verify reproduces exactly
        self.assertEqual(_balance(_simulate(SEEDB_CHAMPION)),
                         lane_b["champion_verify_balance"])
        # unseeded: frozen at 0.000 across all 12 gens — the
        # never-crosses law generalizes to n=4
        self.assertIsNone(lane_u["first_verify_ge_045_gen"])
        self.assertEqual(lane_u["champion_verify_balance"], 0.0)
        self.assertEqual(lane_u["champion_genome"],
                         [["h", 3], ["cx", 0, 1], ["h", 0]])
        for row in lane_u["fitness_by_generation"]:
            self.assertEqual(row["verify_balance"], 0.0)

    def test_honest_limits_scope(self):
        receipt = json.loads(RECEIPT.read_text())
        limits = " ".join(receipt["honest_limits"])
        self.assertIn("single root", limits)
        self.assertIn("BALANCE", limits)
        self.assertIn("mode=any", limits)
        self.assertIn("exp012-exp014", limits)
        self.assertIn("dimension-dependent", limits)
        self.assertIn("NON-canonical", limits)

    def test_tamper_trips_at_mutated_row(self):
        receipt = json.loads(RECEIPT.read_text())
        ledger = [dict(r) for r in receipt["ledger"]]
        ledger[5]["args"] = dict(ledger[5]["args"], ticker=99)
        with self.assertRaises(AssertionError):
            for i, row in enumerate(ledger):
                assert row["hash"] == fnv1a64(_canon(row_body(row))),                     f"tamper not caught at row {i}"


if __name__ == "__main__":
    unittest.main()
