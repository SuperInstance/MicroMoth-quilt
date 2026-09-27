#!/usr/bin/env python3
"""test_import_baseline.py — the dormant lane's first pins.

The lane is asleep; these pins make sure it wakes to a verifiable
baseline, not a memory. Run: python3 tests/test_import_baseline.py

Pins:
  1. receipts/import-baseline.json exists and re-derives to equality
     over every git-tracked file — any edit to the imported tree that
     nobody re-sealed trips RED, naming regeneration as the remedy.
  2. The recorded provenance names the upstream fork.
  3. The import is FUNCTIONAL: a Bell circuit (h, cx, measure) run
     through micromoth puts 100% of shots in {'00','11'} — if a future
     refresh of the import breaks the quantum core, the dormant lane
     finds out at test time, not at wake time.

FAIL-first evidence in the PR body: pin 1 tripped RED before the
manifest existed; a digest mutation trips RED; restore goes green.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))
import import_manifest  # noqa: E402

MANIFEST = LAB / "receipts" / "import-baseline.json"


class BaselineSealed(unittest.TestCase):
    def test_manifest_exists_and_matches(self):
        self.assertTrue(MANIFEST.exists(),
                        "receipts/import-baseline.json missing — regenerate via "
                        "python3 tools/import_manifest.py and commit it WITH your change")
        on_disk = json.loads(MANIFEST.read_text())
        live = import_manifest.build()
        self.assertEqual(on_disk.get("files"), live["files"],
                         "tracked-file digests drifted — regenerate the manifest "
                         "(tools/import_manifest.py), never edit it by hand")

    def test_provenance_names_upstream(self):
        self.assertTrue(MANIFEST.exists(),
                        "receipts/import-baseline.json missing — regenerate via "
                        "python3 tools/import_manifest.py and commit it WITH your change")
        on_disk = json.loads(MANIFEST.read_text())
        self.assertEqual(on_disk.get("upstream"), "moth-quantum/MicroMoth")
        self.assertTrue(on_disk.get("baseline_commit"),
                        "baseline_commit absent — the manifest must name the "
                        "commit it sealed")


class ImportFunctional(unittest.TestCase):
    def test_bell_circuit_entangles(self):
        from micromoth import QuantumCircuit, simulate
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(0, 0)
        qc.measure(1, 1)
        counts = simulate(qc, shots=256, get="counts")
        total = sum(counts.values())
        outside = total - counts.get("00", 0) - counts.get("11", 0)
        self.assertEqual(total, 256, f"shot count drifted: {counts}")
        self.assertEqual(outside, 0,
                         f"Bell circuit leaked {outside}/256 shots outside the "
                         f"entangled subspace: {counts} — the imported core is broken")


if __name__ == "__main__":
    unittest.main(verbosity=2)
