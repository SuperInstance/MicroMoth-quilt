"""Pin: the qcells lab's canonical home is named in AUDIT.md.

The sealed receipts cite a local workspace path (workspace/labs/qcells)
that is not durable provenance. AUDIT.md must name the org repo that
hosts the lab, so a merged PR in this repo carries the by-name citation
the referral graph's weight law requires (edge mgq-qcells-lab ->
mm-sealed-receipts).
"""
import pathlib
import unittest

AUDIT = pathlib.Path(__file__).resolve().parent.parent / "AUDIT.md"


class LabHomeCitation(unittest.TestCase):
    def test_audit_names_micrograd_quilt_repo(self):
        text = AUDIT.read_text(encoding="utf-8")
        self.assertIn("SuperInstance/micrograd-quilt", text,
                      "AUDIT.md must name the qcells lab's canonical repo")

    def test_local_path_not_present_without_repo_name(self):
        # The bare local path may appear only alongside the repo name
        # (it is quoted history, not the citation).
        text = AUDIT.read_text(encoding="utf-8")
        idx = text.find("workspace/labs/qcells")
        self.assertNotEqual(idx, -1, "local path history should be quoted")
        window = text[max(0, idx - 600):idx + 600]
        self.assertIn("SuperInstance/micrograd-quilt", window,
                      "local path must be framed by the repo citation")


if __name__ == "__main__":
    unittest.main()
