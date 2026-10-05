# PRISTINE AUDIT — PR #43 (rung-1 IonQ SIM pre-flight)

- **Audited commit:** ca15c13 (branch `ionq-rung1-sim-preflight`, PR SuperInstance/MicroMoth-quilt#43)
- **Audit time:** 2026-10-05 13:3x CST (snowball pulse)
- **Runner:** `scripts/fresh-audit-pr.sh` (workspace wrapper; canonical tool quilt-tools fresh-audit v0), selftest 3/3 green this window
- **Law:** pins ran inside a fresh `--depth 1` clone of the pushed branch, CWD anchored to clone root — never the author's tree (R85 phantom-RED class)
- **Pins:** `python3 tools/import_manifest.py --check && python3 -m pytest -q`
- **Result:** SEAL OK sealed=524 tracked=524 unsealed=0 drifted=0 orphaned=0; pytest **351 passed** in 7.01s; `fresh-audit: PASS` on both runs
- **Why this receipt exists:** the adopted rule (queue RULES, 15:05 10/4) requires pins PRISTINE for every PR opened or trusted. #44 (rung-2, stacked on this branch) was receipt'd at 12:19; the rung-1 base it stacks on had no receipt of its own — this closes that gap on the pushed head.
- **Honest limit:** audit covers tree at ca15c13 exactly; this receipt commit + re-seal changes the tree, sealed afresh below (524→525).
