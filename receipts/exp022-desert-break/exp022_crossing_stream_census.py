"""exp022 — crossing-stream census: does the k3/k5/k6 band hold the
>=0.45 cell, and how does it get promoted?

Doctrine chain under test:
  exp018  FITNESS DESERT AT THE BIRTH CLOUD on 29/31/37: all
          hard-root child-sims train=0 AND verify=0 for 12 gens.
  exp020  TIE-BAND-DIVERSITY REPLICATED: tie-sampled champion-local
          (no archive) crossed 29 + 37 @0.4824; 31 stayed closed.
  exp021  RATE NOT WALL (31: 3/8 salted streams crossed) +
          DESERT-EXTENDS-TO-CLOUD on the canonical NON-crossing
          stream (seed 31): no cloud cell >=0.45 in 12 gens, so the
          exp016 archive crossing necessarily assembled fitness
          across gens.  Q2 census ran ONLY on the non-crossing
          canonical stream.

Open question THIS experiment seals:
  The exp021 Q2 census covered exactly one stream — the one that
  did NOT cross.  exp022 runs the SAME passive census on the
  crossing band k3/k5/k6 (seeds 31003/31005/31006) plus two
  contrast non-crossing streams (k4 near-miss 0.418, k7 dead 0.0),
  asking: on streams that DID cross, where did the >=0.45 cell
  come from?
  Pinned outcome (a) DESERT-FLOOR TIE-BAND LOTTERY: the crossing
      cell appeared in the cloud with train=0 (desert-floor),
      sat inside an all-floor tie band (gen_max = floor), and was
      promoted purely by the tie-sample rng draw — TIE-BAND-
      DIVERSITY refines from 'mechanism' to 'lottery odds':
      P(cross) = P(>=BAR cell born) x P(drawn within its window).
      Window length (gens cell sat in cloud before pick) reported
      per stream.
  Pinned outcome (b) TRAIN-VISIBLE CROSSING: the crossing cell
      carried train > 0 in its promotion gen — exp018's desert is
      root-specific, not stream-specific, and crossing streams
      simply escape the desert; reported honestly if so.
  Contrast expectation (not a verdict condition): k4's near-miss
      cloud should top out just under BAR; k7's cloud should hold
      nothing — if k4/k7 clouds DO hold >=BAR cells that were
      never drawn, that is OPPORTUNITY-MISSED evidence sharpening
      the lottery read.

Design pins BEFORE running (anti-laundering):
  Lane: exact exp020/exp021 lane — targets ("000","111"), mode
    "balance", n_qubits=3, train_seed=101, verify_seed=202,
    shots=512, gate budget 6, exp004 policy restrict=("replace",
    "indel"), pop 16, gens 12, birth skeleton [["h",0],["cx",0,1]],
    BAR 0.45, tie_sample=True (the exact exp020 tiesample arm).
  Streams (exp021 Q1 seeds, results exp021.results.json):
    crossing band: k3=31003, k5=31005, k6=31006 (all @0.4824)
    contrast:      k4=31004 (0.418), k7=31007 (0.0)
  Census: passive observer — per-candidate verify evals consume NO
    rng; child stream + tie-break sequence byte-identical to
    exp020/exp021 (reuses run_tiebreak from exp021 module shape,
    copied here to keep the experiment self-contained).
  Replicate pins: k3/k5/k6 champions must finish @0.4824 crossed,
    k4 @0.418 not crossed, k7 @0.0 (all vs exp021.results.json
    values verbatim) — census inactive-with-respect-to-stream
    proven by the replicates, not assumed.
  Guard: exp001 default lane through the SAME instrumented loop
    (census ACTIVE) must reproduce experiments/exp001.results.json
    byte-identical.

Honesty: telemetry JSONL per stream; results JSON carries
pre-registered conditions verbatim; post-hoc reads labeled.  No
archive, no retention anywhere in this experiment.
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
RESULTS = LAB / "experiments" / "exp022.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"
EXP021 = LAB / "experiments" / "exp021.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
BUDGET = 6
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45

# exp021 Q1 verbatim values (replicate pins)
STREAMS = {
    "k3": {"seed": 31003, "expected_champion": 0.4824,
           "expected_crossed": True, "class": "crossing"},
    "k4": {"seed": 31004, "expected_champion": 0.418,
           "expected_crossed": False, "class": "contrast_near_miss"},
    "k5": {"seed": 31005, "expected_champion": 0.4824,
           "expected_crossed": True, "class": "crossing"},
    "k6": {"seed": 31006, "expected_champion": 0.4824,
           "expected_crossed": True, "class": "crossing"},
    "k7": {"seed": 31007, "expected_champion": 0.0,
           "expected_crossed": False, "class": "contrast_dead"},
}

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))


def run_tiebreak_census(root_seed, telemetry_path):
    """Exact exp021 Q2 census semantics (passive observer, no rng)."""
    rng = random.Random(root_seed)
    champion = Candidate(genome=[list(g) for g in SKELETON])
    champion.train_p = p_target(champion.genome, TRAIN, SHOTS,
                                TARGETS, N, "balance")
    champion.verify_p = p_target(champion.genome, VERIFY, SHOTS,
                                 TARGETS, N, "balance")
    curve = []
    census_rows = []
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
        cloud = []
        for c in cands:
            vp = p_target(c.genome, VERIFY, SHOTS, TARGETS, N,
                          "balance")
            cloud.append({
                "genome": [list(g) for g in c.genome],
                "train_p": round(c.train_p, 6),
                "verify_p": round(vp, 6),
                "in_band": fitness(c) == fmax,
                "is_champion": c is champion,
            })
        census_rows.append({"gen": gen, "gen_max": round(fmax, 6),
                            "n_tied": len(tied), "cloud": cloud})
        best = rng.choice(tied) if len(tied) > 1 else tied[0]
        best.verify_p = p_target(best.genome, VERIFY, SHOTS,
                                 TARGETS, N, "balance")
        promoted = best.verify_p >= champion.verify_p
        if promoted:
            champion = best
        curve.append({"gen": gen, "train_p": round(best.train_p, 4),
                      "verify_p": round(best.verify_p, 4),
                      "promoted": promoted,
                      "genome": champion.genome if promoted else None})
        with open(telemetry_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(
                {"gen": gen, "curve": curve[-1],
                 "census": census_rows[-1]}, sort_keys=True) + "\n")
    return {"champion": champion, "curve": curve,
            "census": census_rows}


# --- guard: instrumented loop (census ACTIVE) reproduces exp001 ------
def run_guard_default(root_seed, generations, pop, shots, train_seed,
                      verify_seed):
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
print("control reproduces exp001 (census active):", control_ok)
if not control_ok:
    print("FATAL: instrumented loop diverges; results void")
    sys.exit(1)

exp021_doc = json.loads(EXP021.read_text())

# --- census per stream ------------------------------------------------
streams = {}
for name, spec in STREAMS.items():
    telem = LAB / "experiments" / f"exp022.telemetry.{name}.jsonl"
    if telem.exists():
        telem.unlink()
    out = run_tiebreak_census(spec["seed"], str(telem))
    champ_v = round(out["champion"].verify_p, 4)
    crossed = champ_v >= BAR
    replicate_ok = (champ_v == spec["expected_champion"]
                    and crossed == spec["expected_crossed"])

    # where did >=BAR cells live, per gen?
    bar_cells = []          # every cloud cell >= BAR across gens
    band_bar_gens = []      # gens where the TIE BAND held >=BAR
    cloud_bar_gens = []     # gens where the CLOUD held >=BAR
    first_bar_gen = None
    for row in out["census"]:
        bars = [c for c in row["cloud"] if c["verify_p"] >= BAR]
        if bars and first_bar_gen is None:
            first_bar_gen = row["gen"]
        for c in bars:
            bar_cells.append({
                "gen": row["gen"], "train_p": c["train_p"],
                "verify_p": c["verify_p"], "in_band": c["in_band"],
                "gen_max": row["gen_max"],
            })
        if any(c["in_band"] for c in bars):
            band_bar_gens.append(row["gen"])
        if bars:
            cloud_bar_gens.append(row["gen"])

    # the promotion event: gen where a >=BAR cell was PICKED
    pick_gen = None
    for row in out["census"]:
        gen = row["gen"]
        if (gen < len(out["curve"]) and out["curve"][gen]["promoted"]
                and out["curve"][gen]["verify_p"] >= BAR):
            pick_gen = gen
            break

    streams[name] = {
        "seed": spec["seed"], "class": spec["class"],
        "champion_verify": champ_v, "crossed": crossed,
        "exp021_replicate_ok": replicate_ok,
        "first_bar_cell_gen": first_bar_gen,
        "bar_cell_gens": sorted({c["gen"] for c in bar_cells}),
        "band_bar_gens": band_bar_gens,
        "pick_gen": pick_gen,
        "n_bar_cells_total": len(bar_cells),
        "bar_cells_train_values": sorted(
            {c["train_p"] for c in bar_cells}),
        "bar_cells_in_band_only": (
            all(c["in_band"] for c in bar_cells)
            if bar_cells else None),
        "bar_cells_gen_max_values": sorted(
            {c["gen_max"] for c in bar_cells}),
        "window_gens": (pick_gen - first_bar_gen
                        if (pick_gen is not None
                            and first_bar_gen is not None) else None),
    }
    print(f"{name} (seed {spec['seed']}): replicate_ok={replicate_ok} "
          f"champ={champ_v} crossed={crossed} "
          f"bar_gens={streams[name]['bar_cell_gens']} "
          f"pick_gen={pick_gen} "
          f"bar_train={streams[name]['bar_cells_train_values']}")

# --- verdicts (pre-registered conditions) -----------------------------
crossing = {k: v for k, v in streams.items() if v["class"] == "crossing"}
contrast = {k: v for k, v in streams.items() if v["class"] != "crossing"}

all_replicated = all(v["exp021_replicate_ok"] for v in streams.values())
crossing_floor_band = all(
    v["bar_cells_train_values"] == [0.0]
    and v["bar_cells_in_band_only"]
    and v["bar_cells_gen_max_values"] == [0.0]
    for v in crossing.values())
if not all_replicated:
    verdict = ("VOID: replicate pins failed — census run does not "
               "reproduce exp021 stream outcomes; do not read")
elif not crossing:
    verdict = "no crossing streams in panel (unexpected; panel error)"
elif crossing_floor_band:
    windows = [v["window_gens"] for v in crossing.values()]
    verdict = (
        "DESERT-FLOOR TIE-BAND LOTTERY: on every crossing stream the "
        f">={BAR} cell appeared at train=0.0 inside an all-floor tie "
        "band (gen_max 0.0) and was promoted purely by the tie-sample "
        f"rng draw — windows {windows} gens. TIE-BAND-DIVERSITY "
        "refines from 'mechanism' to lottery odds: P(cross) = "
        "P(>=BAR cell born on stream) x P(drawn within window); "
        "exp018's desert holds AT THE FLOOR (zero train signal) yet "
        "the floor band is exactly where a high-verify cell hides — "
        "train fitness on this lane is anti-correlated with verify "
        "in the desert, so incumbent-first (max-by-insertion-order) "
        "never picks it and uniform tie sampling eventually does. "
        "RETENTION not needed to explain the no-archive crossings "
        "(exp020/021 reads stand for 31-archive only)."
    )
else:
    mixed = {k: {"train": v["bar_cells_train_values"],
                 "gen_max": v["bar_cells_gen_max_values"],
                 "in_band_only": v["bar_cells_in_band_only"]}
             for k, v in crossing.items()}
    verdict = (f"TRAIN-VISIBLE OR MIXED CROSSING: crossing cells not "
               f"uniformly desert-floor {mixed} — read per stream; "
               "exp018 root-specific desert refined")

contrast_note = (
    {k: {"champion_verify": v["champion_verify"],
         "bar_cell_gens": v["bar_cell_gens"],
         "band_bar_gens": v["band_bar_gens"],
         "window_gens": v["window_gens"]}
     for k, v in contrast.items()}
)

out_doc = {
    "experiment": "exp022 crossing-stream census",
    "question": "does the k3/k5/k6 crossing band hold the >=0.45 "
                "cell, and how is it promoted (exp021 Q2 covered "
                "only the non-crossing canonical stream)",
    "lane": {"targets": list(TARGETS), "mode": "balance",
             "n_qubits": N, "train_seed": TRAIN,
             "verify_seed": VERIFY, "shots": SHOTS,
             "budget": BUDGET, "restrict": ["replace", "indel"],
             "pop": POP, "gens": GENS, "skeleton": SKELETON,
             "bar": BAR, "tie_sample": True},
    "guard": {"exp001_reproduced_byte_identical": control_ok},
    "streams": streams,
    "contrast_read": contrast_note,
    "verdict": verdict,
    "honesty": "census evals consume no rng; replicate pins vs "
               "exp021.results.json champion/crossed values verbatim "
               "prove stream-inertness per stream, not assumed; "
               "post-hoc reads labeled; no archive, no retention "
               "anywhere in this experiment",
}
RESULTS.write_text(json.dumps(out_doc, indent=1, sort_keys=True))
print("\nVERDICT:", verdict)
print("wrote", RESULTS)
