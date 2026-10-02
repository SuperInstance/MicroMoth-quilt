#!/usr/bin/env python3
"""tools/selfplay.py — exp015/selfplay-d1: bug-injection self-play loop.

Instrument that measures the mutation-battery catch-rate of the tests/
suite against synthetic bugs in micromoth.py, matched to the shape
vocabulary the tests themselves pin (see experiments/selfplay/PIN.md,
SHAPES.md).

Doctrine: honest negatives; receipts before conclusions; temp-copy
mutation only (the working tree's micromoth.py is NEVER mutated); caught
is delta-based vs a pristine baseline run in the same harness (main has
one pre-existing RED, test_import_baseline manifest drift — see PIN.md).

Run: python3 tools/selfplay.py          # baseline + 60 rounds + summary
     python3 tools/selfplay.py --rounds-per-shape 2 --canaries 12
Stdlib only. Receipts land in experiments/selfplay/rounds/.

Widening (2026-10-01, seal-pin lane, PR#30 follow-up): phase_sign_flip
gains a |1>-branch variant (rz degenerates to a global phase) and
noise_mixing_swap gains a per-qubit mis-index variant (noise_model[0]);
both are caught by the widening pins in tests/test_widening_pins.py,
which also carry the boundary-draw canary (r == cumu equality injected
deliberately at interior and total boundaries).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
KERNEL = LAB / "micromoth.py"
BATTERY = LAB / "tests"
OUT = LAB / "experiments" / "selfplay"
ROUNDS = OUT / "rounds"
ROOTS = [7, 11, 23]
TIMEOUT_S = 120

# ---------------------------------------------------------------- shapes
# Each shape carries >=1 concrete variant. A variant is a list of edits:
# (anchor, replacement, occurrence_index). Synthesis fails loudly if an
# anchor is absent -> recorded as an honest negative, never silently.
SHAPES = {
    "opcode_swap": [
        {"desc": "single-qubit dispatch: x gate performs superpose, h gate performs bit-flip",
         "edits": [(
             "          if gate[0]=='x': # For x, just flip the values\n"
             "            k[b0],k[b1]=k[b1],k[b0]\n"
             "          elif gate[0]=='h': # For x, superpose them\n"
             "            k[b0],k[b1]=superpose(k[b0],k[b1])",
             "          if gate[0]=='x': # For x, just flip the values\n"
             "            k[b0],k[b1]=superpose(k[b0],k[b1])\n"
             "          elif gate[0]=='h': # For x, superpose them\n"
             "            k[b0],k[b1]=k[b1],k[b0]", 0)]},
    ],
    "two_qubit_opcode_swap": [
        {"desc": "cx performs swap's body; swap performs cx's body",
         "edits": [(
             "            if gate[0]=='cx':\n"
             "                k[b10],k[b11]=k[b11],k[b10] # Flip the values.\n"
             "            elif gate[0]=='crx':\n"
             "                k[b10],k[b11]=turn(k[b10],k[b11],theta) # Perform the rotation.\n"
             "            elif gate[0]=='swap':\n"
             "                k[b01],k[b10]=k[b10],k[b01] # Flip the values.",
             "            if gate[0]=='cx':\n"
             "                k[b01],k[b10]=k[b10],k[b01] # Flip the values.\n"
             "            elif gate[0]=='crx':\n"
             "                k[b10],k[b11]=turn(k[b10],k[b11],theta) # Perform the rotation.\n"
             "            elif gate[0]=='swap':\n"
             "                k[b10],k[b11]=k[b11],k[b10] # Flip the values.", 0)]},
    ],
    "literal_rewrite": [
        {"desc": "r2 constant truncated 0.70710678118 -> 0.7071",
         "edits": [("r2=0.70710678118 # 1/sqrt(2) will come in handy",
                    "r2=0.7071 # 1/sqrt(2) will come in handy", 0)]},
        {"desc": "r2 constant perturbed in the 9th decimal",
         "edits": [("r2=0.70710678118", "r2=0.70710678119", 0)]},
    ],
    "theta_rescale": [
        {"desc": "rx branch passes 2*theta to turn (theta/2 halving defeated)",
         "edits": [("k[b0],k[b1]=turn(k[b0],k[b1],theta)",
                    "k[b0],k[b1]=turn(k[b0],k[b1],2*theta)", 0)]},
        {"desc": "crx branch passes 2*theta to turn",
         "edits": [("k[b10],k[b11]=turn(k[b10],k[b11],theta)",
                    "k[b10],k[b11]=turn(k[b10],k[b11],2*theta)", 0)]},
    ],
    "phase_sign_flip": [
        {"desc": "phaseturn drops the minus inside sin(-theta/2) for the y-component",
         "edits": [("x[1]*cos(theta/2) + x[0]*sin(-theta/2)",
                    "x[1]*cos(theta/2) + x[0]*sin(theta/2)", 0)]},
        {"desc": "phaseturn conjugates the |1> branch (both sin(+theta/2) -> "
                 "sin(-theta/2)): rz degenerates to a GLOBAL phase",
         "edits": [("[y[0]*cos(theta/2) - y[1]*sin(+theta/2),y[1]*cos(theta/2) + y[0]*sin(+theta/2)]",
                    "[y[0]*cos(theta/2) - y[1]*sin(-theta/2),y[1]*cos(theta/2) + y[0]*sin(-theta/2)]", 0)]},
    ],
    "boundary_offbyone": [
        {"desc": "shot-sampling loop drops the final shot (range(shots) -> range(shots-1))",
         "edits": [("for _ in range(shots):", "for _ in range(shots-1):", 0)]},
        {"desc": "single-qubit pair loop iterates one extra low index",
         "edits": [("for i0 in range(2**j):", "for i0 in range(2**j+1):", 0)]},
    ],
    "noise_mixing_swap": [
        {"desc": "measurement-error mixing weights inverted on both branches",
         "edits": [("probs[b0] = (1-p_meas)*p0 + p_meas*p1",
                    "probs[b0] = p_meas*p0 + (1-p_meas)*p1", 0),
                   ("probs[b1] = (1-p_meas)*p1 + p_meas*p0",
                    "probs[b1] = (1-p_meas)*p0 + p_meas*p1", 0)]},
        {"desc": "per-qubit mis-index: every qubit reads noise_model[0] "
                 "(invisible to uniform noise and to re-label-invariant Bell pins)",
         "edits": [("p_meas = noise_model[j]", "p_meas = noise_model[0]", 0)]},
    ],
    "comparison_flip": [
        {"desc": "sampling acceptance r<cumu -> r<=cumu (boundary double-count risk)",
         "edits": [("if r<cumu and un:", "if r<=cumu and un:", 0)]},
    ],
    "measurement_map_swap": [
        {"desc": "output-bit assembly writes out_list[bit] instead of out_list[qc.num_clbits-1-bit] (bit-order flip)",
         "edits": [("out_list[qc.num_clbits-1-bit] = raw_out[qc.num_qubits-1-outputnum_clbitsap[bit]]",
                    "out_list[bit] = raw_out[qc.num_qubits-1-outputnum_clbitsap[bit]]", 0)]},
    ],
    "gate_noop": [
        {"desc": "x gate body replaced with no-op self-swap (gate silently dropped)",
         "edits": [("          if gate[0]=='x': # For x, just flip the values\n"
                    "            k[b0],k[b1]=k[b1],k[b0]",
                    "          if gate[0]=='x': # For x, just flip the values\n"
                    "            k[b0],k[b1]=k[b0],k[b1]", 0)]},
    ],
    "init_state_perturb": [
        {"desc": "all-|0> initialization becomes k[0]=[0.0,1.0] (imaginary amplitude)",
         "edits": [("k[0] = [1.0,0.0] # Then a single 1 to create the all |0> state.",
                    "k[0] = [0.0,1.0] # Then a single 1 to create the all |0> state.", 0)]},
    ],
    "return_value_perturb": [
        {"desc": "probs drops the imaginary-amplitude contribution (e[0]**2 only)",
         "edits": [("probs = [e[0]**2+e[1]**2 for e in k]",
                    "probs = [e[0]**2 for e in k]", 0)]},
    ],
}

# --------------------------------------------------------------- miner
MINER_PATTERNS = {
    "exact-counts/histogram pins": r"counts|histogram|shots",
    "seeded-rng / root replication pins": r"seed|root|rng",
    "statevector / probability pins": r"statevector|probab",
    "balance / symmetry pins (Bell, GHZ)": r"balance|Bell|GHZ",
    "hash-chain / receipt tamper pins": r"fnv|sha256|chain|tamper|seal",
    "noise-model pins": r"noise",
    "memory-output / ordering pins": r"memory|clbit|order",
}


def mine_shapes() -> dict:
    """Scan the battery for the pinned-property vocabulary; emit taxonomy."""
    taxonomy = {}
    for test_file in sorted(BATTERY.glob("test_*.py")):
        text = test_file.read_text()
        for label, pat in MINER_PATTERNS.items():
            hits = len(re.findall(pat, text, re.IGNORECASE))
            if hits:
                taxonomy.setdefault(label, {})[test_file.name] = hits
    return taxonomy


def write_shapes_md(taxonomy: dict) -> None:
    lines = [
        "# SHAPES.md — mutation-shape taxonomy (mined from tests/)",
        "",
        "Auto-generated by tools/selfplay.py at run time. Two halves:",
        "A) what the battery actually pins (evidence = grep counts per test),",
        "B) the synthetic-bug shapes the synthesizer can build against those pins.",
        "",
        "## A) Pinned-property vocabulary found in the battery",
        "",
        "(note: `qcells/` does not exist on any branch; `tests/` IS the battery — 16 files)",
        "",
    ]
    for label, files in taxonomy.items():
        lines.append(f"### {label}")
        for name, hits in sorted(files.items()):
            lines.append(f"- `{name}`: {hits} hit(s)")
        lines.append("")
    lines += ["## B) Synthetic-bug shape catalog (synthesizer vocabulary)", ""]
    for shape, variants in SHAPES.items():
        lines.append(f"### `{shape}` ({len(variants)} variant(s))")
        for v in variants:
            lines.append(f"- {v['desc']}")
        lines.append("")
    (OUT / "SHAPES.md").write_text("\n".join(lines))


# ------------------------------------------------------------ synthesizer
def synthesize(src: str, shape: str, variant_idx: int) -> tuple[str, str]:
    """Apply variant edits to a source string. Raises on missing anchor."""
    variants = SHAPES[shape]
    v = variants[variant_idx % len(variants)]
    out = src
    for old, new, occ in v["edits"]:
        parts = out.split(old)
        if len(parts) - 1 < occ + 1:
            raise ValueError(f"anchor missing (occ {occ}): {old[:60]!r}")
        head = old.join(parts[: occ + 1])
        tail = old.join(parts[occ + 1:])
        out = head + new + tail
    return out, v["desc"]


# ---------------------------------------------------------------- runner
def stage(tmp: Path, kernel_src: str | None) -> None:
    """Copy the battery's world into tmp; optionally swap in a mutated kernel.

    Everything except VCS internals and this experiment's own output dir is
    staged, so doc-presence pins (test_cell_mapping) see the same world as
    a repo-root run. Only micromoth.py is ever written with mutated content.
    """
    for src in LAB.iterdir():
        if src.name in (".git", "experiments", "__pycache__"):
            continue
        dst = tmp / src.name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    if kernel_src is not None:
        (tmp / "micromoth.py").write_text(kernel_src)


SUMMARY_RE = re.compile(r"^(?P<n>\d+) failed|(?P<p>\d+) passed", re.M)


def run_battery(tmp: Path) -> dict:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no",
             "-p", "no:cacheprovider"],
            cwd=tmp, capture_output=True, text=True, timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"harness_crash": True, "reason": f"timeout>{TIMEOUT_S}s",
                "battery_ms": int((time.monotonic() - t0) * 1000)}
    ms = int((time.monotonic() - t0) * 1000)
    out = proc.stdout + proc.stderr
    failed = set(re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M))
    m = re.findall(r"(\d+) failed", out)
    p = re.findall(r"(\d+) passed", out)
    e = re.findall(r"(\d+) error", out)
    parsed = bool(m or p or e)
    return {
        "harness_crash": not parsed,
        "reason": "pytest produced no parseable summary" if not parsed else "",
        "rc": proc.returncode, "battery_ms": ms,
        "failed_n": int(m[0]) if m else 0,
        "passed_n": int(p[0]) if p else 0,
        "error_n": int(e[0]) if e else 0,
        "failed_nodeids": sorted(failed),
    }


def receipt(round_id: int, shape: str, desc: str, verdict: dict) -> dict:
    rec = {
        "round": round_id,
        "shape": shape,
        "mutation_desc": desc,
        "roots": ROOTS,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    rec.update(verdict)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds-per-shape", type=int, default=4)
    ap.add_argument("--canaries", type=int, default=12)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    ROUNDS.mkdir(parents=True, exist_ok=True)
    write_shapes_md(mine_shapes())

    pristine = KERNEL.read_text()

    # --- baseline (delta semantics; see PIN.md) ---
    with tempfile.TemporaryDirectory() as td:
        stage(Path(td), None)
        base = run_battery(Path(td))
    if base["harness_crash"]:
        print(json.dumps({"failure_mode": "baseline harness crash", "detail": base}))
        return 2
    baseline_failures = set(base["failed_nodeids"])
    (ROUNDS / "round-000-baseline.json").write_text(json.dumps(receipt(
        0, "baseline", "pristine kernel copy; delta reference for all rounds",
        {**base, "caught": None, "baseline_failures": sorted(baseline_failures)}),
        indent=2))
    print(f"baseline: {base['passed_n']} passed / {base['failed_n']} failed "
          f"({base['battery_ms']}ms) failures={sorted(baseline_failures)}")

    # --- round schedule: shapes x rounds-per-shape, canaries interleaved ---
    shape_names = list(SHAPES)
    schedule = []
    for shape in shape_names:
        for i in range(args.rounds_per_shape):
            schedule.append((shape, i, None))
    for c in range(args.canaries):
        shape = shape_names[c % len(shape_names)]
        schedule.insert((c * len(schedule)) // max(1, args.canaries),
                        (shape, c // len(shape_names), f"canary-{c+1:02d}"))

    canaries_injected = 0
    canaries_caught = 0
    totals = {s: {"rounds": 0, "caught": 0, "missed": 0,
                  "synthesis_failed": 0, "harness_crash": 0} for s in shape_names}
    round_id = 0
    honest = {"synthesis_failed": [], "harness_crash": [], "ambiguous": []}

    for shape, vidx, canary in schedule:
        round_id += 1
        verdict = {}
        desc = f"{shape} variant {vidx}"
        try:
            mutated, desc = synthesize(pristine, shape, vidx)
        except ValueError as ex:
            verdict = {"caught": None, "verdict": "synthesis_failed",
                       "error": str(ex), "battery_ms": 0}
            totals[shape]["synthesis_failed"] += 1
            honest["synthesis_failed"].append({"round": round_id, "shape": shape,
                                               "error": str(ex)})
        else:
            if canary:
                canaries_injected += 1
                desc = f"[{canary} seed=sha256('{canary}')] {desc}"
            with tempfile.TemporaryDirectory() as td:
                stage(Path(td), mutated)
                res = run_battery(Path(td))
            if res["harness_crash"]:
                verdict = {"caught": None, "verdict": "harness_crash",
                           "reason": res["reason"], "battery_ms": res["battery_ms"]}
                totals[shape]["harness_crash"] += 1
                honest["harness_crash"].append({"round": round_id, "shape": shape})
            else:
                new_failures = sorted(set(res["failed_nodeids"]) - baseline_failures)
                caught = len(new_failures) > 0
                verdict = {
                    "caught": caught,
                    "verdict": "caught" if caught else "missed",
                    "new_failures": new_failures,
                    "baseline_failures_present": sorted(
                        set(res["failed_nodeids"]) & baseline_failures),
                    **{k: res[k] for k in ("rc", "battery_ms", "failed_n",
                                           "passed_n", "error_n")},
                }
                totals[shape]["rounds"] += 1
                if caught:
                    totals[shape]["caught"] += 1
                    if canary:
                        canaries_caught += 1
                else:
                    totals[shape]["missed"] += 1
                    if res["error_n"]:
                        honest["ambiguous"].append(
                            {"round": round_id, "shape": shape,
                             "note": f"{res['error_n']} error(s) but no new "
                                     "nodeid vs baseline"})
        rec = receipt(round_id, shape, desc, verdict)
        rec["canary"] = canary
        if canary:
            rec["canary_seed"] = hashlib.sha256(canary.encode()).hexdigest()[:16]
        (ROUNDS / f"round-{round_id:03d}.json").write_text(json.dumps(rec, indent=2))
        print(f"round {round_id:03d} {shape:<24} "
              f"{verdict.get('verdict', '?'):<18} {verdict.get('battery_ms', 0)}ms"
              + (f" NEW={verdict['new_failures']}" if verdict.get("new_failures") else ""))

    # --- summary ---
    crashed = sum(t["harness_crash"] for t in totals.values())
    synth_failed = sum(t["synthesis_failed"] for t in totals.values())
    ran = sum(t["rounds"] for t in totals.values())
    caught_total = sum(t["caught"] for t in totals.values())
    lines = [
        "# SUMMARY.md — exp015/selfplay-d1 catch-rate report",
        "",
        f"Generated by tools/selfplay.py. Baseline: {base['passed_n']} passed / "
        f"{base['failed_n']} pre-existing failed ({base['battery_ms']}ms)."
        " Catch is DELTA-based vs baseline (see PIN.md).",
        "",
        "## Catch-rate by shape (caught/(caught+missed); refuting harness crashes and",
        "## synthesis failures excluded from denominators)",
        "",
        "| shape | rounds | caught | missed | catch_rate | harness_crash | synth_fail |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in shape_names:
        t = totals[s]
        denom = t["caught"] + t["missed"]
        rate = f"{t['caught']/denom:.2f}" if denom else "n/a"
        lines.append(f"| `{s}` | {t['rounds']} | {t['caught']} | {t['missed']} "
                     f"| {rate} | {t['harness_crash']} | {t['synthesis_failed']} |")
    overall = f"{caught_total/ran:.2f}" if ran else "n/a"
    lines += [
        "",
        f"Overall: {caught_total}/{ran} rounds caught (rate {overall}).",
        f"Canaries: {canaries_caught}/{canaries_injected} caught.",
        f"Harness crashes: {crashed} (refutation threshold: >30% of injected bugs).",
        "",
        "## Honest negatives",
        "",
    ]
    neg_items = []
    if honest["synthesis_failed"]:
        neg_items.append(f"- Synthesis failures (anchor drift): {honest['synthesis_failed']}")
    if honest["harness_crash"]:
        neg_items.append(f"- Harness crashes: {honest['harness_crash']}")
    if honest["ambiguous"]:
        neg_items.append(f"- Ambiguous verdicts (errors but no new nodeid): {honest['ambiguous']}")
    neg_items.append("- In staged (temp-copy) worlds the manifest pin fails "
                     "ENVIRONMENTALLY, not semantically: the staged copy has "
                     "no .git, so import_manifest.build()'s `git ls-files` "
                     "cannot run — the pin is always in baseline_failures and "
                     "excluded from catch deltas. The real tree's seal is "
                     "owned by tests/test_import_baseline.py, the CI "
                     "seal-check job (.github/workflows/seal.yml) and the "
                     "pre-push hook (tools/install_hooks.sh).")
    neg_items.append("- `qcells/` named in the lane spec does not exist on any "
                     f"branch; the instrument ran against `tests/` "
                     f"({len(list(BATTERY.glob('test_*.py')))} files). "
                     "Deviation D1.")
    neg_items.append("- receipts always carry roots [7,11,23]; the battery's own "
                     "seeded tests self-seed (exp012/exp013 use roots 7/11/23 "
                     "internally), so roots are recorded as provenance, not "
                     "plumbed into micromoth (it has no seed parameter).")
    lines += neg_items + [
        "",
        "## Next probes",
        "",
        "- RESOLVED (PR#30): the baseline manifest drift was root-caused "
        "(auto-push writer commits without re-sealing) and pinned — "
        "tools/import_manifest.py --check + CI seal-check + pre-push hook.",
        "- Boundary_offbyone variant 2 (extra low index) targets arithmetic, not "
        "semantics — measure whether any battery test pins loop-trip counts.",
        "- Add shapes for crx-only paths and memory-output ordering; both are "
        "thinly pinned per SHAPES.md section A.",
    ]
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n")

    print(json.dumps({
        "rounds_ran": ran, "caught": caught_total,
        "overall_rate": overall, "canaries_caught": canaries_caught,
        "canaries_injected": canaries_injected,
        "harness_crashes": crashed, "synthesis_failures": synth_failed,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
