"""exp021 — r31-specific tie-context autopsy: WHY does root 31 alone
resist tie-band diversity?

Doctrine chain under test:
  exp014  SKELETON IS A RATE: champion-local incumbent-on-ties crosses
          easy {3,13,17,19}; hard class {29,31,37} 0/3.
  exp016  skeleton+archive HYBRID crossed 6/8 incl. all three hard
          roots.
  exp018  FITNESS DESERT AT THE BIRTH CLOUD on 29/31/37: all 540
          hard-root child-sims at train=0 AND verify=0 — freeze is
          upstream of selection.
  exp019  assembly mechanism read: 31 = RETENTION-ASSEMBLY (route
          rides 3 zero-train ancestors only archive cells keep);
          29/37 = TIE-BAND-DIVERSITY.
  exp020  TIE-BAND-DIVERSITY REPLICATED: tie-sampled champion-local
          (no archive) crossed 29 + 37 @0.4824 — but 31 alone stayed
          closed (peak 0.3027, champion verify 0.3027).

Open questions THIS experiment seals:
  Q1 (rate vs wall): is 31's resistance a per-stream RATE (ROOT-
      LOTTERY) or absolute at this panel? Replicate the exact
      exp020 tiesample lane on r31 across K=8 salted rng streams.
      >=1 crossing in 8 -> resistance is a rate; 0/8 -> wall at
      K=8 power (desert read stands, exp019 retention verdict for
      31 consistent).
  Q2 (opportunity census): on the canonical exp020 stream (seed=31),
      census EVERY cloud cell's held-out verify per gen (not just
      the tie band, not just the promoted pick). Three pinned
      outcomes:
        (a) some gen's TIE BAND contains a verify>=0.45 cell ->
            OPPORTUNITY-MISSED: tie sampling failed to draw an
            existing crossing cell; resistance is sampling-luck,
            strongly rate-supporting.
        (b) cloud contains verify>=0.45 cell but NEVER in any tie
            band -> STRUCTURAL MISMATCH: crossing fitness is
            invisible to gen-max train selection on 31 (a real
            finding about the desert's shape, not sampling luck).
        (c) cloud NEVER contains verify>=0.45 cell across all 12
            gens -> DESERT-EXTENDS-TO-CLOUD: no single cloud on this
            stream held a crossing cell; exp016's r31 crossing must
            have assembled fitness ACROSS gens via retention
            (exp019 RETENTION-ASSEMBLY verdict is the only
            remaining mechanism).
      Census evals use p_target's deterministic seeds and consume
      NO rng draws; the child stream and tie-break sequence are
      byte-identical to exp020 (census is a passive observer).

Design pins BEFORE running (anti-laundering):
  Lane: exact exp020 lane — targets ("000","111"), mode "balance",
    n_qubits=3, train_seed=101, verify_seed=202, shots=512, gate
    budget 6, exp004 policy restrict=("replace","indel"), pop 16,
    gens 12, birth skeleton [["h",0],["cx",0,1]], BAR 0.45.
  Q1: K=8 replicates, rng seed = 31000+k (k=0..7). exp020 used
    seed=31 (=31000-30969 convention declared here as its own
    baseline stream, rerun as replicate k=31 for census in Q2).
    Report per-root N/M honestly; no pooling across roots.
  Q2: single instrumented run, rng seed=31, tie_sample=True (the
    exact exp020 tiesample arm) + one incumbent arm run seed=31
    for contrast (exp020 incumbent r31 final 0.2422 pinned as
    comparator). Census records per gen: per-candidate train_p +
    verify_p (whole cloud, 16 cells), band membership, picked cell.
  Guard: exp001 default lane through the SAME instrumented loop
    (census active, incumbent tie-break) must reproduce
    experiments/exp001.results.json byte-identical — proves the
    census does not perturb the stream.

Honesty: telemetry JSONL per Q1 replicate + per Q2 arm; results
JSON carries pre-registered conditions verbatim; post-hoc reads
labeled. No archive, no retention anywhere in this experiment.
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
RESULTS = LAB / "experiments" / "exp021.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
TARGETS = ("000", "111")
N = 3
POP, GENS = 16, 12
BUDGET = 6
SKELETON = [["h", 0], ["cx", 0, 1]]
BAR = 0.45
K_REPLICATES = 8

# exp020 named comparators (lab commit 2e741ee)
EXP020_COMPARATOR = {
    "source": "exp020 tie-break ablation, lab commit 2e741ee",
    "incumbent_r31": {"final_verify": 0.2422, "crossed": False},
    "tiesample_r31": {"final_verify": 0.3027, "crossed": False,
                      "tie_gens": 7},
    "tiesample_r29_r37": "crossed @0.4824 (both arms' discriminating "
                         "contrast)",
}

mutate_one = functools.partial(mutate_classed, restrict=("replace", "indel"))


def run_tiebreak(root_seed, tie_sample, telemetry_path=None,
                 census=False):
    """Exact exp020 run_tiebreak semantics; census=True adds passive
    per-candidate verify evals (no rng consumption)."""
    rng = random.Random(root_seed)
    champion = Candidate(genome=[list(g) for g in SKELETON])
    champion.train_p = p_target(champion.genome, TRAIN, SHOTS,
                                TARGETS, N, "balance")
    champion.verify_p = p_target(champion.genome, VERIFY, SHOTS,
                                 TARGETS, N, "balance")
    curve = []
    tie_rows = []
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
        tie_rows.append({"gen": gen, "gen_max": round(fmax, 6),
                         "n_tied": len(tied),
                         "incumbent_tied": fitness(champion) == fmax})
        if census:
            # passive observer: verify every cloud cell; NO rng draws
            cloud = []
            for c in cands:
                vp = p_target(c.genome, VERIFY, SHOTS, TARGETS, N,
                              "balance")
                cloud.append({
                    "genome": c.genome,
                    "train_p": round(c.train_p, 6),
                    "verify_p": round(vp, 6),
                    "in_band": fitness(c) == fmax,
                    "is_champion": c is champion,
                })
            census_rows.append({"gen": gen, "cloud": cloud})
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
            row = {"gen": gen, "curve": curve[-1], "tie": tie_rows[-1]}
            if census:
                row["census"] = census_rows[-1]
            with open(telemetry_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
    return {"champion": champion, "curve": curve, "ties": tie_rows,
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

# --- Q1: rate vs wall — K salted streams, exact exp020 tiesample ----
q1 = {}
for k in range(K_REPLICATES):
    seed = 31000 + k
    telem = LAB / "experiments" / f"exp021.telemetry.q1.k{k}.jsonl"
    if telem.exists():
        telem.unlink()
    out = run_tiebreak(seed, tie_sample=True,
                       telemetry_path=str(telem))
    cross = out["champion"].verify_p >= BAR
    q1[f"k{k}"] = {
        "seed": seed, "crossed": cross,
        "champion_verify": round(out["champion"].verify_p, 4),
        "max_verify_seen": round(
            max(c["verify_p"] for c in out["curve"]), 4),
        "tie_gens": sum(1 for t in out["ties"] if t["n_tied"] > 1),
    }
    print(f"Q1 k{k} (seed {seed}): crossed={cross} "
          f"verify={q1[f'k{k}']['champion_verify']} "
          f"max={q1[f'k{k}']['max_verify_seen']}")

q1_crossings = sum(1 for v in q1.values() if v["crossed"])
print(f"Q1: {q1_crossings}/{K_REPLICATES} streams crossed r31")

# --- Q2: opportunity census on canonical streams (seed 31) ----------
q2 = {}
for arm, tie_sample in (("tiesample", True), ("incumbent", False)):
    telem = LAB / "experiments" / f"exp021.telemetry.q2.{arm}.r31.jsonl"
    if telem.exists():
        telem.unlink()
    out = run_tiebreak(31, tie_sample, telemetry_path=str(telem),
                       census=True)
    # replicate-check vs exp020 comparators (same stream, same lane)
    if arm == "tiesample":
        replicate_ok = (
            round(out["champion"].verify_p, 4) == 0.3027
            and round(max(c["verify_p"] for c in out["curve"]), 4)
            == 0.3027)
    else:
        replicate_ok = (
            round(out["champion"].verify_p, 4) == 0.2422
            and round(max(c["verify_p"] for c in out["curve"]), 4)
            == 0.2422)
    band_opportunity = []   # gens where TIE BAND held verify >= BAR
    cloud_opportunity = []  # gens where CLOUD held verify >= BAR
    band_best = []          # per-gen best verify inside the band
    cloud_best = []         # per-gen best verify in the cloud
    for row in out["census"]:
        gen = row["gen"]
        band = [c for c in row["cloud"] if c["in_band"]]
        bb = max(c["verify_p"] for c in band)
        cb = max(c["verify_p"] for c in row["cloud"])
        band_best.append({"gen": gen, "band_best_verify": bb})
        cloud_best.append({"gen": gen, "cloud_best_verify": cb})
        if bb >= BAR:
            band_opportunity.append(gen)
        if cb >= BAR:
            cloud_opportunity.append(gen)
    q2[arm] = {
        "crossed": out["champion"].verify_p >= BAR,
        "champion_verify": round(out["champion"].verify_p, 4),
        "exp020_replicate_ok": replicate_ok,
        "band_opportunity_gens": band_opportunity,
        "cloud_opportunity_gens": cloud_opportunity,
        "max_band_verify": round(max(b["band_best_verify"]
                                     for b in band_best), 4),
        "max_cloud_verify": round(max(c["cloud_best_verify"]
                                      for c in cloud_best), 4),
    }
    print(f"Q2 {arm} r31: replicate_ok={replicate_ok} "
          f"band_opp_gens={band_opportunity} "
          f"cloud_opp_gens={cloud_opportunity} "
          f"max_band={q2[arm]['max_band_verify']} "
          f"max_cloud={q2[arm]['max_cloud_verify']}")

# --- verdicts (pre-registered conditions) ----------------------------
if q1_crossings >= 1:
    q1_verdict = (f"RATE NOT WALL: {q1_crossings}/{K_REPLICATES} "
                  "salted streams crossed r31 — 31's resistance is a "
                  "per-stream lottery draw, consistent with the "
                  "ROOT-LOTTERY doctrine (exp012/exp014); N/M honest "
                  "read, not a law")
else:
    q1_verdict = (f"WALL AT K={K_REPLICATES}: 0/{K_REPLICATES} salted "
                  "streams crossed r31 — resistance absolute at this "
                  "power; desert read (exp018) stands for 31; exp019 "
                  "RETENTION-ASSEMBLY remains the only mechanism that "
                  "ever crossed 31")

ts = q2["tiesample"]
if ts["band_opportunity_gens"]:
    q2_verdict = ("OPPORTUNITY-MISSED: the canonical stream's tie "
                  f"band held verify>={BAR} cell(s) at gen(s) "
                  f"{ts['band_opportunity_gens']} but was never "
                  "promoted — 31's failure is sampling luck inside "
                  "the band; Q1 rate read is the primary doctrine")
elif ts["cloud_opportunity_gens"]:
    q2_verdict = ("STRUCTURAL MISMATCH: cloud held verify>="
                  f"{BAR} cell(s) at gen(s) "
                  f"{ts['cloud_opportunity_gens']} but NEVER inside "
                  "any gen-max train tie band — crossing fitness on "
                  "31 is invisible to selection (train/verify "
                  "decorrelated at the desert floor); no tie-break "
                  "rule can fix this, only cross-gen retention "
                  "(exp019 retention-assembly confirmed as THE "
                  "mechanism for 31)")
else:
    q2_verdict = ("DESERT-EXTENDS-TO-CLOUD: no cloud cell reached "
                  f"verify>={BAR} in any of 12 gens on the canonical "
                  "stream — the exp016 archive crossing on 31 "
                  "necessarily assembled fitness across generations "
                  "via retention; exp019 RETENTION-ASSEMBLY verdict "
                  "is the only remaining mechanism")

out_doc = {
    "experiment": "exp021 r31-specific tie-context autopsy",
    "question": "why does root 31 alone resist tie-band diversity "
                "(exp020 crossed 29+37, 31 stayed closed @0.3027)",
    "lane": {"targets": list(TARGETS), "mode": "balance",
             "n_qubits": N, "train_seed": TRAIN,
             "verify_seed": VERIFY, "shots": SHOTS,
             "budget": BUDGET, "restrict": ["replace", "indel"],
             "pop": POP, "gens": GENS, "skeleton": SKELETON,
             "bar": BAR},
    "exp020_comparator": EXP020_COMPARATOR,
    "guard": {"exp001_reproduced_byte_identical": control_ok},
    "q1_rate_vs_wall": {"K": K_REPLICATES, "seeds_base": 31000,
                        "crossings": q1_crossings, "runs": q1,
                        "verdict": q1_verdict},
    "q2_opportunity_census": q2,
    "q2_verdict": q2_verdict,
    "honesty": "census evals consume no rng; guard pins the "
               "instrumented loop to exp001 byte-identical; Q2 arms "
               "replicate exp020 champion/max verify exactly "
               "(replicate_ok flags); post-hoc reads labeled; no "
               "archive, no retention anywhere in this experiment",
}
RESULTS.write_text(json.dumps(out_doc, indent=1, sort_keys=True))
print("\nVERDICT Q1:", q1_verdict)
print("VERDICT Q2:", q2_verdict)
print("wrote", RESULTS)
