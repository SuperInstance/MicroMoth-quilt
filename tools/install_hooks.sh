#!/usr/bin/env bash
# install_hooks.sh — activate the repo's seal pins in THIS clone.
#
# Git hooks are not transferred by clone/push, so each clone runs this
# once (idempotent; safe to re-run after pull if the hook changes):
#
#     tools/install_hooks.sh
#
# Installs tools/hooks/pre-push -> .git/hooks/pre-push (the import-manifest
# seal pin). CI enforces the same check remotely; the hook enforces it
# locally so drift is caught before it ever leaves the machine.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/tools/hooks/pre-push"
dst="$root/.git/hooks/pre-push"

if [[ ! -d "$root/.git/hooks" ]]; then
  echo "install_hooks: $root/.git/hooks not found (not a git worktree?)" >&2
  exit 2
fi

cp "$src" "$dst"
chmod 755 "$dst"
echo "install_hooks: seal pin active -> $dst"
echo "install_hooks: every 'git push' now runs 'tools/import_manifest.py --check' first"
