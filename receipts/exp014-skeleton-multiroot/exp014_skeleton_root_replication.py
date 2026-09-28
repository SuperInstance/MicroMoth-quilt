"""exp014 — multi-root replication of the SKELETON-SEED doctrine: is the
"only replicated crossing path" itself root-robust?

Doctrine chain under test: exp012 ROOT-LOTTERY (parent_pool crosses
1/4 roots) and exp013 ROOT-LOTTERY (curriculum transplant 1/4) both
conclude "hand-built zero-fitness skeletons are the ONLY replicated
crossing path". BUT every skeleton crossing ever measured ran on
ROOT 7 ONLY: exp006 (n=3, root 7), exp007 (n=2, root 7), exp008
(n=4, root 7). The "replicated" claim for skeletons is replication
across TARGETS, not across ROOTS. This experiment closes that hole
before any more doctrine is built on it.

Design pin BEFORE running: exp005 exact unaided n=3 balance lane
(targets 000/111, mode="balance", n=3, pop 16, gens 12, train 101,
verify 202, shots 512, jitter-dropped replace/indel one-move cloud via
mutate_classed). Fresh roots 3/5/13/17/19/29/31/37 — 7/11/23/42 are
already characterized. Two arms per root:

  S: skeleton seed [["h",0],["cx",0,1]] (exp006 prescription: zero
     fitness at birth, one indel/replace move from correlation),
     parent_pool=False, champion-local cloud.
  P: parent_pool=True, no seed (extends the exp012 rate sample from
     4 roots to 12 for a crossing-rate estimate).

Interpretation pinned BEFORE running (success = held-out balance
>= 0.45, same bar as exp005-exp013):
  S crosses >= 7/8 roots -> SKELETON ROOT-ROBUST: "seed choice beats
    seed fitness" hardens from doctrine to engine law; the exp012/013
    conclusion stands on solid ground.
  S crosses 3-6/8      -> skeleton is a RATE, not a law: doctrine
    rewrites to crossing-rate ordering between mechanisms.
  S crosses <= 2/8     -> SKELETON ROOT-LOTTERY TOO: nothing in this
    engine is root-invariant; every crossing claim carries a measured
    rate or it carries nothing.
  P rate: combined with exp012's [7]/[11,23,42] for an n=12 estimate.

Guard: exp001 default lane must reproduce byte-identical in-harness
before any results are written. Telemetry per arm per root.
"""
import functools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qcell.search import mutate_classed, run_search

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp014.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
NEW_ROOTS = (3, 5, 13, 17, 19, 29, 31, 37)
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))

# --- guard: default lane still reproduces exp001 -------------------------
ctrl_telem = LAB / "experiments" / "exp014.telemetry.control.jsonl"
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
    print("FATAL: exp014 harness changed default behavior; "
          "refusing to write results")
    sys.exit(1)

runs = []
for root in NEW_ROOTS:
    for arm, kw in (("skeleton", dict(seed_genome=SKELETON,
                                      parent_pool=False)),
                    ("pool", dict(seed_genome=None,
                                  parent_pool=True))):
        telem = LAB / "experiments" / \
            f"exp014.telemetry.r{root}.{arm}.jsonl"
        if telem.exists():
            telem.unlink()
        res = run_search(root, generations=GENS, pop=POP, shots=SHOTS,
                         train_seed=TRAIN, verify_seed=VERIFY,
                         telemetry_path=str(telem), targets=TARGETS,
                         n_qubits=N, mode="balance",
                         mutate_fn=mutate_one, **kw)
        champ = res["champion"]
        first_ok = next((r["gen"] for r in res["curve"]
                         if r["verify_p"] >= BAR), None)
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
              f"first_ge_045_gen={first_ok} verify={champ.verify_p:.4f}",
              flush=True)

skel_runs = [r for r in runs if r["arm"] == "skeleton"]
pool_runs = [r for r in runs if r["arm"] == "pool"]
skel_crosses = [r["root_seed"] for r in skel_runs if r["crossed"]]
pool_crosses = [r["root_seed"] for r in pool_runs if r["crossed"]]
n_skel = len(skel_crosses)

if n_skel >= 7:
    verdict = "SKELETON ROOT-ROBUST"
elif n_skel >= 3:
    verdict = "SKELETON IS A RATE"
else:
    verdict = "SKELETON ROOT-LOTTERY TOO"

summary = {
    "experiment": "exp014_skeleton_root_replication",
    "question": "is the skeleton-seed crossing path root-robust, or is "
                "every crossing mechanism in this engine a root-lottery "
                "with different rates?",
    "design": "exp005 exact unaided n=3 balance lane; fresh roots "
              "3/5/13/17/19/29/31/37 (7/11/23/42 already characterized); "
              "S arm = exp006 skeleton seed [h(0),cx(0,1)] champion-local; "
              "P arm = parent_pool unaided (extends exp012 rate sample "
              "to n=12 combined)",
    "success_threshold": BAR,
    "pre_registered_verdicts": {
        ">=7/8": "SKELETON ROOT-ROBUST (engine law)",
        "3-6/8": "SKELETON IS A RATE (doctrine rewrites to rates)",
        "<=2/8": "SKELETON ROOT-LOTTERY TOO (nothing root-invariant)",
    },
    "runs": runs,
    "skeleton_crosses": skel_crosses,
    "skeleton_cross_fraction": f"{n_skel}/{len(skel_runs)}",
    "pool_crosses_this_experiment": pool_crosses,
    "pool_combined_crosses_incl_exp011_exp012": [7] + pool_crosses,
    "verdict": verdict,
}
RESULTS.write_text(json.dumps(summary, indent=2) + "\n")
print("verdict:", verdict,
      "| skeleton crosses:", summary["skeleton_cross_fraction"],
      "| pool crosses (all experiments):",
      summary["pool_combined_crosses_incl_exp011_exp012"])
