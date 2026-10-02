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

SEAL PIN: the drift-catcher only works if it runs. Two enforcers call the
read-only mode so drift can no longer slip through silently:

    python3 tools/import_manifest.py --check   # verify only; exit 0 clean,
                                               # 1 drift, 2 manifest broken

  - CI (workflow job `seal-check`) runs --check on every push/PR;
  - the pre-push hook (tools/hooks/pre-push, installed via
    tools/install_hooks.sh) blocks `git push` on drift, so the overnight
    auto-push writer cannot ship artifacts it forgot to re-seal.

Usage: python3 tools/import_manifest.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
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
    # The manifest must never hash itself: no fixed point exists (writing the
    # file changes the bytes the entry commits to). Excluded by path.
    return [l for l in out.stdout.splitlines() if l and l != "receipts/import-baseline.json"]


def head_commit() -> str:
    out = subprocess.run(
        ["git", "-C", str(LAB), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True)
    return out.stdout.strip()


def build() -> dict:
    # Fixed-point note: the manifest cannot embed a digest of itself (a
    # sha256 self-reference is uncomputable), so it is excluded from the
    # files map and recorded explicitly instead.
    self_path = self_rel()
    files = {rel: sha256(LAB / rel) for rel in tracked_files() if rel != self_path}
    return {
        "schema": "micromoth-quilt/import-baseline@v1",
        "upstream": UPSTREAM,
        "baseline_commit": head_commit(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "self": self_path + " (excluded: sha256 fixed-point, cannot embed own digest)",
        "doctrine": "regenerate via tools/import_manifest.py; never edit by hand",
        "files": files,
    }


def self_rel() -> str:
    return MANIFEST.relative_to(LAB).as_posix()


def live_map() -> dict[str, str]:
    """Digest of every currently tracked file (read-only; writes nothing)."""
    self_path = self_rel()
    return {rel: sha256(LAB / rel) for rel in tracked_files() if rel != self_path}


def verify() -> tuple[bool, list[str], str, bool]:
    """Read-only drift check against the sealed manifest.

    Returns (ok, problem_lines, summary, fatal). Never writes: this is the
    mode the seal pin (CI job + pre-push hook) calls. Problem lines name
    the file and the drift class so the remedy is unambiguous. fatal=True
    means the manifest itself is missing/unreadable (exit 2, not 1).
    """
    if not MANIFEST.exists():
        return False, [
            f"MANIFEST MISSING: {MANIFEST.relative_to(LAB)}",
        ], "manifest absent", True
    try:
        on_disk = json.loads(MANIFEST.read_text())
    except (json.JSONDecodeError, OSError) as ex:
        return False, [
            f"MANIFEST UNREADABLE: {ex}",
        ], "manifest unreadable", True
    sealed = on_disk.get("files")
    if not isinstance(sealed, dict):
        return False, [
            "MANIFEST MALFORMED: 'files' map absent",
        ], "manifest malformed", True

    live = live_map()
    unsealed = sorted(set(live) - set(sealed))
    orphaned = sorted(set(sealed) - set(live))
    drifted = sorted(f for f in set(live) & set(sealed) if live[f] != sealed[f])

    problems: list[str] = []
    problems += [f"UNSEALED  {f}  (tracked, absent from manifest)" for f in unsealed]
    problems += [f"DRIFTED   {f}  (content changed since seal)" for f in drifted]
    problems += [f"ORPHANED  {f}  (sealed, no longer tracked)" for f in orphaned]

    summary = (f"sealed={len(sealed)} tracked={len(live)} "
               f"unsealed={len(unsealed)} drifted={len(drifted)} "
               f"orphaned={len(orphaned)}")
    return (not problems), problems, summary, False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="read-only: verify the seal, exit 0 clean / 1 drift / "
                         "2 manifest missing or unreadable; never writes")
    args = ap.parse_args()

    if args.check:
        ok, problems, summary, fatal = verify()
        if ok:
            print(f"SEAL OK: {summary}")
            return
        print(f"SEAL DRIFT — {summary}", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        print(
            "  remedy: python3 tools/import_manifest.py  (re-seal) and commit "
            "receipts/import-baseline.json WITH your change",
            file=sys.stderr)
        raise SystemExit(2 if fatal else 1)

    manifest = build()
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"sealed: {len(manifest['files'])} tracked files @ "
          f"{manifest['baseline_commit'][:12]}…")


if __name__ == "__main__":
    main()
