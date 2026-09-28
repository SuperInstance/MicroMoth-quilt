#!/usr/bin/env python3
"""import_manifest.py — seal the dormant lane's import baseline.

MicroMoth-quilt is a fork of moth-quantum/MicroMoth, imported while the
quilt-native lane sleeps. This baseline answers the question the lane
will ask on day one: WHAT EXACTLY DID WE IMPORT?

The manifest binds every git-tracked file's sha256 plus the upstream
provenance. tests/test_import_baseline.py re-derives it; drift trips
RED by name.

REGENERATION IS THE DECLARED RE-EMBED: after any intentional change to
the imported tree, rerun this tool and commit the manifest WITH the
change. Never edit receipts/import-baseline.json by hand.

Usage: python3 tools/import_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
MANIFEST = LAB / "receipts" / "import-baseline.json"
UPSTREAM = "moth-quantum/MicroMoth"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(LAB), "ls-files"], capture_output=True, text=True, check=True)
    return [l for l in out.stdout.splitlines() if l]


def head_commit() -> str:
    out = subprocess.run(
        ["git", "-C", str(LAB), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True)
    return out.stdout.strip()


def build() -> dict:
    # Fixed-point note: the manifest cannot embed a digest of itself (a
    # sha256 self-reference is uncomputable), so it is excluded from the
    # files map and recorded explicitly instead.
    self_rel = MANIFEST.relative_to(LAB).as_posix()
    files = {rel: sha256(LAB / rel) for rel in tracked_files() if rel != self_rel}
    return {
        "schema": "micromoth-quilt/import-baseline@v1",
        "upstream": UPSTREAM,
        "baseline_commit": head_commit(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "self": self_rel + " (excluded: sha256 fixed-point, cannot embed own digest)",
        "doctrine": "regenerate via tools/import_manifest.py; never edit by hand",
        "files": files,
    }


def main() -> None:
    manifest = build()
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"sealed: {len(manifest['files'])} tracked files @ "
          f"{manifest['baseline_commit'][:12]}…")


if __name__ == "__main__":
    main()
