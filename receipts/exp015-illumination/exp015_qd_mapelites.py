"""exp015 — Illuminate the Freeze: MAP-Elites quality-diversity archive
over the qcells circuit-search space. Does the frozen unaided n=3
GHZ-balance lane hide signal that single-fitness champion search
cannot see?

Doctrine under test: exp014 pinned "THE FREEZE IS THE LAW; THE CROSSING
IS ALWAYS A RATE" — champion-local unaided search crossed 0/11 configs
while every seeded/reach mechanism crossed at a measurable rate. But
every one of those verdicts came from SINGLE-FITNESS champion search:
one genome owns the population; a child that is interesting but not
better-than-champion is DISCARDED every generation. Nobody has looked
at COVERAGE: what does the fitness landscape look like under
illumination? If the archive holds elites at held-out balance > 0 that
champion search never promoted, the freeze is partly an ELITISM
artifact, not engine law. Edge-watch flagged Intel KernelFoundry's
MAP-Elites + parent->child fitness-delta mutation hints as
technique-transfer candidates; this experiment is the transfer test.

Design pin BEFORE running (anti-laundering):
  Lane: the exact exp005 unaided lane — targets ("000","111"),
    mode="balance", n_qubits=3, train_seed=101, verify_seed=202,
    shots=512, gate budget 6, exp004 jitter-dropped policy
    restrict=("replace","indel"), one-move classed cloud.
  Archive A1 (primary, DRIVES EMISSION): behavior descriptors =
    (verify_balance_bucket x circuit_length). Buckets: 0 | (0,.125] |
    (.125,.25] | (.25,.375] | (.375,.5] | >.5  (6) x length 1..6 (6)
    = 36 cells. Fitness = TRAIN balance only; per-cell elitism on
    train fitness; verify enters ONLY as a descriptor — selection
    never sees the held-out seed (honesty preserved by construction).
  Archive A2 (passive illumination lens): BD = (balance_bucket x
    output_entropy_bucket of the verify-seed counts), 6 x 5 = 30
    cells. Emission never draws from A2; it is a second map of the
    same evaluations.
  Emitter: parents sampled uniformly from A1 occupied cells, one
    mutate_classed move (resample-on-None semantics identical to
    run_search; MutationDeadlock recorded, never worked around).
  Configs x roots 7/11/23 (3-root doctrine):
    (a) unaided     — random 3-gate birth (exp005 birth semantics).
    (b) skeleton    — birth genome [["h",0],["cx",0,1]] (exp006
                      prescription: zero fitness, one move from
                      correlation).
    (c) transplant  — unaided birth + archive-elite-transplant
                      curriculum: every K=4 gens the A1 elite from the
                      LEAST-VISITED occupied cell is cloned into the
                      child stream that gen (guaranteed injection).
  Interpretation pinned BEFORE running (success bar unchanged:
  held-out verify balance >= 0.45):
    Occupied cells with elite verify > 0 in config (a) on >= 1 root
      -> the unaided freeze hides reachable signal that single-
         fitness search discarded: ELITISM-ARTIFACT (partial).
    Occupied >0 cells only in (b)/(c) -> seeding/transplant
      manufactures the signal; the unaided freeze is illumination-
      invariant under the archive map too.
    All 9 runs empty above 0 -> FREEZE IS ILLUMINATION-INVARIANT;
      the engine-law verdict STRENGTHENS (survives a fundamentally
      different selection regime, not just more draws/reach).
    A 2-root crossing in (c) with 0 in (a) counts as curriculum
      signal worth a follow-up lane; per exp012 doctrine a bare
      crossing claim still needs its measured rate.
  Honesty: per-gen archive snapshots (JSONL) for both archives;
    every elite carries provenance (born/skeleton/transplant/evo with
    parent cell + lineage); NO silent lineage merge (pong-quilt
    load-merge P3 lesson); transplant events logged; per-child rows
    record parent->child fitness delta (KernelFoundry hint) and
    cloud-max verify balance per gen (signal-region sampling even
    when the child is not elite).
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
RESULTS = LAB / "experiments" / "exp015.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
ROOTS = (7, 11, 23)
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45
K_TRANSPLANT = 4

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))


# --- evaluation ----------------------------------------------------------
def sim_counts(genome, seed, shots=SHOTS, n_qubits=N):
    random.seed(seed)
    qc = genome_circuit(genome, n_qubits=n_qubits)
    return micromoth.simulate(qc, shots=shots, get="counts")


def evaluate(genome):
    """train balance (fitness) + verify balance + verify-counts entropy.
    Two seeded sims per candidate; entropy rides free on the verify
    counts (same WORLD call the balance descriptor uses)."""
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
    return min(1 + int(b * 8), 5)  # (0,.125]1 (.125,.25]2 (.25,.375]3
                                   # (.375,.5]4 >.5 5


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


BAL_LABELS = ("0", "(0,.125]", "(.125,.25]", "(.25,.375]",
              "(.375,.5]", ">.5")
ENT_LABELS = ("0", "(0,.5]", "(.5,1]", "(1,1.5]", ">1.5")


class Archive:
    """MAP-Elites grid: per-cell elitism on TRAIN fitness only."""

    def __init__(self, name):
        self.name = name
        self.cells = {}      # bd tuple -> elite record
        self.visits = Counter()  # bd -> candidates that landed here

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

    def least_visited_elite(self):
        occ = [bd for bd in self.cells if True]
        if not occ:
            return None
        pick = min(occ, key=lambda bd: (self.visits[bd],
                                        self.cells[bd]["fitness"]))
        return pick, self.cells[pick]


# --- MAP-Elites runner ---------------------------------------------------
def run_mapelites(root, config, telemetry_path):
    rng = random.Random(root)
    a1, a2 = Archive("bal_x_len"), Archive("bal_x_entropy")
    telem = open(telemetry_path, "a", encoding="utf-8")
    transplants = []
    next_lineage = [0]

    def mklineage():
        next_lineage[0] += 1
        return f"r{root}-{config}-{next_lineage[0]}"

    def place(genome, train, verify, ent, provenance, gen):
        rec = {"genome": [list(g) for g in genome], "train": train,
               "verify": verify, "fitness": train,
               "provenance": provenance, "born_gen": gen}
        bd1 = (bal_bucket(verify), len(genome))
        bd2 = (bal_bucket(verify), ent_bucket(ent))
        new1 = a1.try_add(bd1, rec)
        new2 = a2.try_add(bd2, rec)
        return bd1, new2

    # birth
    if config == "skeleton":
        birth_genome = [list(g) for g in SKELETON]
        birth_prov = {"kind": "skeleton-seed", "parent": None,
                      "lineage": mklineage()}
    else:
        birth_genome = [random_gate(rng, N) for _ in range(3)]
        birth_prov = {"kind": "born", "parent": None,
                      "lineage": mklineage()}
    tb, vb, eb = evaluate(birth_genome)
    place(birth_genome, tb, vb, eb, birth_prov, gen=-1)

    deadlock = None
    for gen in range(GENS):
        children = []
        # config (c): archive-elite-transplant curriculum every K gens
        if config == "transplant" and gen > 0 and gen % K_TRANSPLANT == 0:
            pick = a1.least_visited_elite()
            if pick is not None:
                src_bd, src = pick
                clone = [list(g) for g in src["genome"]]
                prov = {"kind": "transplant", "parent": src_bd,
                        "src_lineage": src["provenance"]["lineage"],
                        "src_born_gen": src["born_gen"],
                        "lineage": mklineage()}
                children.append((clone, prov))
                transplants.append({"gen": gen, "src_cell": list(src_bd),
                                    "src_fitness": round(src["fitness"], 4),
                                    "src_verify": round(src["verify"], 4),
                                    "src_lineage": prov["src_lineage"]})
        while len(children) < POP:
            # emitter: uniform over A1 occupied cells, take that cell's
            # elite as the parent (archive-driven genealogy)
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

        new_elites1, new_elites2 = [], []
        max_cloud_verify = 0.0
        deltas = []
        for genome, prov in children:
            tr, vr, en = evaluate(genome)
            max_cloud_verify = max(max_cloud_verify, vr)
            parent_fit = None
            if prov["kind"] == "evo":
                parent_fit = a1.cells[tuple(prov["parent"])]["fitness"]
                deltas.append(round(tr - parent_fit, 4))
            was_new1 = a1.try_add((bal_bucket(vr), len(genome)),
                                  {"genome": [list(g) for g in genome],
                                   "train": tr, "verify": vr, "fitness": tr,
                                   "provenance": prov, "born_gen": gen})
            bd2 = (bal_bucket(vr), ent_bucket(en))
            was_new2 = a2.try_add(bd2,
                                  {"genome": [list(g) for g in genome],
                                   "train": tr, "verify": vr, "fitness": tr,
                                   "provenance": prov, "born_gen": gen})
            if was_new1:
                new_elites1.append({"cell": [bal_bucket(vr), len(genome)],
                                    "train": round(tr, 4),
                                    "verify": round(vr, 4),
                                    "provenance": prov})
            if was_new2:
                new_elites2.append({"cell": [bal_bucket(vr), ent_bucket(en)],
                                    "train": round(tr, 4),
                                    "verify": round(vr, 4)})
        row = {"gen": gen,
               "a1_coverage": len(a1.cells),
               "a2_coverage": len(a2.cells),
               "a1_coverage_gt0": len(a1.occupied_gt0()),
               "a2_coverage_gt0": len(a2.occupied_gt0()),
               "a1_max_elite_verify": round(
                   max((r["verify"] for r in a1.cells.values()), default=0.0), 4),
               "cloud_max_verify": round(max_cloud_verify, 4),
               "new_elites_a1": new_elites1,
               "new_elites_a2_count": len(new_elites2),
               "fitness_deltas": deltas,
               "a1": a1.snapshot(), "a2": a2.snapshot()}
        telem.write(json.dumps(row, sort_keys=True) + "\n")

    telem.close()
    best_elite = max(a1.cells.values(),
                     key=lambda r: r["verify"], default=None)
    first_cross = None
    # crossing read off per-gen snapshots is expensive; scan cells' born
    # gens for the first elite that beat the bar on the held-out seed
    for bd, r in a1.cells.items():
        if r["verify"] >= BAR:
            g = r["born_gen"]
            if first_cross is None or (g >= 0 and g < first_cross):
                first_cross = g
    for bd, r in a2.cells.items():
        if r["verify"] >= BAR:
            g = r["born_gen"]
            if first_cross is None or (g >= 0 and g < first_cross):
                first_cross = g
    return {
        "root_seed": root, "config": config,
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
        "transplant_events": transplants,
        "a1_final": a1.snapshot(), "a2_final": a2.snapshot(),
    }


# --- guard: default lane still reproduces exp001 -------------------------
ctrl_telem = LAB / "experiments" / "exp015.telemetry.control.jsonl"
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
    print("FATAL: exp015 harness changed default behavior; "
          "refusing to write results")
    sys.exit(1)

runs = []
for root in ROOTS:
    for config in ("unaided", "skeleton", "transplant"):
        telem = LAB / "experiments" \
            / f"exp015.telemetry.r{root}.{config}.jsonl"
        if telem.exists():
            telem.unlink()
        res = run_mapelites(root, config, str(telem))
        runs.append(res)
        print(f"r{root} {config}: cov={res['a1_final_coverage']}/36 "
              f"gt0={res['a1_coverage_gt0']} "
              f"maxV={res['max_elite_verify']} "
              f"crossed={res['crossed']} "
              f"deadlock={res['deadlock'] is not None}")

unaided_gt0 = [r for r in runs
               if r["config"] == "unaided" and r["a1_coverage_gt0"] > 0]
verdict = ("ELITISM-ARTIFACT (partial): unaided archive holds verify>0 "
           "cells champion search discarded"
           if unaided_gt0 else
           "FREEZE IS ILLUMINATION-INVARIANT: zero archive cells above "
           "balance 0 in all 9 runs under per-cell elitism")

summary = {
    "experiment": "exp015_qd_mapelites",
    "question": "does MAP-Elites coverage over the exp005 lane reveal "
                "occupied cells at held-out balance > 0 that "
                "single-fitness champion search never promoted (freeze "
                "= elitism artifact), or is coverage empty above 0 "
                "(freeze = illumination-invariant engine law)?",
    "design": "A1 BD=(verify_balance_bucket x circuit_length) 36 cells, "
              "A2 BD=(balance_bucket x verify-counts entropy) 30 cells; "
              "fitness=train balance only (verify is descriptor-only, "
              "selection never sees the held-out seed); emitter=one-"
              "move mutate_classed cloud off uniform A1 cell parents; "
              "configs (a) unaided birth (b) skeleton birth (c) "
              "unaided + least-visited-cell elite transplant every 4 "
              "gens; roots 7/11/23; exact exp005 lane (targets "
              "000/111, balance, n=3, train101/verify202/shots512, "
              "budget 6, restrict=('replace','indel')); 12 gens x pop16",
    "success_threshold_verify_balance": BAR,
    "pre_run_pin": "occupied verify>0 cells in config (a) on >=1 root "
                   "= ELITISM-ARTIFACT; >0 cells only in (b)/(c) = "
                   "signal manufactured by seeding; all 9 runs empty "
                   "above 0 = FREEZE IS ILLUMINATION-INVARIANT",
    "guard_exp001_reproduced": control_ok,
    "runs": runs,
    "verdict": verdict,
    "unaided_gt0_runs": [r["root_seed"] for r in unaided_gt0],
    "crossing_table": {
        f"r{r['root_seed']}.{r['config']}": {
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
