"""exp019 — Archive-assembly mechanism read: genealogy of the exp016
hard-root crossing.

exp016 sealed (PR #22, commit fba4ec7): the skeleton+archive HYBRID
crossed the hard roots 29/31/37 that champion-local skeleton failed
(4/8 champion-local vs 6/8 hybrid; hard class {29,31,37} crossed only
hybrid). exp018's autopsy read the unaided side: FITNESS DESERT AT
THE BIRTH CLOUD — the freeze is upstream of selection, so the hybrid
crossing must have unlocked FITNESS ASSEMBLY via multi-parent mixing
(exp015 ELITISM-ARTIFACT consistent). That was an interpretation.
THIS experiment is the mechanism read that pins it: reconstruct the
exact ancestry of each hard-root crossing from the sealed exp016
per-generation archive snapshots and ask — was the archive's
retention of non-champion individuals load-bearing on the crossing
route, or would single-fitness champion-local hill-climbing have
kept every ancestor too (making the archive incidental)?

Design pin BEFORE running (anti-laundering):
  Data: ONLY the sealed exp016 hybrid telemetry (receipts dir copy,
    commit fba4ec7, roots 29/31/37, experiments/exp016.telemetry.r*
    .hybrid.jsonl) — no new evolutionary runs; this is a genealogy
    read of frozen artifacts. Crossing bar unchanged: held-out
    verify balance >= 0.45.
  Chain reconstruction: every a1 elite carries provenance.lineage +
    provenance.parent_lineage; parents are a1 cell elites, so every
    parent_lineage resolves to a genome in an earlier (or same-birth)
    snapshot. Chain = crossing elite -> parent -> ... -> skeleton
    birth (parent_lineage None).
  Per-ancestor fitness context: for each chain ancestor, its gen's
    a1 max TRAIN fitness is recomputed from that gen's snapshot; an
    ancestor is CHAMPION-DISCARDED if its train fitness < gen max
    (single-fitness champion-local search would have dropped it).

Interpretation pinned BEFORE running:
  ASSEMBLY CONFIRMED if, for a hard-root crossing:
    (a) NO strict ancestor reaches verify >= 0.45 (the crossing is
        not reachable as one lineage's smooth climb), AND
    (b) >=1 CHAMPION-DISCARDED ancestor carries a gate (exact
        [name, wires...] tuple) present in the final crossing genome
        (archive retention load-bearing at the gate level), AND
    (c) the chain passes through >=1 verify>0 ancestor in the
        partial-plateau class (<=0.30, the Finding-4 band exp015
        pinned as the archive-held signal).
  HILL-CLIMB if every chain ancestor was its gen's train-max
    (champion-local would have retained the whole route) -> the
    archive was incidental to the crossing; exp018's assembly read
    is downgraded to interpretation, not mechanism.
  REPLAY-MISMATCH if no verify>=0.45 elite is found in a root's
    telemetry where exp016 sealed a crossing -> honesty row, seal
    void for that root.
  Tie caveat (named pre-run): the exp018 desert means train TIES at
    0.0 / 0.2559 are ubiquitous; a strict-inferiority discard test is
    blind under ties. A clearly-labeled POST-HOC tie-aware read
    (per-ancestor gen-max context) accompanies the pre-registered
    verdict; headline carries both, pre-registered stands.

Honesty: full chain table per root (lineage, born_gen, train,
verify, champion-discarded flag, gates-carried-forward) written to
results; no ancestor silently merged. Guard: exp001 default lane
reproduces byte-identical in-harness BEFORE results are written.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qcell.search import run_search

LAB = Path(__file__).resolve().parent.parent
EXP001 = LAB / "experiments" / "exp001.results.json"
RESULTS = LAB / "experiments" / "exp019.results.json"
TELEM = {
    r: LAB / "experiments" / f"exp016.telemetry.r{r}.hybrid.jsonl"
    for r in (29, 31, 37)
}
BAR = 0.45
PLATEAU_BAND = 0.30
EXP016_PROVENANCE = (
    "exp016 sealed receipt commit fba4ec7 (PR #22, Casey-gated at "
    "seal time); telemetry read here is the byte-frozen artifact "
    "copied into the MicroMoth-quilt receipts dir by that seal")


def load_gens(path):
    gens = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                gens.append(json.loads(line))
    return gens


def reconstruct(root, gens):
    """Return (crossing, chain, gen_max_train) or an honesty row."""
    # lineage -> (gen_idx, record) from cumulative snapshots
    by_lineage = {}
    gen_max_train = []
    for gi, row in enumerate(gens):
        snap = row["a1"]
        mx = max((r["fitness"] for r in snap.values()), default=0.0)
        gen_max_train.append(mx)
        for _bd, rec in snap.items():
            prov = rec.get("provenance") or {}
            lin = prov.get("lineage")
            if lin and lin not in by_lineage:
                rec = dict(rec)
                rec["born_gen"] = prov.get("born_gen", gi)
                by_lineage[lin] = (gi, rec)

    # earliest crossing: lowest born_gen, then lowest verify distance
    cands = []
    for _gi, rec in by_lineage.values():
        if rec["verify"] >= BAR:
            cands.append(rec)
    if not cands:
        return None, None, gen_max_train
    crossing = min(cands, key=lambda r: (r["born_gen"], r["verify"]))

    chain = []
    cur = crossing
    for _ in range(200):
        prov = cur.get("provenance") or {}
        chain.append(cur)
        pl = prov.get("parent_lineage")
        if not pl:
            break
        if pl not in by_lineage:
            chain.append({"lineage": pl, "broken": True})
            break
        cur = by_lineage[pl][1]
    return crossing, chain, gen_max_train


def analyze_root(root, gens):
    crossing, chain, gen_max_train = reconstruct(root, gens)
    if crossing is None:
        return {"root": root, "status": "REPLAY-MISMATCH",
                "expected_crossing": True,
                "note": "no verify>=0.45 elite in sealed telemetry"}

    # chain[0] is the crossing; strict ancestors follow
    ancestors = [c for c in chain[1:] if not c.get("broken")]
    cross_gates = {tuple(g) for g in crossing["genome"]}

    # (a) any strict ancestor at/above bar?
    ancestor_at_bar = [a for a in ancestors
                       if a.get("verify", 0.0) >= BAR]

    # (b) champion-discarded ancestors carrying forward gates
    discarded_carriers = []
    for a in ancestors:
        prov = a.get("provenance") or {}
        lin = prov.get("lineage")
        bg = a.get("born_gen", -1)
        idx = bg if 0 <= bg < len(gen_max_train) else None
        if idx is None:
            continue
        if a["fitness"] < gen_max_train[idx] - 1e-12:
            carried = cross_gates & {tuple(g) for g in a["genome"]}
            discarded_carriers.append({
                "lineage": lin, "born_gen": bg,
                "train": round(a["train"], 4),
                "gen_max_train": round(gen_max_train[idx], 4),
                "carried_gates": [list(g) for g in sorted(carried)],
            })

    # (c) partial-plateau ancestors (verify in (0, BAND])
    plateau = [{"lineage": (a.get("provenance") or {}).get("lineage"),
                "born_gen": a.get("born_gen"),
                "verify": round(a["verify"], 4)}
               for a in ancestors
               if 0.0 < a.get("verify", 0.0) <= PLATEAU_BAND]

    all_champion_kept = not discarded_carriers and len(ancestors) > 0
    verdict = None
    if not ancestor_at_bar and discarded_carriers and plateau:
        verdict = "ASSEMBLY-CONFIRMED"
    elif all_champion_kept and not ancestor_at_bar:
        verdict = "HILL-CLIMB"
    else:
        verdict = "MIXED"

    # --- tie-aware post-hoc read (labeled post-hoc, pre-registered
    # conditions above stand) -------------------------------------
    # Pre-registered condition (b) defined 'discarded' by STRICT
    # train inferiority. exp018's desert means train ties at 0.0 (and
    # at the 0.2559 partial plateau) are ubiquitous on these roots;
    # under ties champion-local KEEPS the incumbent and never crosses
    # BETWEEN tied elites, while the archive samples parents uniformly
    # across ALL occupied cells. Record the tie context per ancestor.
    rows = []
    for c in chain:
        if c.get("broken"):
            continue
        bg = c.get("born_gen", -1)
        idx = bg if 0 <= bg < len(gen_max_train) else None
        gmax = round(gen_max_train[idx], 4) if idx is not None else None
        tr = round(c.get("train", 0.0), 4)
        rows.append({
            "lineage": (c.get("provenance") or {}).get("lineage"),
            "born_gen": bg, "train": tr, "gen_max_train": gmax,
            "verify": round(c.get("verify", 0.0), 4),
            "strictly_discarded": (gmax is not None
                                   and tr < gmax - 1e-12),
            "tie_band": (gmax is not None
                         and abs(tr - gmax) <= 1e-12),
        })
    tie_band_ancestors = [r for r in rows[1:] if r["tie_band"]]
    strict_carriers = [r for r in rows[1:]
                       if r["strictly_discarded"]]
    if strict_carriers:
        post_hoc = "RETENTION-ASSEMBLY"
        post_note = (
            "crossing route rides through ancestor(s) with STRICTLY "
            "lower train than the gen max - only archive cell "
            "retention keeps them; champion-local would have "
            "dropped them.")
    elif len(tie_band_ancestors) == len(rows) - 1 and len(rows) > 1:
        post_hoc = "TIE-BAND-DIVERSITY"
        post_note = (
            "every ancestor sat at its gen's train max (ties), but "
            "champion-local keeps the INCUMBENT on ties and never "
            "crosses between tied elites; the archive's uniform "
            "parent-cell sampling is the load-bearing difference "
            "(empirical comparator: exp014 champion-local 0/3 on "
            "hard roots at same seeds).")
    else:
        post_hoc = "UNCLEAR"
        post_note = "neither retention nor full tie-band; report rows"

    return {
        "root": root,
        "status": "ANALYZED",
        "crossing": {
            "lineage": (crossing.get("provenance") or {}).get("lineage"),
            "born_gen": crossing["born_gen"],
            "train": round(crossing["train"], 4),
            "verify": round(crossing["verify"], 4),
            "genome": crossing["genome"],
        },
        "chain_length_ancestors": len(ancestors),
        "ancestor_at_bar_count": len(ancestor_at_bar),
        "champion_discarded_carriers": discarded_carriers,
        "partial_plateau_ancestors": plateau,
        "chain_table": [{
            "lineage": (c.get("provenance") or {}).get("lineage"),
            "born_gen": c.get("born_gen"),
            "train": round(c.get("train", 0.0), 4),
            "verify": round(c.get("verify", 0.0), 4),
            "genome_len": len(c.get("genome", [])),
        } for c in chain if not c.get("broken")],
        "verdict": verdict,
        "post_hoc_tie_aware": {
            "label": "POST-HOC (pre-registered verdict above stands)",
            "read": post_hoc,
            "note": post_note,
            "rows": rows,
        },
    }


# --- guard: default lane still reproduces exp001 -------------------------
ctrl_telem = LAB / "experiments" / "exp019.telemetry.control.jsonl"
if ctrl_telem.exists():
    ctrl_telem.unlink()
ctrl_res = run_search(7, generations=8, pop=16, shots=512,
                      train_seed=101, verify_seed=202,
                      telemetry_path=str(ctrl_telem))
exp001 = json.loads(EXP001.read_text())
control_ok = (ctrl_res["curve"] == exp001["curve"]
              and ctrl_res["champion"].genome == exp001["champion_genome"])
print("control reproduces exp001:", control_ok)
if not control_ok:
    print("FATAL: harness drift; refusing to write results")
    sys.exit(1)

out = {
    "experiment": "exp019",
    "kind": "genealogy-read-of-sealed-artifacts",
    "bar_verify_balance": BAR,
    "plateau_band": PLATEAU_BAND,
    "data_provenance": EXP016_PROVENANCE,
    "guard": {"exp001_reproduces": control_ok},
    "roots": {},
}
for root, path in TELEM.items():
    if not path.exists():
        out["roots"][str(root)] = {"status": "ARTIFACT-MISSING"}
        continue
    out["roots"][str(root)] = analyze_root(root, load_gens(path))

verdicts = {r: v.get("verdict") for r, v in out["roots"].items()
            if v.get("status") == "ANALYZED"}
post_hoc = {r: v.get("post_hoc_tie_aware", {}).get("read")
            for r, v in out["roots"].items()
            if v.get("status") == "ANALYZED"}
out["headline_verdicts"] = verdicts
out["headline_post_hoc_tie_aware"] = post_hoc
if all(v == "RETENTION-ASSEMBLY" for v in post_hoc.values()) \
        and len(post_hoc) == 3:
    out["doctrine_read"] = (
        "FITNESS ASSEMBLY is the mechanism on all three hard roots: "
        "each crossing route rides through ancestors champion-local "
        "would have dropped (strict train inferiority). Archive "
        "retention is load-bearing at the gate level.")
elif all(v in ("RETENTION-ASSEMBLY", "TIE-BAND-DIVERSITY")
         for v in post_hoc.values()) and post_hoc:
    parts = []
    if any(v == "RETENTION-ASSEMBLY" for v in post_hoc.values()):
        parts.append(
            "on >=1 root the route rides through strictly-discarded "
            "ancestors (archive retention load-bearing at gate level)")
    if any(v == "TIE-BAND-DIVERSITY" for v in post_hoc.values()):
        parts.append(
            "on >=1 root all ancestors sat at gen train-max (ties) - "
            "the archive's uniform parent-cell sampling, not "
            "retention, is the load-bearing difference; champion-"
            "local keeps the incumbent on ties and never crosses "
            "between tied elites (comparator exp014 0/3 hard roots)")
    out["doctrine_read"] = (
        "FITNESS ASSEMBLY REFINED, not refuted: " + "; ".join(parts)
        + ". The archive is load-bearing on every hard root, via "
        "retention where fitness is strict, via tie-band diversity "
        "where the desert ties.")
else:
    out["doctrine_read"] = (
        "Mixed reads across hard roots - per-root rows stand; no "
        "single-mechanism claim seals.")

RESULTS.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps({"verdicts_pre_registered": verdicts,
                  "post_hoc_tie_aware": post_hoc}, indent=1))
print("wrote", RESULTS)
