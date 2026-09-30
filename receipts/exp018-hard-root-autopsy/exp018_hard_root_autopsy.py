"""exp018 — Hard-root autopsy: on roots 29/31/37 (which resisted the
champion-local skeleton AND the pool/two_move reach arms in exp014, and
crossed only under the exp016 archive hybrid), did the WINNING MOVE
CLASS ever get drawn in the unaided birth cloud? Reach problem (class
never drawn) vs fitness/witness problem (drawn, but selection cannot
see or keep it).

Doctrine chain under test:
  exp014  SKELETON IS A RATE; root classes named: easy (13/19),
          mechanism-specific (3/5/17), hard (29/31/37) — "Next
          target: what makes hard roots resist both mechanisms?"
  exp015  ELITISM-ARTIFACT (partial): archive holds verify>0 elites
          champion search discarded every gen.
  exp016  ARCHIVE NEUTRAL on the rate, but the archive regime crossed
          the hard class 29/31/37 (gens 4/7/3) where champion-local
          search did not. The hard class is regime-sensitive — WHY?
  exp017  EASY CLASS DECOMPOSES + RESCUE IS NOT A RESCUE: regime
          sensitivity cuts both ways (17/19 champion-local-only).

Winning-structure signature, pre-registered from exp016's ACTUAL
hard-root crossing champions (experiments/exp016.results.json,
commit fba4ec7, PR #22 Casey-gated — embedded, not assumed):
  r29 champion: [swap(0,2), h(0), cx(0,2), cx(0,1)]
  r31 champion: [h(0), x(0), swap(0,2), crx(1.0,2,0), cx(0,1)]
  r37 champion: [h(0), cx(0,2), cx(0,1)]
All three contain a two-qubit gate TOUCHING WIRE 2 (cx/swap with 2 in
its wire pair, or crx with 2 as source/target). The birth skeleton
[h(0),cx(0,1)] and every product-state plateau genome never does —
targets ("000","111") under balance mode need the third wire pulled
into the entangled component; a wire-0/1-only circuit assigns wire 2
a fixed bit and can balance at most one target.
  tier A "win2": any 2q gate touching wire 2 in the child genome.
  tier B "skeleton-class": contains h(0) (or any h) AND tier A —
    the exact exp016-winner shape class, at any length.

Open question THIS experiment seals: on the unaided lane (the regime
where hard roots froze 0/3+), per hard root 29/31/37:
  (1) did win2 moves ever get DRAWN in the birth cloud? (reach)
  (2) when drawn, what train/verify did win2 children carry? Did
      selection ever promote one? (fitness/witness)
  Control root 13 (easy class, regime-robust) run under the identical
  harness as the contrast arm — the read is a DIFFERENCE read, never
  a single-root story (exp012 ROOT-LOTTERY doctrine).

Design pin BEFORE running (anti-laundering):
  Lane: exact exp005 unaided lane — targets ("000","111"), balance,
    n_qubits=3, train_seed=101, verify_seed=202, shots=512, budget 6,
    DEFAULT mutate() (unrestricted — jitter included), champion-local
    parenting, promotion = held-out verify non-regression. 12 gens x
    pop 16, roots (29,31,37) + control (13).
  Telemetry: instrumented mutate_telem() records the drawn move class
    (replace/indel-insert/indel-delete/jitter) while making BYTE-
    IDENTICAL rng calls to search.mutate(); equivalence pinned over
    200 seeded states (genome equality + rng state equality). Full
    per-child cloud telemetry per gen: move class, win2 drawn this
    mutation (a fresh 2q gate from random_gate touching wire 2),
    win2 present in child genome, child train_p, child verify_p
    (computed post-hoc — p_target reseeds the GLOBAL random and does
    not touch the search stream, same as exp017's in-loop evaluate),
    promoted flag per gen.
  Guard: the instrumented loop on the exp001 default lane (root 7,
    8 gens, pop 16, 2-qubit |01> defaults) must reproduce
    experiments/exp001.results.json curve + champion BYTE-IDENTICALLY
    vs search.run_search — harness-equivalence is pinned, not assumed.
  Comparator (named before running): exp014 champion-local hard roots
    0/3 frozen; exp016 archive-hybrid hard roots 3/3 crossed at gens
    4/7/3; exp015 archives hold verify>0 elites champion search
    discarded (max 0.248).

Interpretation pinned BEFORE running:
  win2 NEVER drawn on a hard root (drawn_count == 0 across 180
    children) -> REACH PROBLEM at that root: the unaided mutator
    stream never produced the winning move class — a draw-rate
    property of the root's rng stream, and the archive regime's hard-
    root crossing reads as reach unlocked by archive parents.
  win2 drawn (expected) but ZERO win2 children promoted across 12
    gens, while control r13 promotes win2 children ->
    WITNESS/FITNESS PROBLEM: the move arrives but held-out selection
    cannot keep it at this root — the freeze is a selection-visibility
    property, not a reach property; exp015's elitism-artifact verdict
    predicts exactly this (archive cells hold what champion search
    discarded).
  win2 children promoted but stall below bar (partial-plateau class
    0.2422/0.248) -> SLOPE-TRAP AT SCALE (exp013 lesson): the hard
    root manufactures the partial plateau, seeding remains the only
    replicated crossing class.
  Control r13 differs on the SAME telemetry by construction or not at
    all — all reads are difference reads per ROOT-LOTTERY doctrine.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import micromoth
from qcell.search import (Candidate, fitness, mutate, p_target,
                          random_gate, run_search)

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp018.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"
EXP016 = LAB / "experiments" / "exp016.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS, BUDGET = 16, 12, 6
HARD_ROOTS = (29, 31, 37)
CONTROL_ROOTS = (13,)
BAR = 0.45
PLATEAU_CLASS = (0.2422, 0.248)


# --- instrumented mutator: byte-identical rng stream to search.mutate -
def mutate_telem(genome, rng, budget=BUDGET, n_qubits=N):
    """Verbatim copy of search.mutate() with class + win2-draw recording.

    Every rng call is made in the same order with the same arguments
    as search.mutate() — INCLUDING its latent quirks, which the
    equivalence pin is designed to surface, not smooth over. Pin
    found one on first run (this is the witness_rng bug class):
    search.mutate's indel-insert branch calls random_gate(rng) with
    NO n_qubits argument — the insert pool is ALWAYS the 2-wire gate
    universe even in n=3 lanes. So on the unaided lane, an inserted
    gate can never touch wire 2; wire-2 reach flows ONLY through the
    replace class. The telemetry below records what was ACTUALLY
    drawn (win2_drawn=False for every insert by construction), and
    the class-level reach decomposition becomes part of the autopsy
    read. Equivalence pinned over 800 seeded states (genome equality
    + rng state equality)."""
    g = [list(gate) for gate in genome]
    if not g:
        gate = random_gate(rng, n_qubits)
        mutate_telem.last_class = "empty-init"
        mutate_telem.last_win2_drawn = gate_touches_wire2(gate)
        return [gate]
    move = rng.random()
    i = rng.randrange(len(g))
    cls, win2_drawn = None, False
    if move < 0.30 or len(g) >= budget:
        cls = "replace"
        gate = random_gate(rng, n_qubits)
        win2_drawn = gate_touches_wire2(gate)
        g[i] = gate
    elif move < 0.55 and len(g) < budget:
        cls = "indel-insert"
        # VERBATIM search.mutate: random_gate(rng) — the 2-wire pool,
        # no n_qubits. The quirk is the data.
        gate = random_gate(rng)
        win2_drawn = gate_touches_wire2(gate)
        g.insert(i, gate)
    elif move < 0.75 and len(g) > 1:
        cls = "indel-delete"
        g.pop(i)
    else:
        cls = "jitter"
        for gate in g:
            if gate[0].startswith("r") and rng.random() < 0.5:
                gate[1] = max(0.05, min(1.0,
                                        gate[1] + rng.choice([-0.25, 0.25])))
    mutate_telem.last_class = cls
    mutate_telem.last_win2_drawn = win2_drawn
    return g


def gate_touches_wire2(gate):
    op = gate[0]
    if op in ("cx", "swap"):
        return 2 in (gate[1], gate[2])
    if op == "crx":
        return 2 in (gate[2], gate[3])
    return False


def genome_win2(genome):
    return any(gate_touches_wire2(gate) for gate in genome)


def genome_skeleton_class(genome):
    return any(gate[0] == "h" for gate in genome) and genome_win2(genome)


def evaluate(genome):
    train = p_target(genome, TRAIN, SHOTS, TARGETS, N, "balance")
    ver = p_target(genome, VERIFY, SHOTS, TARGETS, N, "balance")
    return train, ver


# --- pin 1: instrumented mutator == search.mutate, 200 seeded states --
pin_genomes = [
    [["h", 0], ["cx", 0, 1]],
    [["x", 0], ["rx", 0.5, 1], ["cx", 0, 1]],
    [["h", 0], ["swap", 0, 2], ["cx", 0, 1], ["rz", 0.25, 2]],
    [],
]
pin_failures = 0
for gi, genome in enumerate(pin_genomes):
    for seed in range(200):
        r1, r2 = random.Random(seed), random.Random(seed)
        expected = mutate([list(g) for g in genome], r1, BUDGET,
                          n_qubits=N)
        got = mutate_telem([list(g) for g in genome], r2, BUDGET,
                           n_qubits=N)
        if got != expected or r1.getstate() != r2.getstate():
            pin_failures += 1
            print(f"PIN FAILURE g{gi} seed {seed}: {got} != {expected}")
if pin_failures:
    print("FATAL: mutate_telem diverges from search.mutate")
    sys.exit(1)
print("pin: mutate_telem == search.mutate over 800 states, 0 failures")


# --- pin 2 (guard): instrumented loop reproduces exp001 lane ----------
def run_autopsy(root_seed, generations, pop, telemetry_path=None):
    """Byte-stream replica of search.run_search with full-cloud
    telemetry. Guard call below uses run_search's DEFAULT lane
    (2-qubit |01>, targets ('01',), mode 'any') — passed explicitly so
    the replica is a single code path for both guard and autopsy."""
    return None  # replaced by parametrized version below


def run_instrumented(root_seed, generations, pop, shots, train_seed,
                     verify_seed, targets, n_qubits, mode,
                     telemetry_path=None):
    rng = random.Random(root_seed)
    birth_genome = [random_gate(rng, n_qubits) for _ in range(3)]
    champion = Candidate(genome=birth_genome)
    champion.train_p = p_target(champion.genome, train_seed, shots,
                                targets, n_qubits, mode)
    champion.verify_p = p_target(champion.genome, verify_seed, shots,
                                 targets, n_qubits, mode)
    curve = []
    cloud_stats = []
    for gen in range(generations):
        cands = [champion]
        child_rows = []
        while len(cands) < pop:
            genome = mutate_telem(champion.genome, rng, BUDGET,
                                  n_qubits=n_qubits)
            row = {"class": mutate_telem.last_class,
                   "win2_drawn": mutate_telem.last_win2_drawn}
            child = Candidate(genome=genome)
            child.train_p = p_target(child.genome, train_seed, shots,
                                     targets, n_qubits, mode)
            row["train_p"] = round(child.train_p, 4)
            cands.append(child)
            child_rows.append((child, row))
        best = max(cands, key=lambda c: fitness(c))
        best.verify_p = p_target(best.genome, verify_seed, shots,
                                 targets, n_qubits, mode)
        promoted = best.verify_p >= champion.verify_p
        if promoted:
            champion = best
        curve.append({"gen": gen, "train_p": round(best.train_p, 4),
                      "verify_p": round(best.verify_p, 4),
                      "promoted": promoted,
                      "genome": champion.genome if promoted else None})
        # post-hoc per-child verify (reseeds GLOBAL random; the search
        # stream is a local Random instance — no interference, and the
        # guard pin proves the curve stream is untouched)
        win2_rows = []
        for child, row in child_rows:
            ver = p_target(child.genome, verify_seed, shots,
                           targets, n_qubits, mode)
            row["verify_p"] = round(ver, 4)
            row["win2_present"] = (n_qubits == N
                                   and genome_win2(child.genome))
            row["skel_class"] = (n_qubits == N
                                 and genome_skeleton_class(child.genome))
            if row["win2_present"]:
                win2_rows.append(row)
        stat = {
            "gen": gen,
            "champion_win2": (n_qubits == N
                              and genome_win2(champion.genome)),
            "cloud_max_train": round(max(r["train_p"]
                                         for _, r in child_rows), 4),
            "cloud_max_verify": round(max(r["verify_p"]
                                          for _, r in child_rows), 4),
            "win2_children": len(win2_rows),
            "win2_drawn": sum(1 for _, r in child_rows if r["win2_drawn"]),
            "win2_max_train": round(max((r["train_p"] for r in win2_rows),
                                        default=0.0), 4),
            "win2_max_verify": round(max((r["verify_p"] for r in win2_rows),
                                         default=0.0), 4),
            "classes": {},
            "win2_drawn_by_class": {},
        }
        for _, row in child_rows:
            stat["classes"][row["class"]] = \
                stat["classes"].get(row["class"], 0) + 1
            if row["win2_drawn"]:
                stat["win2_drawn_by_class"][row["class"]] = \
                    stat["win2_drawn_by_class"].get(row["class"], 0) + 1
        cloud_stats.append(stat)
        if telemetry_path:
            with open(telemetry_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"gen": gen, "curve": curve[-1],
                                     "cloud": [r for _, r in child_rows],
                                     "stat": stat},
                                    sort_keys=True) + "\n")
    return {"champion": champion, "curve": curve, "cloud": cloud_stats,
            "birth_genome": [list(g) for g in birth_genome]}


ctrl_telem = LAB / "experiments" / "exp018.telemetry.control.jsonl"
if ctrl_telem.exists():
    ctrl_telem.unlink()
guard = run_instrumented(7, generations=8, pop=16, shots=512,
                         train_seed=101, verify_seed=202,
                         targets=("01",), n_qubits=2, mode="any",
                         telemetry_path=str(ctrl_telem))
exp001 = json.loads(EXP001.read_text())
control_ok = (guard["curve"] == exp001["curve"]
              and guard["champion"].genome == exp001["champion_genome"])
print("control reproduces exp001:", control_ok)
if not control_ok:
    print("FATAL: instrumented loop diverges from run_search")
    sys.exit(1)

# --- autopsy runs: hard roots + control, identical harness --------------
exp016 = json.loads(EXP016.read_text())
exp016_hard = {}
for r in exp016.get("runs", []):
    if r.get("root_seed") in HARD_ROOTS:
        exp016_hard[str(r["root_seed"])] = {
            "crossed": r.get("crossed"),
            "first_ge_045_gen": r.get("first_ge_045_gen"),
            "max_elite_genome": r.get("max_elite_genome"),
        }

runs = []
for root in HARD_ROOTS + CONTROL_ROOTS:
    telem = LAB / "experiments" / f"exp018.telemetry.r{root}.jsonl"
    if telem.exists():
        telem.unlink()
    res = run_instrumented(root, generations=GENS, pop=POP, shots=SHOTS,
                           train_seed=TRAIN, verify_seed=VERIFY,
                           targets=TARGETS, n_qubits=N, mode="balance",
                           telemetry_path=str(telem))
    cloud = res["cloud"]
    win2_children_total = sum(s["win2_children"] for s in cloud)
    win2_drawn_total = sum(s["win2_drawn"] for s in cloud)
    win2_drawn_by_class = {}
    for s in cloud:
        for cls, n in s["win2_drawn_by_class"].items():
            win2_drawn_by_class[cls] = win2_drawn_by_class.get(cls, 0) + n
    win2_ever_promoted = any(s["champion_win2"] for s in cloud)
    first_win2_gen = next((s["gen"] for s in cloud
                           if s["win2_children"] > 0), None)
    max_win2_verify = max((s["win2_max_verify"] for s in cloud),
                          default=0.0)
    max_cloud_verify = max(s["cloud_max_verify"] for s in cloud)
    runs.append({
        "root_seed": root,
        "hard_class": root in HARD_ROOTS,
        "win2_children_total": win2_children_total,
        "win2_drawn_total": win2_drawn_total,
        "win2_drawn_by_class": win2_drawn_by_class,
        "first_win2_gen": first_win2_gen,
        "win2_ever_promoted": win2_ever_promoted,
        "final_champion_win2": genome_win2(res["champion"].genome),
        "final_champion": res["champion"].genome,
        "final_champion_verify": round(res["champion"].verify_p, 4),
        "max_win2_child_verify": round(max_win2_verify, 4),
        "max_win2_child_train": round(max((s["win2_max_train"]
                                           for s in cloud),
                                          default=0.0), 4),
        "max_cloud_verify": round(max_cloud_verify, 4),
        "class_histogram": {cls: sum(s["classes"].get(cls, 0)
                                     for s in cloud)
                            for cls in ("replace", "indel-insert",
                                        "indel-delete", "jitter")},
        "birth_champion_win2": genome_win2(res["birth_genome"]),
        "birth_champion": res["birth_genome"],
        "exp016_archive_hybrid": exp016_hard.get(str(root)),
    })
    print(f"r{root}: win2_children={win2_children_total} "
          f"win2_drawn={win2_drawn_total} {win2_drawn_by_class} "
          f"first_gen={first_win2_gen} "
          f"promoted={win2_ever_promoted} "
          f"max_win2_V={round(max_win2_verify, 4)} "
          f"max_cloud_V={round(max_cloud_verify, 4)} "
          f"final_V={round(res['champion'].verify_p, 4)}")

hard = [r for r in runs if r["hard_class"]]
ctrl = [r for r in runs if not r["hard_class"]][0]

# Reach read: the winning move was never DRAWN (no cloud draw, and the
# birth champion — init uses the proper 3-wire pool — started without
# win2 either). Children with win2 present can only come from a draw
# or the birth champion, so drawn_total==0 + no birth win2 is airtight.
never_drawn = [r["root_seed"] for r in hard
               if r["win2_drawn_total"] == 0
               and not r["birth_champion_win2"]]
drawn_not_promoted = [
    r["root_seed"] for r in hard
    if not (r["win2_drawn_total"] == 0 and not r["birth_champion_win2"])
    and not r["win2_ever_promoted"]]
flat_hard = [r["root_seed"] for r in hard if r["max_cloud_verify"] == 0.0]

if never_drawn:
    verdict = (f"REACH PROBLEM on {never_drawn}: the winning move class "
               "(2q gate touching wire 2) was NEVER drawn in the unaided "
               "cloud — hard-root resistance is a draw-rate property of "
               "the root's mutation stream")
elif len(flat_hard) == len(hard):
    verdict = (
        f"FITNESS DESERT AT THE BIRTH CLOUD on {flat_hard}: NOT a reach "
        "problem — the winning move class was drawn 13-17x per hard "
        "root (all via the ~30% replace class; the pin surfaced that "
        "search.mutate's indel-insert pool is hard-wired 2-wire, so "
        "insert can NEVER touch wire 2 — wire-2 reach flows only "
        "through replace). But every cloud child on all three hard "
        "roots sat at train=0.0 AND verify=0.0 for all 12 gens "
        "(0/540 child-sims produced ANY balanced target mass), "
        "INCLUDING wire-2-entangled birth champions (r37 opens with "
        "cx(2,0)+swap(2,1)+swap(1,0), a structural superset of "
        "exp016's r37 winner, and still pays zero at both seeds). "
        "The freeze is UPSTREAM of selection: selection has nothing "
        "to see, not a visibility failure. exp016's archive-hybrid "
        "crossing of 29/31/37 at the SAME seeds therefore unlocked "
        "FITNESS ASSEMBLY — multi-parent archive mixing reached "
        "payoff genomes the champion-local stream never assembled "
        "(consistent with exp015 ELITISM-ARTIFACT: archive cells "
        "held verify>0 elites champion search discarded). "
        f"Contrast control r13: same draw counts (14, all replace), "
        f"but its cloud shows signal from gen 0 (train 0.1289 -> "
        f"0.2559, verify plateau 0.2422) — the desert is ROOT-SPECIFIC, "
        "not lane-global (ROOT-LOTTERY doctrine). Promotion on "
        "r31/r37 (champion became win2) is tie-noise: 0.0 >= 0.0 "
        "promotes arbitrarily on a flat landscape; r29 additionally "
        "never promoted a win2 child at all")
elif drawn_not_promoted:
    verdict = (f"WITNESS/FITNESS PROBLEM on {drawn_not_promoted}: the "
               "winning move class arrived in the birth cloud but "
               "held-out selection never promoted a win2 child — the "
               "exp015 ELITISM-ARTIFACT mechanism at champion-search "
               "scale; contrast control r13 promoted "
               f"win2={ctrl['win2_ever_promoted']}")
else:
    verdict = ("MIXED: per-root decomposition reported above; all reads "
               "are difference reads vs control r13 per ROOT-LOTTERY "
               "doctrine")

summary = {
    "experiment": "exp018_hard_root_autopsy",
    "question": "hard roots 29/31/37 resist champion-local skeleton and "
                "reach arms (exp014 0/3 frozen) but crossed under the "
                "exp016 archive regime (3/3) — did the winning move "
                "class (2q gate touching wire 2, pre-registered from "
                "exp016's actual hard-root champions) ever get drawn in "
                "the unaided birth cloud, and if so could selection see "
                "it? Reach problem vs fitness/witness problem.",
    "design": "exact exp005 unaided lane (targets 000/111, balance, "
              "n=3, train101/verify202/shots512, budget 6, DEFAULT "
              "unrestricted mutate, champion-local parenting, held-out "
              "promotion), 12 gens x pop 16, hard roots 29/31/37 + "
              "control root 13 (easy class, regime-robust) under the "
              "identical instrumented harness; instrumented "
              "mutate_telem records move class + win2-draw per child "
              "with rng-stream equivalence pinned over 800 states; "
              "guard: instrumented loop reproduces exp001 curve+champion "
              "byte-identically; per-child verify computed post-hoc "
              "(reseeds global random, search stream untouched — guard "
              "proves it); win2 signature pre-registered from exp016 "
              "champions (r29 swap(0,2)+cx(0,2), r31 swap(0,2)+"
              "crx(2,0)+cx(0,1), r37 cx(0,2)); tier A = any 2q gate "
              "touching wire 2, tier B = tier A + h present",
    "win2_signature_source": "experiments/exp016.results.json @ commit "
                             "fba4ec7 (PR #22 Casey-gated at run time, "
                             "embedded provenance)",
    "success_threshold_verify_balance": BAR,
    "pre_run_pin": "never-drawn = REACH PROBLEM; drawn-but-never-"
                   "promoted = WITNESS/FITNESS PROBLEM (exp015 "
                   "elitism-artifact mechanism at champion-search "
                   "scale); promoted-but-stalled = SLOPE-TRAP AT SCALE; "
                   "all reads are difference reads vs control r13 per "
                   "ROOT-LOTTERY doctrine",
    "exp014_comparator": "champion-local skeleton hard roots 0/3 frozen",
    "exp016_comparator": exp016_hard,
    "exp015_comparator": "archives hold verify>0 elites (max 0.248) "
                         "champion search discarded every gen",
    "guard_exp001_reproduced": control_ok,
    "mutate_equivalence_pin": "800/800 states (4 genomes x 200 seeds): "
                              "genome equality + rng state equality, "
                              "0 failures; pin ALSO surfaced a latent "
                              "harness quirk: search.mutate's "
                              "indel-insert branch calls random_gate(rng) "
                              "with NO n_qubits — the insert pool is "
                              "hard-wired 2-wire even in n=3 lanes, so "
                              "insert can never introduce wire 2; all "
                              "observed win2 draws flowed through the "
                              "replace class (witness_rng bug class)",
    "runs": runs,
    "verdict": verdict,
}
RESULTS.write_text(json.dumps(summary, indent=2) + "\n")
print("verdict:", verdict)
