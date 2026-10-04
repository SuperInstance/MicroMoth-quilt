"""test_state_witness.py — pins for the TICK/PROOF statevector witness lane.

Implements the executable-law half of docs/CELL-MAPPING.md's TICK and
PROOF clauses (tools/state_witness.py is the implementation):

  1. Moment partition: qubit-disjoint gates share a TICK, touching
     gates do not — depth is the circuit's moment count.
  2. Parity (port rule 8): the witness engine's per-TICK state is
     BITWISE equal to simulate(get='statevector') on the same chain,
     and the final state_hash is derivable from the reference
     statevector alone — the port claims nothing the baseline didn't.
  3. PROOF pins the statevector by sha256 of the declared-precision
     canonical encoding, never inlines amplitudes, and tampers name
     themselves.
  4. The x·x nuance: state can come home (unitary round trip) while
     the ticker never retreats — the log is monotonic even when the
     state is not.
  5. Sugar never reaches a ledger; measurements partition no moment.
  6. Replay determinism: two witness runs of the same circuit mint
     byte-identical chains; verify() re-derives every id.

FAIL-first: on pristine main tools/state_witness.py does not exist and
every pin here dies at import (the runner's RED is the import error,
same honesty class as the receipt it pins).
"""

import hashlib
import json
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))

from micromoth import QuantumCircuit, simulate  # noqa: E402

import state_witness as sw  # noqa: E402


def ghz4():
    qc = QuantumCircuit(4, 0)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    return qc


class TestMomentPartition(unittest.TestCase):
    def test_disjoint_gates_share_a_moment(self):
        qc = QuantumCircuit(2, 0)
        qc.h(0)
        qc.h(1)
        self.assertEqual(sw.tick_witnesses(qc)["depth"], 1)

    def test_ghz4_depth_is_chain_length(self):
        # h(0) touches cx(0,1) on qubit 0; each cx shares one qubit
        # with its neighbor — no two gates are disjoint here.
        self.assertEqual(sw.tick_witnesses(ghz4())["depth"], 4)

    def test_measurements_partition_no_moment(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(0, 0)
        qc.measure(1, 1)
        # only the two gates are moments; the two 'm' records are not
        self.assertEqual(sw.tick_witnesses(qc)["depth"], 2)

    def test_sugar_refused(self):
        qc = QuantumCircuit(1, 0)
        qc.data.append(("y", 0))  # hand-built, unbaseline chain
        with self.assertRaises(ValueError):
            sw.tick_witnesses(qc)


class TestReferenceParity(unittest.TestCase):
    def test_final_state_bitwise_equal_to_simulate(self):
        qc = ghz4()
        k = [[0, 0] for _ in range(16)]
        k[0] = [1.0, 0.0]
        for moment in sw.layers(qc):
            for gate in moment:
                sw._apply(k, gate, 4)
        ref = simulate(qc, get="statevector")
        self.assertEqual(k, ref)  # bitwise, not approx

    def test_state_hash_derivable_from_reference_statevector(self):
        qc = ghz4()
        ref = simulate(qc, get="statevector")
        receipt = sw.tick_witnesses(qc, proof_at=-1)
        self.assertEqual(receipt["final_state_hash"], sw.state_hash(ref))

    def test_per_tick_hashes_are_recompute_points(self):
        # each TICK's state_hash must match the reference statevector
        # after applying exactly the gates of that moment
        qc = ghz4()
        k = [[0, 0] for _ in range(16)]
        k[0] = [1.0, 0.0]
        receipt = sw.tick_witnesses(qc)
        ticks = [c for c in receipt["cells"] if c["op"] == "TICK"]
        self.assertEqual(len(ticks), 4)
        for moment, tick in zip(sw.layers(qc), ticks):
            for gate in moment:
                sw._apply(k, gate, 4)
            self.assertEqual(tick["args"]["state_hash"], sw.state_hash(k))


class TestProofCell(unittest.TestCase):
    def test_proof_pins_sha256_of_rounded_reference(self):
        qc = ghz4()
        receipt = sw.tick_witnesses(qc, proof_at=-1)
        proofs = [c for c in receipt["cells"] if c["op"] == "PROOF"]
        self.assertEqual(len(proofs), 1)
        p = proofs[0]["args"]
        self.assertEqual(p["tick"], 4)
        ref = simulate(qc, get="statevector")
        want = hashlib.sha256(
            sw.state_digest(ref, p["precision"]).encode()).hexdigest()
        self.assertEqual(p["state_sha256"], want)
        # amplitudes are never inlined (cost law)
        self.assertNotIn("amplitudes", p)
        self.assertNotIn("statevector", json.dumps(p))

    def test_proof_tamper_names_itself(self):
        qc = ghz4()
        receipt = sw.tick_witnesses(qc, proof_at=1)
        proof = [c for c in receipt["cells"] if c["op"] == "PROOF"][0]
        proof["args"]["state_sha256"] = "0" * 64
        # cells: LINK@0 TICK@1 TICK@2 PROOF@3 — the proof body itself moved
        self.assertEqual(sw.verify(receipt, qc)["why"], "id_mismatch@3")

    def test_proof_chain_break_names_index(self):
        import collapse_ledger as cl
        qc = ghz4()
        receipt = sw.tick_witnesses(qc, proof_at=-1)
        cells = receipt["cells"]
        cells[3]["prev"] = cells[1]["id"]  # rewire a TICK's parent
        # repair the moved cell's own id so the chain check is reached
        cells[3]["id"] = "0x%016x" % cl.fnv1a64(cl._canon(
            {"op": cells[3]["op"], "prev": cells[3]["prev"],
             "args": cells[3]["args"]}))
        why = sw.verify(receipt)["why"]
        self.assertEqual(why, "chain_break@3")


class TestMonotonicLog(unittest.TestCase):
    def test_xx_state_returns_but_ticker_does_not(self):
        qc = QuantumCircuit(1, 0)
        qc.x(0)
        qc.x(0)
        receipt = sw.tick_witnesses(qc)
        home = sw.state_hash([[1, 0], [0, 0]])
        self.assertEqual(receipt["final_state_hash"], home)
        self.assertEqual(receipt["depth"], 2)
        # the log is monotonic even when the state is not: the x;x
        # chain must NOT collapse into the identity chain's cells
        ident = QuantumCircuit(1, 0)
        ident2 = sw.tick_witnesses(ident)
        self.assertNotEqual(
            [c["id"] for c in receipt["cells"]],
            [c["id"] for c in ident2["cells"]])


class TestReplay(unittest.TestCase):
    def test_two_runs_mint_identical_chains(self):
        a = sw.tick_witnesses(ghz4(), proof_at=-1)
        b = sw.tick_witnesses(ghz4(), proof_at=-1)
        self.assertEqual(
            json.dumps(a["cells"], sort_keys=True),
            json.dumps(b["cells"], sort_keys=True))

    def test_verify_replay_rejects_state_divergence(self):
        qc = ghz4()
        receipt = sw.tick_witnesses(qc)  # no PROOF: last cell is a TICK
        last = receipt["cells"][-1]
        self.assertEqual(last["op"], "TICK")
        last["args"]["state_hash"] = "0x0000000000000000"
        # repair the moved id so the structural checks pass and replay
        # is reached — replay then recomputes the real hash and the
        # chains diverge
        import collapse_ledger as cl
        last["id"] = "0x%016x" % cl.fnv1a64(cl._canon(
            {"op": last["op"], "prev": last["prev"], "args": last["args"]}))
        why = sw.verify(receipt, qc)["why"]
        self.assertEqual(why, "replay_divergence")

    def test_verify_ok_on_fresh_receipt(self):
        qc = ghz4()
        receipt = sw.tick_witnesses(qc, proof_at=-1)
        self.assertEqual(sw.verify(receipt, qc), {"ok": True, "why": "ok"})


if __name__ == "__main__":
    unittest.main()
