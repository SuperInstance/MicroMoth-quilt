"""exp012 — 3-seed replication of exp011 arm B (the reach fix that
CROSSED UNSEEDED), closing the single-root-seed honest limit.

exp011 arm B (parent_pool=True: one-move children off parents sampled
uniformly from the champion+children cloud) was the FIRST unaided
crossing on a balance-gated target: held-out verify 0.4824 at gen 5
on root seed 7 — but exactly one root seed. exp011's honest limit
named this experiment BEFORE any doctrine-hardening.

Design pin BEFORE running: vary ONLY the root seed (new roots 11, 23,
42; root 7 already run as exp011). train/verify/shots/targets/policy
stay the named exp005 lane values — a replication that changes the
fitness stream is a different experiment. Each root runs TWO arms:

  unaided: parent_pool=False, classed one-move cloud (the exp005
           frozen lane — per-seed freeze baseline, guard against
           'root 7 was just easy')
  poolB:   parent_pool=True, same mutator (the exp011 arm B claim)

Interpretation pinned BEFORE running: poolB crossing on >= 2 of 3 new
roots = the genealogy reach fix REPLICATES, 'birth proximity is not
the only path' hardens toward engine law. poolB crossing on exactly
1 root total (7) = the crossing is root-lottery, freeze verdict
softens to 'champion-locality holds except favorable genealogies' —
doctrine must keep seeding primary. unaided arm freezing on all 3 new
roots = exp005 freeze replicates too (expected).

Success = held-out balance >= 0.45 (same threshold exp005-exp011).
Telemetry per arm per root. exp001 reproduction guard runs the
default lane in-harness (parent_pool default False, must reproduce
byte-identical).
"""
import functools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qcell.search import mutate_classed, run_search

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp012.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
NEW_ROOTS = (11, 23, 42)

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))

# --- guard: default lane still reproduces exp001 -------------------------
ctrl_telem = LAB / "experiments" / "exp012.telemetry.control.jsonl"
if ctrl_telem.exists():
    ctrl_telem.unlink()
ctrl_res = run_search(7, generations=8, pop=16, shots=SHOTS,
                      train_seed=TRAIN, verify_seed=VERIFY,
                      telemetry_path=str(ctrl_telem))
exp001 = json.loads(EXP001.read_text())
control_ok = (ctrl_res["curve"] == exp001["curve"]
              and ctrl_res["champion"].genome == exp001["champion_genome"])
print("control reproduces exp001:", control_ok)
if not control_ok:
    print("FATAL: exp012 harness changed default behavior; "
          "refusing to write results")
    sys.exit(1)

runs = []
for root in NEW_ROOTS:
    for arm, kw in (("unaided", dict(parent_pool=False)),
                    ("poolB", dict(parent_pool=True))):
        telem = LAB / "experiments" / \
            f"exp012.telemetry.r{root}.{arm}.jsonl"
        if telem.exists():
            telem.unlink()
        res = run_search(root, generations=GENS, pop=POP, shots=SHOTS,
                         train_seed=TRAIN, verify_seed=VERIFY,
                         telemetry_path=str(telem), targets=TARGETS,
                         n_qubits=N, mode="balance",
                         mutate_fn=mutate_one, **kw)
        champ = res["champion"]
        first_ok = next((r["gen"] for r in res["curve"]
                         if r["verify_p"] >= 0.45), None)
        runs.append({
            "root_seed": root,
            "arm": arm,
            "champion_genome": champ.genome,
            "champion_len": len(champ.genome),
            "champion_train_p": champ.train_p,
            "champion_verify_p": champ.verify_p,
            "first_ge_045_gen": first_ok,
            "crossed": first_ok is not None,
            "champ_balances": [r["train_p"] for r in res["curve"]],
        })
        print(f"root {root} {arm}: crossed={first_ok is not None} "
              f"first_ge_045_gen={first_ok} verify={champ.verify_p:.4f}")

pool_crosses = [r["root_seed"] for r in runs
                if r["arm"] == "poolB" and r["crossed"]]
unaided_crosses = [r["root_seed"] for r in runs
                   if r["arm"] == "unaided" and r["crossed"]]
replicates = len(pool_crosses) >= 2
exp011_crossed = True  # arm B root 7, booked in exp011.results.json

summary = {
    "experiment": "exp012_seed_replication",
    "question": "does exp011 arm B (parent_pool genealogy reach) "
                "replicate across root seeds, or is the unaided "
                "crossing a root-7 lottery?",
    "design": "only root seed varies (11/23/42 new; 7 = exp011); "
              "train=101 verify=202 shots=512 targets 000/111 n=3 "
              "balance pop16 gens12 jitter-dropped replace/indel "
              "one-move cloud; per-root unaided baseline arm as the "
              "freeze control",
    "success_threshold": 0.45,
    "runs": runs,
    "poolB_crosses_new_roots": pool_crosses,
    "poolB_total_crosses_incl_exp011": pool_crosses + ([7] if exp011_crossed else []),
    "unaided_crosses": unaided_crosses,
    "replication_verdict": ("REPLICATES" if replicates else
                            "ROOT-LOTTERY"),
}
RESULTS.write_text(json.dumps(summary, indent=2) + "\n")
print("verdict:", summary["replication_verdict"],
      "| poolB crosses:", summary["poolB_total_crosses_incl_exp011"],
      "| unaided crosses:", unaided_crosses)
