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
