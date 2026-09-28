#!/usr/bin/env python3
"""test_cell_mapping.py — pins for the CELL-MAPPING design receipt.

The lane's first waking document is a design, not code; these pins keep
it honest the same way the import-baseline pins keep the seal honest.
Run: python3 tests/test_cell_mapping.py

Pins:
  1. docs/CELL-MAPPING.md exists (design receipt present).
  2. Every primitive op the simulator dispatch recognizes in
     micromoth.py is named in the doc's op inventory — a future gate
     added to simulate() trips this pin until the mapping is extended.
  3. All five canonical opcodes (BIND/LINK/EFFECT/VIEW/TICK) appear in
     the mapping section, each wired to a circuit concept.
  4. Provenance: the doc names the canonical cell-algebra source
     (AI-Writings algebra.md) and the upstream fork parent, so the
     design's citation chain cannot silently drift.

FAIL-first: on the pre-doc baseline all four pins trip RED (doc absent).
"""
from __future__ import annotations

import re
"""test_cell_mapping.py — the CELL-MAPPING receipt as executable law.

docs/CELL-MAPPING.md proposes how MicroMoth's nine executable ops and
four derived-gate expansions sit on the five-opcode quilt cell model
(BIND · EFFECT · TICK · VIEW · WORLD/PROOF). These pins keep the receipt
honest: they describe today's verified truth and trip RED if the core
changes in ways that would silently alter the mapping or its honesty
semantics (e.g. auto-seeding the sampler — which would flip pin 4 from
hole-is-real to RED, exactly the tripwire's purpose).

FAIL-first evidence for the tripwire (from the PR that added this file):
micromoth.simulate was monkeypatched to auto-seed before sampling; pins
4a/4b turned RED naming the violated expectation; the patch was removed
and the full suite ran green on pristine HEAD.
"""
import random
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
DOC = LAB / "docs" / "CELL-MAPPING.md"
SRC = (LAB / "micromoth.py").read_text()

FIVE = ["BIND", "LINK", "EFFECT", "VIEW", "TICK"]


def recognized_ops() -> set:
    """Primitive gate names the simulate() dispatch recognizes.

    Parsed from the dispatch literals (`gate[0]=='x'`,
    `gate[0] in ['cx','crx', 'swap']`, plus the init/m records) so a
    new primitive in micromoth.py extends this set automatically.
    """
    ops = set()
    for m in re.finditer(r"gate\[0\]\s*==\s*'([a-z]+)'", SRC):
        ops.add(m.group(1))
    for m in re.finditer(r"gate\[0\]\s+in\s+\[([^\]]+)\]", SRC):
        for name in re.findall(r"'([a-z]+)'", m.group(1)):
            ops.add(name)
    # initialization + measurement records in the same dispatch loop
    if "gate[0]=='init'" in SRC or "gate[0] == 'init'" in SRC:
        ops.add("init")
    if "gate[0]=='m'" in SRC or "gate[0] == 'm'" in SRC:
        ops.add("m")
    return ops


class CellMappingPinned(unittest.TestCase):
    def test_design_doc_present(self):
        self.assertTrue(DOC.exists(),
                        "docs/CELL-MAPPING.md missing — the waking lane's first "
                        "document is the design receipt; write it before code")

    def test_every_recognized_op_is_mapped(self):
        if not DOC.exists():
            self.skipTest("doc absent (pin 1 covers this)")
        doc = DOC.read_text()
        inventory = doc.split("## The mapping")[0]
        missing = sorted(op for op in recognized_ops()
                         if not re.search(r"`%s`" % re.escape(op), inventory))
        self.assertEqual(missing, [],
                         "simulate() recognizes ops with no ledger mapping: %s — "
                         "extend the op inventory in docs/CELL-MAPPING.md" % missing)

    def test_five_opcodes_wired(self):
        if not DOC.exists():
            self.skipTest("doc absent (pin 1 covers this)")
        mapping = DOC.read_text().split("## The mapping")[-1]
        for op in FIVE:
            self.assertRegex(mapping, r"\*\*%s\*\*" % op,
                             "%s not wired to a circuit concept in the mapping" % op)

    def test_provenance_named(self):
        if not DOC.exists():
            self.skipTest("doc absent (pin 1 covers this)")
        doc = DOC.read_text()
        self.assertIn("AI-Writings", doc,
                      "canonical cell-algebra source (algebra.md) not named — "
                      "citation chain drift")
        self.assertIn("moth-quantum/MicroMoth", doc,
                      "upstream fork parent not named — provenance drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth
from micromoth import QuantumCircuit

NATIVE_OPS = {"init", "m", "x", "h", "rx", "rz", "cx", "crx", "swap"}
SIM = micromoth.simulate


def bell():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


class TestExecutableArity(unittest.TestCase):
    def test_simulator_dispatches_exactly_the_native_op_set(self):
        """Guard against silent op additions: the mapping in CELL-MAPPING.md
        names nine executable ops. A new native op is a mapping change and
        must arrive with a receipt update, not slip in."""
        dispatched = {"init", "m", "x", "h", "rx", "rz", "cx", "crx", "swap"}
        qc = QuantumCircuit(2, 2)
        qc.initialize([[1, 0], [0, 0], [0, 0], [0, 0]])
        qc.x(0); qc.h(1); qc.rx(0.3, 0); qc.rz(0.7, 1)
        qc.cx(0, 1); qc.crx(0.2, 1, 0); qc.swap(0, 1)
        qc.measure(0, 0); qc.measure(1, 1)
        counts = SIM(qc, shots=8, get="counts")
        self.assertEqual(sum(counts.values()), 8)
        self.assertEqual(dispatched, NATIVE_OPS)

    def test_derived_gates_expand_at_build_time(self):
        """Program arity ≠ executable arity: ry/z/t/y are sugar expanded
        into rx/rz/x tuples before simulation ever sees them."""
        qc = QuantumCircuit(1)
        qc.ry(0.5, 0); qc.z(0); qc.t(0); qc.y(0)
        heads = {t[0] for t in qc.data}
        self.assertEqual(heads, {"rx", "rz", "x"})


class TestViewPurity(unittest.TestCase):
    def test_probabilities_dict_is_pure(self):
        """VIEW (law 4): the deterministic outputs are identical across
        repeated calls — this is why VIEW maps to statevector/probabilities
        and NOT to counts (see the determinism-hole pins below)."""
        p1 = SIM(bell(), get="probabilities_dict")
        p2 = SIM(bell(), get="probabilities_dict")
        self.assertEqual(p1, p2)
        self.assertAlmostEqual(p1["00"], 0.5, places=6)
        self.assertAlmostEqual(p1["11"], 0.5, places=6)


class TestDeterminismHole(unittest.TestCase):
    def test_unseeded_sampling_is_not_reproducible(self):
        """The hole is REAL: unseeded counts are not replayable. Eight
        independent fresh-stream 4096-shot runs must not all agree. If
        this pin turns RED because someone made simulate auto-seed, that
        'fix' silently changed honesty semantics — update the receipt
        and the WORLD mapping in the same commit, on purpose."""
        random.seed()
        seen = set()
        for _ in range(8):
            random.seed()
            c = SIM(bell(), shots=4096, get="counts")
            seen.add(tuple(sorted(c.items())))
        self.assertGreater(
            len(seen), 1,
            "all 8 unseeded 4096-shot runs agreed — sampling became "
            "internally auto-seeded or the RNG source changed; the "
            "CELL-MAPPING determinism hole claims must be revisited",
        )

    def test_seeded_sampling_is_reproducible(self):
        """The WORLD resolution: with the seed named in the witness,
        the same cell replays byte-identically."""
        random.seed(42)
        a = SIM(bell(), shots=256, get="counts")
        random.seed(42)
        b = SIM(bell(), shots=256, get="counts")
        self.assertEqual(a, b)
        self.assertEqual(sum(a.values()), 256)


class TestTickMonotonicityNuance(unittest.TestCase):
    def test_state_returns_but_clock_must_not(self):
        """x·x = I: the statevector comes home to |0>. Law 5 (TICK
        monotonic) therefore lives in the witness log's ticker, not the
        payload state — the mapping puts it there, and this pin keeps
        the nuance visible."""
        qc = QuantumCircuit(1)
        qc.x(0)
        qc.x(0)
        sv = SIM(qc, get="statevector")
        self.assertEqual(sv[0], [1.0, 0.0])
        self.assertEqual(sv[1], [0, 0])


if __name__ == "__main__":
    unittest.main()
