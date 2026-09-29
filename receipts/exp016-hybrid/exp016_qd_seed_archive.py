"""exp016 — Hybrid: skeleton seed + MAP-Elites archive, multi-root rate
replication. Does the archive (exp015 regime) change the skeleton-seed
CROSSING RATE that exp014 pinned at 4/8 under champion-local search?

Doctrine chain under test:
  exp005  the unaided n=3 GHZ-balance lane FREEZES (champion 0.0).
  exp006  a skeleton seed [h(0),cx(0,1)] crosses on root 7 (0.4824).
  exp011  non-champion-parent cloud crosses once on root 7 — genealogy
          was a favorable draw, seeding stays the replicated class.
  exp012  ROOT-LOTTERY: the unaided crossing does not replicate; any
          crossing claim needs N/M roots + measured rate.
  exp013  curriculum transplant traps at the partial plateau
          (~0.2422) — a wrong-scale ladder, not a crossing class.
  exp014  SKELETON IS A RATE: champion-local skeleton crosses 4/8
          fresh roots {3,13,17,19} of {3,5,13,17,19,29,31,37}.
  exp015  ELITISM-ARTIFACT (partial): the MAP-Elites archive holds
          verify>0 elites (max 0.248) champion search discarded, but
          the 0.45 crossing stayed skeleton-only 3/3 on roots 7/11/23
          under the archive regime too — crossing is selection-
          regime-invariant on those roots.

Open question THIS experiment seals: exp015 compared archive-vs-champion
only on the three well-characterized roots (7/11/23), where champion-
local skeleton was already 3/3 — no rate difference was measurable.
The discriminating comparison is exp014's fresh-root panel, where
champion-local skeleton FAILED on half the roots. If the archive's
retained partial-plateau signal is load-bearing for the crossing, the
hybrid should cross roots champion-local missed (29/31/37 class). If
the crossing is birth-seeding alone, the hybrid reproduces the same
4/8 (or a root-disjoint draw, which per exp012 doctrine is a
rate-class read, not a mechanism claim).

Design pin BEFORE running (anti-laundering):
  Lane: the exact exp005 unaided lane — targets ("000","111"),
    mode="balance", n_qubits=3, train_seed=101, verify_seed=202,
    shots=512, gate budget 6, exp004 jitter-dropped policy
    restrict=("replace","indel"), one-move classed cloud.
  Config: hybrid ONLY — birth genome = exp006 skeleton
    [["h",0],["cx",0,1]] (zero fitness, one move from correlation),
    then exp015's exact archive regime: A1 BD=(verify_balance_bucket x
    circuit_length) 36 cells drives emission (uniform occupied-cell
    parents, one mutate_classed move), A2 BD=(balance_bucket x
    verify-counts entropy) passive lens; fitness = TRAIN balance only;
    verify descriptor-only (selection never sees held-out seed 202).
    NO transplant curriculum (exp015 pinned it is not a crossing
    class; this experiment isolates birth-seed x regime).
  Roots: exp014's EXACT fresh panel 3/5/13/17/19/29/31/37 (7/11/23/42
    already characterized; same-root comparison is the whole point).
    12 gens x pop 16, identical to exp015's archive runs.
  Comparator (named before running): exp014 champion-local skeleton
    crossed {3,13,17,19} = 4/8 (receipt commit 793a771, PR #19
    Casey-gated at seal time — comparator data embedded here with
    provenance, no pin depends on exp014 files being on main).
  Success bar unchanged: held-out verify balance >= 0.45.

Interpretation pinned BEFORE running:
  hybrid crosses >=7/8 -> ARCHIVE AMPLIFIES SEEDING: coverage retains
    signal champion-local discarded and the crossing rate moves up.
    Elitism-artifact is load-bearing; doctrine gains an archive
    clause (crossing rate is regime-sensitive upward).
  hybrid crosses 4-6/8 -> ARCHIVE NEUTRAL: SKELETON-IS-A-RATE stands
    unchanged; the crossing rides the birth seed alone, the archive
    neither helps nor hurts the rate.
  hybrid crosses <=2/8 -> CHAMPION LOCALITY IS THE LAW: the archive
    actively DILUTES the seed signal (parents sampled from partial-
    plateau cells pull children off the crossing route); single-
    fitness champion locality is load-bearing for seeded crossing.
    A root-disjoint draw (e.g. {5,29} vs {3,13,17,19}) with counts in
    the 3-5 band reads as NEUTRAL per exp012 ROOT-LOTTERY doctrine,
    reported as N/M, never as mechanism victory.

  Per-root agreement table vs exp014 reported either way; root
  difficulty classes from exp014 (easy 13/19; mechanism-specific
  3/17 skeleton-only, 5 pool-only; hard 29/31/37) named per root.

  Honesty: per-gen archive snapshots (JSONL) for both archives; every
  elite carries provenance; per-child parent->child fitness delta
  rows; cloud-max verify per gen (partial-plateau signal visible
  in-band); NO silent lineage merge.
  Guard: exp001 default lane must reproduce byte-identical in-harness
    before any results are written.
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
from qcell.search import (genome_circuit, mutate_classed, random_gate,
                          run_search, MutationDeadlock)

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp016.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
# exp014's EXACT fresh panel — same-root comparison is the design
ROOTS = (3, 5, 13, 17, 19, 29, 31, 37)
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45

# exp014 champion-local comparator (receipt commit 793a771, PR #19
# Casey-gated at seal time — named provenance, embedded not assumed)
EXP014_COMPARATOR = {
    "source": "exp014-skeleton-multiroot receipt, commit 793a771 "
              "(PR #19 Casey-gated, not merged at seal time)",
    "champion_local_skeleton_crosses": [3, 13, 17, 19],
    "champion_local_skeleton_fraction": "4/8",
}

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))


# --- evaluation (identical to exp015) ------------------------------------
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
    """MAP-Elites grid: per-cell elitism on TRAIN fitness only
    (exp015 semantics, unchanged)."""

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


# --- hybrid runner --------------------------------------------------------
def run_hybrid(root, telemetry_path):
    rng = random.Random(root)
    a1, a2 = Archive("bal_x_len"), Archive("bal_x_entropy")
    telem = open(telemetry_path, "a", encoding="utf-8")
    next_lineage = [0]

    def mklineage():
        next_lineage[0] += 1
        return f"r{root}-hybrid-{next_lineage[0]}"

    # birth: exp006 skeleton seed (hybrid = birth-seeding x archive)
    birth_genome = [list(g) for g in SKELETON]
    birth_prov = {"kind": "skeleton-seed", "parent": None,
                  "lineage": mklineage()}
    tb, vb, eb = evaluate(birth_genome)
    for arch, bd in ((a1, (bal_bucket(vb), len(birth_genome))),
                     (a2, (bal_bucket(vb), ent_bucket(eb)))):
        arch.try_add(bd, {"genome": [list(g) for g in birth_genome],
                          "train": tb, "verify": vb, "fitness": tb,
                          "provenance": birth_prov, "born_gen": -1})

    deadlock = None
    for gen in range(GENS):
        children = []
        while len(children) < POP:
            occ = list(a1.cells.keys())
            parent_bd = rng.choice(occ)
            parent = a1.cells[parent_bd]
            genome = None
            for _ in range(10000):
                cand = mutate_one(parent["genome"], rng, 6, n_qubits=N)
                if cand is not None:
                    genome = cand
                    break
            if genome is None:
                deadlock = (gen, list(parent["genome"]))
                break
            prov = {"kind": "evo", "parent": list(parent_bd),
                    "parent_lineage": parent["provenance"]["lineage"],
                    "lineage": mklineage()}
            children.append((genome, prov))
        if deadlock:
            break

        new_elites1 = []
        max_cloud_verify = 0.0
        deltas = []
        for genome, prov in children:
            tr, vr, en = evaluate(genome)
            max_cloud_verify = max(max_cloud_verify, vr)
            if prov["kind"] == "evo":
                parent_fit = a1.cells[tuple(prov["parent"])]["fitness"]
                deltas.append(round(tr - parent_fit, 4))
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
                                    "provenance": prov})
        telem.write(json.dumps({
            "gen": gen,
            "a1_coverage": len(a1.cells),
            "a2_coverage": len(a2.cells),
            "a1_coverage_gt0": len(a1.occupied_gt0()),
            "a2_coverage_gt0": len(a2.occupied_gt0()),
            "a1_max_elite_verify": round(
                max((r["verify"] for r in a1.cells.values()),
                    default=0.0), 4),
            "cloud_max_verify": round(max_cloud_verify, 4),
            "new_elites_a1": new_elites1,
            "fitness_deltas": deltas,
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
    return {
        "root_seed": root, "config": "hybrid",
        "a1_final_coverage": len(a1.cells),
        "a2_final_coverage": len(a2.cells),
        "a1_coverage_gt0": len(a1.occupied_gt0()),
        "a2_coverage_gt0": len(a2.occupied_gt0()),
        "a1_cells_gt0": [list(bd) for bd in sorted(a1.occupied_gt0())],
        "a2_cells_gt0": [list(bd) for bd in sorted(a2.occupied_gt0())],
        "max_elite_verify": round(best_elite["verify"], 4) if best_elite else 0.0,
        "max_elite_genome": best_elite["genome"] if best_elite else None,
        "crossed": first_cross is not None,
        "first_ge_045_gen": first_cross,
        "deadlock": deadlock,
        "a1_final": a1.snapshot(), "a2_final": a2.snapshot(),
    }


# --- guard: default lane still reproduces exp001 -------------------------
ctrl_telem = LAB / "experiments" / "exp016.telemetry.control.jsonl"
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
    print("FATAL: exp016 harness changed default behavior; "
          "refusing to write results")
    sys.exit(1)

runs = []
for root in ROOTS:
    telem = LAB / "experiments" / f"exp016.telemetry.r{root}.hybrid.jsonl"
    if telem.exists():
        telem.unlink()
    res = run_hybrid(root, str(telem))
    runs.append(res)
    print(f"r{root} hybrid: cov={res['a1_final_coverage']}/36 "
          f"gt0={res['a1_coverage_gt0']} "
          f"maxV={res['max_elite_verify']} "
          f"crossed={res['crossed']} gen={res['first_ge_045_gen']} "
          f"deadlock={res['deadlock'] is not None}")

crosses = sorted(r["root_seed"] for r in runs if r["crossed"])
n_cross = len(crosses)
champ_crosses = set(EXP014_COMPARATOR["champion_local_skeleton_crosses"])
agree = sorted(set(crosses) & champ_crosses)
hybrid_only = sorted(set(crosses) - champ_crosses)
champ_only = sorted(champ_crosses - set(crosses))

if n_cross >= 7:
    verdict = ("ARCHIVE AMPLIFIES SEEDING: hybrid crosses "
               f"{n_cross}/8 roots under the archive regime vs 4/8 "
               "champion-local; the elitism-artifact signal exp015 "
               "found is load-bearing for the crossing rate")
elif n_cross >= 3:
    verdict = (f"ARCHIVE NEUTRAL: hybrid crosses {n_cross}/8 "
               f"({crosses}) vs champion-local 4/8 "
               f"({sorted(champ_crosses)}); agreement {agree}, "
               f"hybrid-only {hybrid_only or 'none'}, "
               f"champion-only {champ_only or 'none'} — "
               "SKELETON-IS-A-RATE stands, the crossing rides the "
               "birth seed alone (exp012 ROOT-LOTTERY doctrine: N/M, "
               "never mechanism victory)")
else:
    verdict = (f"CHAMPION LOCALITY IS THE LAW: hybrid crosses only "
               f"{n_cross}/8 ({crosses or 'none'}) vs champion-local "
               "4/8 — uniform archive parents dilute the seed signal; "
               "single-fitness champion locality is load-bearing for "
               "seeded crossing")

summary = {
    "experiment": "exp016_qd_seed_archive_hybrid",
    "question": "does the MAP-Elites archive regime (exp015) change the "
                "skeleton-seed crossing rate that exp014 pinned at 4/8 "
                "under champion-local search on the same 8 fresh roots "
                "(3/5/13/17/19/29/31/37)?",
    "design": "hybrid ONLY: exp006 skeleton birth [h(0),cx(0,1)] + "
              "exp015's exact archive regime (A1 BD=verify_balance_"
              "bucket x circuit_length 36 cells drives emission, A2 "
              "balance x verify-counts entropy passive; fitness=train "
              "balance only, verify descriptor-only; uniform occupied-"
              "cell parents, one mutate_classed move); NO transplant; "
              "roots = exp014's exact fresh panel 3/5/13/17/19/29/31/37; "
              "12 gens x pop 16; exact exp005 lane (targets 000/111, "
              "balance, n=3, train101/verify202/shots512, budget 6, "
              "restrict=('replace','indel'))",
    "success_threshold_verify_balance": BAR,
    "pre_run_pin": ">=7/8 cross = ARCHIVE AMPLIFIES SEEDING (coverage "
                   "retains discarded signal, rate moves up); 3-6/8 = "
                   "ARCHIVE NEUTRAL (SKELETON-IS-A-RATE stands, root-"
                   "disjoint draws read as N/M per ROOT-LOTTERY); "
                   "<=2/8 = CHAMPION LOCALITY IS THE LAW (archive "
                   "dilutes the seed signal)",
    "exp014_comparator": EXP014_COMPARATOR,
    "guard_exp001_reproduced": control_ok,
    "runs": runs,
    "hybrid_crosses": crosses,
    "hybrid_cross_fraction": f"{n_cross}/8",
    "root_agreement_with_exp014": {
        "both_cross": agree,
        "hybrid_only": hybrid_only,
        "champion_local_only": champ_only,
    },
    "verdict": verdict,
    "crossing_table": {
        f"r{r['root_seed']}.hybrid": {
            "crossed": r["crossed"],
            "first_ge_045_gen": r["first_ge_045_gen"],
            "max_elite_verify": r["max_elite_verify"],
            "a1_coverage_gt0": r["a1_coverage_gt0"],
            "deadlock": r["deadlock"],
        } for r in runs
    },
}
RESULTS.write_text(json.dumps(summary, indent=2) + "\n")
print("verdict:", verdict)
