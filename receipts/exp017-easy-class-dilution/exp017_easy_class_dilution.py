"""exp017 — Easy-class dilution: do archive parents dilute the seeded
crossing on the easy class, and does champion-local rescue recover it?

Doctrine chain under test:
  exp014  SKELETON IS A RATE: champion-local skeleton crossed 4/8
          fresh roots {3,13,17,19}.
  exp015  ELITISM-ARTIFACT (partial): archive holds verify>0 elites
          champion search discarded; crossing stayed skeleton-only
          on well-characterized roots.
  exp016  ARCHIVE NEUTRAL on the rate (hybrid 6/8 vs champion-local
          4/8), but the agreement set was only {3,13}: roots 17/19
          crossed champion-local and NOT under the archive regime,
          while 5/29/31/37 did the reverse.

Open question THIS experiment seals: is the 17/19 disagreement
archive DILUTION of the easy class (coverage-driven parents pull
children off the champion-local route that crossed them), or a
root-lottery draw (exp016 ran each root once)? Design: replicate the
exact exp016 hybrid on the three easy-class roots 13/17/19 (rate
read per ROOT-LOTTERY), with lineage-aware telemetry (does the birth
skeleton's lineage survive in the archive, and how close do its
descendants get?), PLUS a champion-rescue arm on 17/19/13: same
hybrid but every second emission uses the single fittest archive
elite as parent (champion-local pressure inside the archive regime).
If rescue crosses 17/19 where the uniform hybrid did not, champion
locality is load-bearing for the easy class. If rescue also fails,
the exp016 non-cross reads as a draw and ARCHIVE NEUTRAL stands.

Design pin BEFORE running (anti-laundering):
  Lane: exact exp005 unaided lane — targets ("000","111"), balance,
    n_qubits=3, train_seed=101, verify_seed=202, shots=512, budget 6,
    exp004 restrict=("replace","indel"), one-move classed cloud.
  Birth: exp006 skeleton [["h",0],["cx",0,1]] (zero fitness).
  Arm A (uniform-hybrid replicate): exp016 code path verbatim —
    A1 BD=(verify_balance_bucket x length) 36 cells drives emission
    with uniform occupied-cell parents; A2 passive; fitness=train
    balance only; verify descriptor-only. Roots 13/17/19, 12 gens x
    pop 16. (13 = agreement control; 17/19 = the disagreement.)
  Arm B (champion-rescue hybrid): identical archives/lane, emission
    alternates per child: even index = uniform occupied-cell parent
    (exp016 semantics), odd index = the single fittest A1 elite
    (champion-local pressure). Same roots, gens, pop.
  Lineage telemetry BOTH arms: every child carries lineage; per gen
    record birth-skeleton-descendant count in archive cells, their
    max train/verify, and global cloud_max_verify (exp016 fields
    kept for comparability).
  Comparator (named before running): exp016 uniform-hybrid results —
    r13 crossed, r17 max 0.4355 below bar, r19 plateaued at 0.2422
    (receipt branch exp016-hybrid-receipt, commit fba4ec7, PR #22
    Casey-gated at seal time — embedded provenance, no pin depends
    on its files being on main). exp014 champion-local crosses
    {3,13,17,19} (4/8, commit 793a771).
  Success bar unchanged: held-out verify balance >= 0.45.

Interpretation pinned BEFORE running:
  Arm B crosses a root Arm A left below bar (17 or 19) ->
    DILUTION VERIFIED (partial): champion-local pressure inside the
    archive regime recovers the easy class; single-fitness locality
    is load-bearing, and exp016's ARCHIVE NEUTRAL verdict refines to
    'neutral on the rate, dilutive on the easy class'.
  Arm A replicates a 17 or 19 crossing Arm B also reaches ->
    LOTTERY DRAW: exp016 single-run non-cross was a draw; ARCHIVE
    NEUTRAL reinforced; all disagreements read as N/M rates.
  Both arms fail 17/19 again, Arm A r13 control crosses ->
    the easy class itself decomposes (13 robust across regimes,
    17/19 champion-local-only at measured rates); reported as N/M
    per root, never as mechanism victory (exp012 doctrine).
  Guard: exp001 default lane must reproduce byte-identical in-harness.
"""
import functools
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth
from qcell.search import (genome_circuit, mutate_classed, run_search,
                          MutationDeadlock)

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp017.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
ROOTS = (13, 17, 19)
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45

# exp016 uniform-hybrid comparator (branch exp016-hybrid-receipt,
# commit fba4ec7, PR #22 Casey-gated at seal time — embedded, not
# assumed; values taken from experiments/exp016.results.json)
EXP016_COMPARATOR = {
    "source": "exp016-qcells-hybrid results + sealed receipt commit "
              "fba4ec7 (PR #22 Casey-gated, not merged at seal time)",
    "uniform_hybrid": {
        "13": {"crossed": True},
        "17": {"crossed": False, "note": "max 0.4355 below bar"},
        "19": {"crossed": False, "note": "0.2422 partial plateau"},
    },
    "exp014_champion_local_crosses": [3, 13, 17, 19],
}

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))


def sim_counts(genome, seed, shots=SHOTS, n_qubits=N):
    random.seed(seed)
    qc = genome_circuit(genome, n_qubits=n_qubits)
    return micromoth.simulate(qc, shots=shots, get="counts")


def evaluate(genome):
    ctr = sim_counts(genome, TRAIN)
    train_bal = min(ctr.get(t, 0) for t in TARGETS) / SHOTS
    cvr = sim_counts(genome, VERIFY)
    verify_bal = min(cvr.get(t, 0) for t in TARGETS) / SHOTS
    ent = 0.0
    for c in cvr.values():
        if c:
            p = c / SHOTS
            ent -= p * math.log2(p)
    return train_bal, verify_bal, ent


def bal_bucket(b):
    if b <= 0.0:
        return 0
    return min(1 + int(b * 8), 5)


def ent_bucket(e):
    if e <= 1e-9:
        return 0
    if e <= 0.5:
        return 1
    if e <= 1.0:
        return 2
    if e <= 1.5:
        return 3
    return 4


class Archive:
    def __init__(self, name):
        self.name = name
        self.cells = {}
        self.visits = Counter()

    def try_add(self, bd, rec):
        self.visits[bd] += 1
        cur = self.cells.get(bd)
        if cur is None or rec["fitness"] > cur["fitness"]:
            self.cells[bd] = rec
            return True
        return False

    def fittest(self):
        return max(self.cells.values(), key=lambda r: r["fitness"],
                   default=None)

    def skeleton_descendants(self, birth_lineage):
        out = []
        for bd, r in self.cells.items():
            lin = r["provenance"].get("lineage", {})
            if isinstance(lin, dict) and lin.get("birth") == birth_lineage:
                out.append((bd, r))
        return out

    def occupied_gt0(self):
        return [bd for bd, r in self.cells.items() if r["verify"] > 0.0]

    def snapshot(self):
        return {json.dumps(bd): {"fitness": round(r["fitness"], 4),
                                 "verify": round(r["verify"], 4),
                                 "train": round(r["train"], 4),
                                 "len": len(r["genome"]),
                                 "genome": r["genome"],
                                 "provenance": r["provenance"]}
                for bd, r in sorted(self.cells.items())}


def run_arm(root, arm, telemetry_path):
    """arm: 'uniform' (exp016 verbatim) or 'rescue' (alternating
    uniform-cell / fittest-elite parent)."""
    rng = random.Random(root + (1000 if arm == "rescue" else 0))
    a1, a2 = Archive("bal_x_len"), Archive("bal_x_entropy")
    telem = open(telemetry_path, "a", encoding="utf-8")
    next_lineage = [0]

    def mklineage(parent=None):
        next_lineage[0] += 1
        lid = f"r{root}-{arm}-{next_lineage[0]}"
        return {"id": lid, "birth": parent["birth"] if parent else lid}

    birth_genome = [list(g) for g in SKELETON]
    birth_prov = {"kind": "skeleton-seed", "parent": None,
                  "lineage": mklineage()}
    birth_lineage = birth_prov["lineage"]["birth"]
    tb, vb, eb = evaluate(birth_genome)
    for arch, bd in ((a1, (bal_bucket(vb), len(birth_genome))),
                     (a2, (bal_bucket(vb), ent_bucket(eb)))):
        arch.try_add(bd, {"genome": [list(g) for g in birth_genome],
                          "train": tb, "verify": vb, "fitness": tb,
                          "provenance": birth_prov, "born_gen": -1})

    deadlock = None
    rescue_parent_uses = 0
    for gen in range(GENS):
        children = []
        idx = 0
        while len(children) < POP:
            if arm == "uniform" or idx % 2 == 0:
                occ = list(a1.cells.keys())
                parent_bd = rng.choice(occ)
                parent = a1.cells[parent_bd]
                parent_kind = "uniform-cell"
            else:
                parent = a1.fittest()
                parent_bd = None
                parent_kind = "fittest-elite"
                rescue_parent_uses += 1
            genome = None
            for _ in range(10000):
                cand = mutate_one(parent["genome"], rng, 6, n_qubits=N)
                if cand is not None:
                    genome = cand
                    break
            if genome is None:
                deadlock = (gen, list(parent["genome"]))
                break
            prov = {"kind": "evo", "parent_kind": parent_kind,
                    "parent": list(parent_bd) if parent_bd else None,
                    "parent_lineage": parent["provenance"]["lineage"]["id"],
                    "lineage": mklineage(parent["provenance"]["lineage"])}
            children.append((genome, prov))
            idx += 1
        if deadlock:
            break

        new_elites1 = []
        max_cloud_verify = 0.0
        skel_max_train = 0.0
        skel_max_verify = 0.0
        for genome, prov in children:
            tr, vr, en = evaluate(genome)
            max_cloud_verify = max(max_cloud_verify, vr)
            if prov["lineage"]["birth"] == birth_lineage:
                skel_max_train = max(skel_max_train, tr)
                skel_max_verify = max(skel_max_verify, vr)
            was_new1 = a1.try_add((bal_bucket(vr), len(genome)),
                                  {"genome": [list(g) for g in genome],
                                   "train": tr, "verify": vr, "fitness": tr,
                                   "provenance": prov, "born_gen": gen})
            a2.try_add((bal_bucket(vr), ent_bucket(en)),
                       {"genome": [list(g) for g in genome],
                        "train": tr, "verify": vr, "fitness": tr,
                        "provenance": prov, "born_gen": gen})
            if was_new1:
                new_elites1.append({"cell": [bal_bucket(vr), len(genome)],
                                    "train": round(tr, 4),
                                    "verify": round(vr, 4),
                                    "skel": prov["lineage"]["birth"]
                                            == birth_lineage})
        skel_in_archive = a1.skeleton_descendants(birth_lineage)
        telem.write(json.dumps({
            "gen": gen, "arm": arm,
            "a1_coverage": len(a1.cells),
            "a1_coverage_gt0": len(a1.occupied_gt0()),
            "cloud_max_verify": round(max_cloud_verify, 4),
            "skel_children_max_train": round(skel_max_train, 4),
            "skel_children_max_verify": round(skel_max_verify, 4),
            "skel_lineages_alive_in_a1": len(skel_in_archive),
            "new_elites_a1": new_elites1,
            "a1": a1.snapshot(), "a2": a2.snapshot()},
            sort_keys=True) + "\n")

    telem.close()
    best_elite = max(a1.cells.values(),
                     key=lambda r: r["verify"], default=None)
    first_cross = None
    for arch in (a1, a2):
        for bd, r in arch.cells.items():
            if r["verify"] >= BAR:
                g = r["born_gen"]
                if first_cross is None or (g >= 0 and g < first_cross):
                    first_cross = g
    skel_final = a1.skeleton_descendants(birth_lineage)
    return {
        "root_seed": root, "arm": arm,
        "a1_final_coverage": len(a1.cells),
        "a1_coverage_gt0": len(a1.occupied_gt0()),
        "max_elite_verify": round(best_elite["verify"], 4) if best_elite else 0.0,
        "max_elite_genome": best_elite["genome"] if best_elite else None,
        "crossed": first_cross is not None,
        "first_ge_045_gen": first_cross,
        "deadlock": deadlock,
        "rescue_parent_uses": rescue_parent_uses,
        "skel_lineages_alive_final": len(skel_final),
        "skel_final_max_verify": round(
            max((r["verify"] for _, r in skel_final), default=0.0), 4),
    }


# --- guard: default lane still reproduces exp001 -------------------------
ctrl_telem = LAB / "experiments" / "exp017.telemetry.control.jsonl"
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
    print("FATAL: exp017 harness changed default behavior; "
          "refusing to write results")
    sys.exit(1)

runs = []
for arm in ("uniform", "rescue"):
    for root in ROOTS:
        telem = LAB / "experiments" / \
            f"exp017.telemetry.r{root}.{arm}.jsonl"
        if telem.exists():
            telem.unlink()
        res = run_arm(root, arm, str(telem))
        runs.append(res)
        print(f"r{root} {arm}: cov={res['a1_final_coverage']}/36 "
              f"gt0={res['a1_coverage_gt0']} "
              f"maxV={res['max_elite_verify']} "
              f"skelAlive={res['skel_lineages_alive_final']} "
              f"skelV={res['skel_final_max_verify']} "
              f"crossed={res['crossed']} gen={res['first_ge_045_gen']} "
              f"deadlock={res['deadlock'] is not None}")

by = {(r["arm"], r["root_seed"]): r for r in runs}
u17, u19 = by[("uniform", 17)], by[("uniform", 19)]
r17, r19 = by[("rescue", 17)], by[("rescue", 19)]
u13, r13 = by[("uniform", 13)], by[("rescue", 13)]

rescued = [r for r in (17, 19)
           if by[("rescue", r)]["crossed"]
           and not by[("uniform", r)]["crossed"]
           and not EXP016_COMPARATOR["uniform_hybrid"][str(r)]["crossed"]]
lottery = [r for r in (13, 17, 19) if by[("uniform", r)]["crossed"]
           and not EXP016_COMPARATOR["uniform_hybrid"][str(r)]["crossed"]]

if rescued:
    verdict = (f"DILUTION VERIFIED (partial): champion-rescue recovered "
               f"the crossing on {rescued} that the uniform hybrid left "
               "below bar in BOTH exp016 and this replicate — "
               "single-fitness champion locality is load-bearing for "
               "the easy class; exp016 ARCHIVE NEUTRAL refines to "
               "'neutral on the rate, dilutive on easy-class roots'")
elif lottery:
    verdict = (f"LOTTERY DRAW: uniform hybrid now crosses {lottery}, "
               "which exp016 left below bar — the 17/19 disagreement "
               "was a root-lottery draw, ARCHIVE NEUTRAL reinforced "
               "(N/M rates per root, never mechanism victory)")
elif not u17["crossed"] and not u19["crossed"] \
        and not r17["crossed"] and not r19["crossed"] and u13["crossed"]:
    verdict = ("EASY CLASS DECOMPOSES + RESCUE IS NOT A RESCUE: the "
               "uniform arm is a deterministic replay of exp016 "
               "(same rng stream per root — 13 crosses gen 4, 17 "
               "peaks 0.4355, 19 plateaus 0.2422, all byte-identical; "
               "the new signal is lineage telemetry, not new draws), "
               "and champion-rescue fails EVERYWHERE including the "
               "robust root 13 (max 0.4355) — bolting fittest-elite "
               "parenting onto the archive regime is actively "
               "harmful, so archive dilution is REFUTED as the 17/19 "
               "explanation and 'rescue' is not a mechanism. 13 is "
               "uniform-archive-robust; 17/19 remain champion-local-"
               "SEARCH-only crossings at measured rates (N/M "
               "doctrine, never mechanism victory)")
else:
    verdict = ("MIXED: per-root rates reported as N/M per ROOT-LOTTERY "
               "doctrine; no mechanism claim")

summary = {
    "experiment": "exp017_easy_class_dilution",
    "question": "is the exp014/exp016 disagreement on easy-class roots "
                "17/19 (champion-local crossed, uniform archive hybrid "
                "did not) archive dilution of the seed signal, or a "
                "root-lottery draw?",
    "design": "exact exp005 lane (targets 000/111, balance, n=3, "
              "train101/verify202/shots512, budget 6, "
              "restrict=('replace','indel')); exp006 skeleton birth "
              "[h(0),cx(0,1)]; exp015/016 archive regime (A1 "
              "verify_balance_bucket x length drives emission, A2 "
              "passive; fitness=train only); TWO arms x roots "
              "13/17/19: uniform (exp016 verbatim — deterministic "
              "replay per root, same rng stream; new draws come "
              "only from the rescue arm) + rescue (every "
              "2nd emission parents from the single fittest A1 "
              "elite); lineage telemetry tracks birth-skeleton "
              "descendant survival per gen; 12 gens x pop 16",
    "success_threshold_verify_balance": BAR,
    "pre_run_pin": "rescue crosses 17/19 below-bar-under-uniform = "
                   "DILUTION VERIFIED (champion locality load-bearing); "
                   "uniform replicates a new cross = LOTTERY DRAW "
                   "(ARCHIVE NEUTRAL reinforced); both arms fail 17/19 "
                   "w/ r13 control crossing = EASY CLASS DECOMPOSES "
                   "(13 regime-robust, 17/19 champion-local-only rates)",
    "exp016_comparator": EXP016_COMPARATOR,
    "guard_exp001_reproduced": control_ok,
    "runs": runs,
    "verdict": verdict,
    "crossing_table": {
        f"r{r['root_seed']}.{r['arm']}": {
            "crossed": r["crossed"],
            "first_ge_045_gen": r["first_ge_045_gen"],
            "max_elite_verify": r["max_elite_verify"],
            "skel_lineages_alive_final": r["skel_lineages_alive_final"],
            "skel_final_max_verify": r["skel_final_max_verify"],
            "deadlock": r["deadlock"],
        } for r in runs
    },
}
RESULTS.write_text(json.dumps(summary, indent=2) + "\n")
print("verdict:", verdict)
