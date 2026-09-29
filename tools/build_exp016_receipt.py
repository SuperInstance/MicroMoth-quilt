"""Build receipts/exp016-hybrid.json (results-kind seal) from the
sealed artifacts in receipts/exp016-hybrid/. Integrity table covers
every file in the artifact dir byte-for-byte. Never edit the receipt
or artifacts by hand after sealing — a drifted byte voids the seal."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ART = HERE / "receipts" / "exp016-hybrid"
results = json.loads((ART / "exp016.results.json").read_text())

artifacts = sorted(p.name for p in ART.iterdir() if p.is_file())
integrity = {name: hashlib.sha256((ART / name).read_bytes()).hexdigest()
             for name in artifacts}

ct = results["crossing_table"]
receipt = {
    "schema": "micromoth-quilt/exp-receipt@v1",
    "receipt_kind": "results",
    "experiment": "exp016-hybrid",
    "status": "SEALED",
    "title": "skeleton-seed + MAP-Elites archive hybrid on the exp014 "
             "fresh-root panel — ARCHIVE NEUTRAL (6/8, top of the "
             "pre-registered neutral band): the archive converts the "
             "champion-local hard class (29/31/37) but loses the easy "
             "class (17/19); SKELETON-IS-A-RATE stands",
    "directive": "2026-09-29: iterate locally on MicroMoth-quilt "
                 "(qcells lab, workspace/labs/qcells)",
    "engine": {
        "name": "micromoth",
        "vendored_sha256": "bbd10ac2ffd4dd8bdee86480866107b3c0917ab09286b1d9e2ed144faed482df",
        "note": "matches the import-baseline manifest pin on main",
    },
    "seeds": {"roots": [3, 5, 13, 17, 19, 29, 31, 37],
              "shots": 512, "train": 101, "verify": 202},
    "question": results["question"],
    "design": results["design"],
    "success_threshold_verify_balance": 0.45,
    "pre_run_pin": results["pre_run_pin"],
    "artifacts": artifacts,
    "integrity": integrity,
    "results": {
        "verdict": results["verdict"],
        "guard_exp001_reproduced": results["guard_exp001_reproduced"],
        "hybrid_crosses": results["hybrid_crosses"],
        "hybrid_cross_fraction": results["hybrid_cross_fraction"],
        "root_agreement_with_exp014": results["root_agreement_with_exp014"],
        "crossing_table": ct,
    },
    "cross_receipts": {
        "exp005": "the freeze being tested: unaided single-fitness "
                  "champion search stays at champion_verify_balance 0.0 "
                  "on this lane",
        "exp012": "ROOT-LOTTERY doctrine (merged PR #17): crossing "
                  "claims carry N/M roots + measured rate, never bare "
                  "'crosses' — the 6/8-vs-4/8 root-disjoint draw is "
                  "read exactly that way here",
        "exp013": "partial-plateau class (merged PR #18): r19's 0.2422 "
                  "hybrid max is that class, named not rounded",
        "exp014": "the comparator: SKELETON IS A RATE, champion-local "
                  "4/8 on this exact panel (receipt commit 793a771, "
                  "PR #19 Casey-gated at seal time — comparator data "
                  "embedded in results.json with provenance, no pin "
                  "depends on exp014 files being on main)",
        "exp015": "the archive regime being hybridized (PR #21 "
                  "Casey-gated at seal time): elitism-artifact partial "
                  "signal, skeleton 3/3 on roots 7/11/23 — this "
                  "experiment extends the regime comparison to the "
                  "discriminating fresh-root panel",
    },
    "honest_limits": [
        "ARCHIVE NEUTRAL is the pre-registered 3-6/8 band verdict, and "
        "6/8 sits at its TOP edge — the honest read is 'no evidence the "
        "archive moves the crossing rate' combined with the observed "
        "asymmetry, not 'proven identical': hybrid crosses 6/8 "
        "({3,5,13,29,31,37}) vs champion-local 4/8 ({3,13,17,19}), "
        "agreement only {3,13}. Per exp012 ROOT-LOTTERY doctrine a "
        "root-disjoint draw of this size is an N/M rate read, not a "
        "mechanism victory.",
        "ASYMMETRY NAMED, NOT EXPLAINED: the archive converts the "
        "champion-local HARD class (29/31/37 all cross, gens 4/7/3) "
        "but LOSES the EASY class (17 stops at 0.4355, 19 at 0.2422 "
        "— the exp013 partial plateau). Coverage-driven parents "
        "sample partial-plateau cells that pull children off the "
        "champion-local route on easy roots. A 'CHAMPION LOCALITY IS "
        "THE LAW' reading is available on the easy class alone; the "
        "pre-registered band (count over the whole panel) governs the "
        "verdict, the asymmetry is reported for the follow-up lane.",
        "Root 19's 0.2422 and root 17's 0.4355 are NAMED at their "
        "measured values, never rounded up to the 0.45 bar.",
        "results-style receipt (no witness LEDGER; exp001 remains the "
        "lane's only LEDGER receipt) — sealed artifacts are runner + "
        "results.json + telemetry jsonl, and the receipt's sha256 "
        "table must match every file byte-for-byte or the seal is "
        "void. The runner is sealed as the exact bytes executed in "
        "the qcells lab (workspace/labs/qcells).",
        "The exp014 comparator is embedded with provenance (commit "
        "793a771, PR #19 Casey-gated, NOT merged at seal time); if "
        "exp014's merged numbers ever disagree, this receipt's "
        "comparator pins must be re-audited, not silently trusted.",
        "12 gens x pop 16 is the exp015 archive budget, not an "
        "asymptotic sample: a rate difference smaller than one "
        "root-in-8 is below this experiment's resolution.",
    ],
}
out = HERE / "receipts" / "exp016-hybrid.json"
out.write_text(json.dumps(receipt, indent=2) + "\n")
print("sealed", out, len(artifacts), "artifacts")
