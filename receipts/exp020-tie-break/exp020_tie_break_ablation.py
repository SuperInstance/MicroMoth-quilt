"""exp020 — Tie-break ablation: is tie-band diversity ALONE sufficient
for the hard-root crossing?

Doctrine chain under test:
  exp014  SKELETON IS A RATE: champion-local skeleton (incumbent kept
          on train ties, max()-first-wins) crosses 4/8 fresh roots
          {3,13,17,19}; hard class {29,31,37} 0/3.
  exp016  skeleton+archive HYBRID crossed 6/8 incl. all three hard
          roots — ARCHIVE NEUTRAL band top edge; archive converts the
          hard class.
  exp018  FITNESS DESERT AT THE BIRTH CLOUD on 29/31/37: freeze is
          upstream of selection; the hybrid crossing must have
          unlocked fitness ASSEMBLY.
  exp019  assembly mechanism read (genealogy of the exp016 crossing):
          pre-registered strict-inferiority verdicts HILL-CLIMB /
          MIXED blind under the exp018 desert's train ties; POST-HOC
          tie-aware read: 31 RETENTION-ASSEMBLY, 29/37 TIE-BAND-
          DIVERSITY — champion-local keeps the incumbent on ties,
          the archive samples uniformly across tied cells. That read
          was labeled POST-HOC. It has never been tested by running.

Open question THIS experiment seals: the exp019 tie-aware read claims
the archive's hard-root advantage decomposes partly into TIE-BAND
DIVERSITY (sampling across train-tied elites instead of freezing on
the incumbent). If that is a real mechanism, champion-local search
with ONLY the tie-break rule flipped (sample uniformly among
fitness-tied gen-max candidates) should reproduce some or all of the
hard-root crossings — with NO archive, NO retention of non-champion
cells, single-fitness selection otherwise untouched. If tie-sampled
champion-local still crosses 0/3 on the hard class, the tie-band read
is downgraded to interpretation and exp019's assembly verdict stands
on retention alone.

Design pin BEFORE running (anti-laundering):
  Lane: the exact exp016 lane — targets ("000","111"), mode="balance",
    n_qubits=3, train_seed=101, verify_seed=202, shots=512, gate
    budget 6, exp004 jitter-dropped policy restrict=("replace",
    "indel"), one-move classed cloud, pop 16, gens 12.
  Birth: exp006 skeleton [["h",0],["cx",0,1]] in every run.
  Roots: the hard class 29/31/37 (the discriminating comparison) plus
    easy control 13 (expected crossing in both arms — harness sanity
    live in-arm). root_seed = the root value itself, same for both
    arms; arm is the ONLY difference between paired runs.
  Arms:
    ARM-INCUMBENT — best = max(cands, key=fitness); python max keeps
      the FIRST max, cands[0] is the incumbent champion, so train
      ties freeze on the incumbent (exact exp014 semantics).
    ARM-TIESAMPLE — collect all cands with fitness == gen-max fitness
      (exact float equality, no epsilon); if >1, sample uniformly via
      the run's rng. The extra rng draw is part of the arm definition
      (documented stream divergence, same as any behavioral change).
  Both arms: single champion carried forward (NO archive, NO cloud
    retention across gens — tie-sampled pick is promoted or the
    incumbent stays per the usual verify gate); verify gate unchanged
    (best.verify_p >= champion.verify_p).

Interpretation pinned BEFORE running:
  INCUMBENT must reproduce exp014's class on this panel: cross 13,
    0/3 on hard roots. If INCUMBENT crosses a hard root here, that is
    a ROOT-LOTTERY rate read per exp012 (exp014 was the 4/8 panel;
    this is 3 roots), reported as N/M honestly.
  TIESAMPLE crosses >=1 hard root that INCUMBENT missed ->
    TIE-BAND-DIVERSITY REPLICATED: the exp019 post-hoc read upgrades
    to a run mechanism (still an N/M rate claim per ROOT-LOTTERY, not
    a law).
  TIESAMPLE 0/3 on hard roots -> TIE SAMPLING ALONE INSUFFICIENT:
    the archive's hard-root advantage is NOT explained by tie-band
    diversity; exp019's assembly verdict stands on retention alone;
    doctrine: archive load-bearing mechanism = keeping non-champion
    cells, not tie-breaking.
  Either way: per-arm per-root curve + tie counts recorded; crossing
    bar unchanged: held-out verify balance >= 0.45.

Honesty: per-run curve telemetry (one JSONL per arm x root); per-gen
tie-count rows (how many candidates sat at gen-max fitness); no
silent arm merge. Guard: exp001 default lane (2-qubit |01>, targets
("01",), mode "any", root 7, 8 gens, pop 16, shots 512) must
reproduce byte-identical via the SAME instrumented loop before any
results are written — the loop's default tie behavior is incumbent,
so the guard pins the shared machinery; the tie-sample arm diverges
from the guard lane by definition and is not guard-covered (stated).
"""
import functools
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qcell.search import (Candidate, fitness, mutate, mutate_classed,
                          p_target, random_gate)

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp020.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
BUDGET = 6
# hard class (discriminating) + easy control (harness sanity)
ROOTS = (29, 31, 37, 13)
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45

# exp014 named comparator (receipt commit 793a771 — champion-local
# incumbent-on-ties skeleton, 8-root panel; hard class 0/3, 13 easy)
EXP014_COMPARATOR = {
    "source": "exp014-skeleton-multiroot receipt, commit 793a771 "
              "(PR #19; merged 2026-09-29 per queue log #17-#22 burst)",
    "champion_local_incumbent_hard_class": "0/3 on {29,31,37}",
    "champion_local_incumbent_crosses": [3, 13, 17, 19],
}

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))


def run_tiebreak(root_seed, tie_sample, telemetry_path=None):
    """Champion-local skeleton lane; tie_sample flips ONLY the gen-max
    tie-break (uniform among exact-fitness ties vs incumbent-first).
    Single champion, verify gate, no archive, byte-identical child
    stream to the incumbent arm up to the first tie-break divergence.
    """
    rng = random.Random(root_seed)
    champion = Candidate(genome=[list(g) for g in SKELETON])
    champion.train_p = p_target(champion.genome, TRAIN, SHOTS,
                                TARGETS, N, "balance")
    champion.verify_p = p_target(champion.genome, VERIFY, SHOTS,
                                 TARGETS, N, "balance")
    curve = []
    tie_rows = []
    for gen in range(GENS):
        cands = [champion]
        while len(cands) < POP:
            genome = mutate_one(champion.genome, rng, BUDGET,
                                n_qubits=N)
            if genome is None:
                continue  # classed restrict resample (exp003 contract)
            child = Candidate(genome=genome)
            child.train_p = p_target(child.genome, TRAIN, SHOTS,
                                     TARGETS, N, "balance")
            cands.append(child)
        fmax = max(fitness(c) for c in cands)
        tied = [c for c in cands if fitness(c) == fmax]
        tie_rows.append({"gen": gen, "gen_max": round(fmax, 6),
                         "n_tied": len(tied),
                         "incumbent_tied": fitness(champion) == fmax})
        if tie_sample and len(tied) > 1:
            best = rng.choice(tied)
        else:
            best = max(cands, key=lambda c: fitness(c))
        best.verify_p = p_target(best.genome, VERIFY, SHOTS,
                                 TARGETS, N, "balance")
        promoted = best.verify_p >= champion.verify_p
        if promoted:
            champion = best
        curve.append({"gen": gen, "train_p": round(best.train_p, 4),
                      "verify_p": round(best.verify_p, 4),
                      "promoted": promoted,
                      "genome": champion.genome if promoted else None})
        if telemetry_path:
            with open(telemetry_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"gen": gen, "curve": curve[-1],
                                     "tie": tie_rows[-1]},
                                    sort_keys=True) + "\n")
    return {"champion": champion, "curve": curve, "ties": tie_rows}


# --- guard: instrumented loop reproduces exp001 on the DEFAULT lane --
def run_guard_default(root_seed, generations, pop, shots, train_seed,
                      verify_seed):
    """The shared machinery (birth, cloud loop, classed mutate, fitness,
    verify gate) on run_search's default 2-qubit |01> lane, incumbent
    tie-break. Must equal experiments/exp001.results.json."""
    rng = random.Random(root_seed)
    champion = Candidate(genome=[random_gate(rng, 2) for _ in range(3)])
    champion.train_p = p_target(champion.genome, train_seed, shots,
                                ("01",), 2, "any")
    champion.verify_p = p_target(champion.genome, verify_seed, shots,
                                 ("01",), 2, "any")
    curve = []
    for gen in range(generations):
        cands = [champion]
        while len(cands) < pop:
            # exp001 ran run_search's DEFAULT mutator (full mutate,
            # not the exp004 classed policy) — guard must too
            genome = mutate(champion.genome, rng, BUDGET, n_qubits=2)
            child = Candidate(genome=genome)
            child.train_p = p_target(child.genome, train_seed, shots,
                                     ("01",), 2, "any")
            cands.append(child)
        best = max(cands, key=lambda c: fitness(c))
        best.verify_p = p_target(best.genome, verify_seed, shots,
                                 ("01",), 2, "any")
        promoted = best.verify_p >= champion.verify_p
        if promoted:
            champion = best
        curve.append({"gen": gen, "train_p": round(best.train_p, 4),
                      "verify_p": round(best.verify_p, 4),
                      "promoted": promoted,
                      "genome": champion.genome if promoted else None})
    return {"champion": champion, "curve": curve}


guard = run_guard_default(7, generations=8, pop=16, shots=512,
                          train_seed=101, verify_seed=202)
exp001 = json.loads(EXP001.read_text())
control_ok = (guard["curve"] == exp001["curve"]
              and guard["champion"].genome == exp001["champion_genome"])
print("control reproduces exp001:", control_ok)
if not control_ok:
    print("FATAL: shared machinery diverges; results void")
    sys.exit(1)

# --- runs ------------------------------------------------------------
ARMS = {"incumbent": False, "tiesample": True}
runs = {}
for arm, tie_sample in ARMS.items():
    for root in ROOTS:
        telem = LAB / "experiments" / \
            f"exp020.telemetry.{arm}.r{root}.jsonl"
        if telem.exists():
            telem.unlink()
        out = run_tiebreak(root, tie_sample, telemetry_path=str(telem))
        cross = out["champion"].verify_p >= BAR
        runs[f"{arm}.r{root}"] = {
            "arm": arm, "root": root, "crossed": cross,
            "champion_verify": round(out["champion"].verify_p, 4),
            "champion_train": round(out["champion"].train_p, 4),
            "champion_genome": out["champion"].genome,
            "max_verify_seen": round(
                max(c["verify_p"] for c in out["curve"]), 4),
            "gens_any_promotion": sum(1 for c in out["curve"]
                                      if c["promoted"]),
            "tie_gens": sum(1 for t in out["ties"] if t["n_tied"] > 1),
            "tie_gens_incumbent_tied":
                sum(1 for t in out["ties"]
                    if t["n_tied"] > 1 and t["incumbent_tied"]),
        }
        print(f"{arm} r{root}: crossed={cross} "
              f"verify={runs[f'{arm}.r{root}']['champion_verify']} "
              f"tie_gens={runs[f'{arm}.r{root}']['tie_gens']}")

# --- verdict (pre-registered conditions) -----------------------------
hard = (29, 31, 37)
inc_hard = [r for r in hard if runs[f"incumbent.r{r}"]["crossed"]]
tie_hard = [r for r in hard if runs[f"tiesample.r{r}"]["crossed"]]
tie_new = sorted(set(tie_hard) - set(inc_hard))
r13 = {a: runs[f"{a}.r13"]["crossed"] for a in ARMS}

if tie_new:
    verdict = ("TIE-BAND-DIVERSITY REPLICATED: tiesample crossed hard "
               f"root(s) {tie_new} that incumbent missed (per-root "
               "N/M per ROOT-LOTTERY, not a law); exp019 post-hoc "
               "tie-aware read upgrades to run-tested mechanism")
elif inc_hard:
    verdict = ("ROOT-LOTTERY RATE READ: incumbent arm crossed "
               f"{inc_hard} of the hard class here vs exp014's 0/3 — "
               "3-root panel cannot distinguish rate from draw; no "
               "mechanism claim either way")
else:
    verdict = ("TIE SAMPLING ALONE INSUFFICIENT: tiesample 0/3 on the "
               "hard class; archive advantage NOT explained by "
               "tie-band diversity; exp019 assembly verdict stands on "
               "retention alone (archive keeps non-champion cells, "
               "not tie-breaking, is the load-bearing mechanism)")

result = {
    "experiment": "exp020-tie-break-ablation",
    "guard": {
        "control_reproduces_exp001": control_ok,
        "note": "guard covers shared machinery on default lane; "
                "tiesample arm diverges by definition, not guard-"
                "covered (stated)",
    },
    "lane": {"targets": list(TARGETS), "mode": "balance",
             "n_qubits": N, "train_seed": TRAIN, "verify_seed": VERIFY,
             "shots": SHOTS, "pop": POP, "gens": GENS,
             "budget": BUDGET, "mutate": "classed(replace,indel)",
             "birth": SKELETON, "bar": BAR},
    "arms": {"incumbent": "max() first-wins (exp014 semantics)",
             "tiesample": "uniform rng.choice among exact-fitness "
                          "gen-max ties"},
    "comparator": EXP014_COMPARATOR,
    "runs": runs,
    "easy_control_root13_crossed": r13,
    "hard_class": {"incumbent_crossed": inc_hard,
                   "tiesample_crossed": tie_hard,
                   "tiesample_only": tie_new},
    "verdict": verdict,
}
RESULTS.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
print("VERDICT:", verdict)
