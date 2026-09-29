"""exp013 — curriculum: 2-qubit Bell balance BEFORE n=3 (multi-root at birth).

exp012 doctrine (VERIFIED): any 'unaided crossing' claim needs multi-root
replication by design; seeding/curriculum is the only REPLICATED
crossing class (exp006 n=3, exp007 n=2, exp008 n=4). exp013 tests the
last unreplicated crossing-class idea: CURRICULUM — solve the cheap
entangled problem first (2-qubit Bell balance, exp007's home turf),
then TRANSPLANT the earned champion as the birth seed of the n=3 GHZ
balance lane (exp005's frozen home problem).

Design pinned BEFORE running (anti-laundering):
  Phase 1 (per root): Bell balance curriculum, targets ("01","10"),
    n_qubits=2, mode="balance", seeded with the exp007 prescription
    [["h",0],["cx",0,1]] (zero fitness, one x insert from psi+).
    Success bar: held-out verify >= 0.45 (same bar as exp006/007).
  Transplant rule (pinned, deterministic): the phase-1 champion is
    mapped op-for-op onto qubits {0,1} of the 3-qubit encoding; qubit
    index references unchanged; the new qubit 2 enters as |0>. The
    transplant therefore births a REAL correlated state (psi on q0,q1
    tensor |0>) whose balance vs ("000","111") is 0.0 — zero-fitness
    structural prefix, earned by solving the smaller problem, never
    hand-built for the bigger one.
    If phase 1 does NOT cross, the transplant is recorded as NO-OP
    (curriculum failed before it started) — never silently replaced.
  Phase 2 (per root): three n=3 lanes on the exact exp005 lane
    (targets ("000","111"), jitter-dropped restrict=("replace","indel"),
    pop 16, 12 gens):
      curriculum  — phase-1 champion transplanted per the rule above
      unaided     — random 3-gate birth (exp005 freeze control)
    Success bar: held-out verify balance >= 0.45.
  Multi-root at birth per exp012 doctrine: roots 7, 11, 23, 42
  (the exp012 root set; root 7 is the historical one).
The exp001 reproduction guard runs the default 2-qubit lane in-harness
per root before any results are written.
"""
import functools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qcell.search import mutate_classed, run_search

LAB = Path(__file__).resolve().parent.parent
RESULTS = LAB / "experiments" / "exp013.results.json"
EXP001 = LAB / "experiments" / "exp001.results.json"

TRAIN, VERIFY, SHOTS = 101, 202, 512
ROOTS = (7, 11, 23, 42)
BELL_TARGETS = ("01", "10")
GHZ_TARGETS = ("000", "111")
CURRICULUM_SEED = [["h", 0], ["cx", 0, 1]]
BAR = 0.45

mutate_fn = functools.partial(mutate_classed, restrict=("replace", "indel"))
exp001 = json.loads(EXP001.read_text())

def guard(root):
    # exp001's canonical curve was produced at ROOT SEED 7; the guard
    # re-runs THAT lane (like exp005-012), not a per-root variant.
    telem = LAB / "experiments" / f"exp013.telemetry.guard.jsonl"
    if telem.exists():
        telem.unlink()
    res = run_search(7, generations=8, pop=16, shots=SHOTS,
                     train_seed=TRAIN, verify_seed=VERIFY,
                     telemetry_path=str(telem))
    ok = (res["curve"] == exp001["curve"]
          and res["champion"].genome == exp001["champion_genome"])
    print(f"guard r{root} reproduces exp001:", ok)
    return ok

def run(root, name, targets, n_qubits, seed_genome, gens=12):
    telem = LAB / "experiments" \
        / f"exp013.telemetry.r{root}.{name}.jsonl"
    if telem.exists():
        telem.unlink()
    return run_search(root, generations=gens, pop=16, shots=SHOTS,
                      train_seed=TRAIN, verify_seed=VERIFY,
                      telemetry_path=str(telem), mutate_fn=mutate_fn,
                      targets=targets, n_qubits=n_qubits,
                      mode="balance", seed_genome=seed_genome)

def transplant_to_n3(genome):
    """Pinned rule: phase-1 Bell champion on qubits {0,1} mapped
    op-for-op; indices unchanged; qubit 2 enters as |0>."""
    return [list(g) for g in genome]

roots_out = {}
for root in ROOTS:
    if not guard(root):
        print(f"FATAL: exp013 harness changed default behavior at "
              f"root {root}; refusing to write results")
        sys.exit(1)

    # phase 1: Bell curriculum (seeded per exp007 prescription)
    p1 = run(root, "phase1_bell", BELL_TARGETS, 2, CURRICULUM_SEED)
    p1_cross = p1["champion"].verify_p >= BAR
    print(f"r{root} phase1 Bell: champion={json.dumps(p1['champion'].genome)}"
          f" verify={p1['champion'].verify_p:.4f} crossed={p1_cross}")

    phase2 = {}
    if p1_cross:
        # curriculum lane: transplant the EARNED champion
        seed = transplant_to_n3(p1["champion"].genome)
        res = run(root, "phase2_curriculum", GHZ_TARGETS, 3, seed)
        c = res["champion"]
        phase2["curriculum"] = {
            "seed_genome": seed,
            "champion_genome": c.genome,
            "champion_verify_p": c.verify_p,
            "first_ge_045_gen": next(
                (r["gen"] for r in res["curve"]
                 if r["verify_p"] >= BAR), None),
            "curve": res["curve"],
        }
        print(f"r{root} curriculum: champion={json.dumps(c.genome)} "
              f"verify={c.verify_p:.4f}")
    else:
        phase2["curriculum"] = {"skipped": "phase 1 did not cross"}

    # unaided control on the exact exp005 lane
    res = run(root, "phase2_unaided", GHZ_TARGETS, 3, None)
    c = res["champion"]
    phase2["unaided"] = {
        "champion_genome": c.genome,
        "champion_verify_p": c.verify_p,
        "first_ge_045_gen": next(
            (r["gen"] for r in res["curve"] if r["verify_p"] >= BAR),
            None),
        "curve": res["curve"],
    }
    print(f"r{root} unaided: verify={c.verify_p:.4f}")

    roots_out[str(root)] = {
        "phase1_crossed": p1_cross,
        "phase1_champion": p1["champion"].genome,
        "phase1_champion_verify_p": p1["champion"].verify_p,
        "phase2": phase2,
    }

out = {
    "seeds": {"train": TRAIN, "verify": VERIFY, "shots": SHOTS,
              "roots": list(ROOTS)},
    "design": {
        "curriculum_seed": CURRICULUM_SEED,
        "transplant_rule": "phase-1 Bell champion mapped op-for-op onto "
                           "qubits {0,1}; indices unchanged; qubit 2 "
                           "enters as |0>",
        "multi_root_doctrine": "exp012: any crossing claim needs 2+ "
                               "roots agreeing",
        "success_bar_verify_balance": BAR,
        "policy": "restrict=('replace','indel') jitter-dropped",
    },
    "roots": roots_out,
}
RESULTS.write_text(json.dumps(out, indent=2, sort_keys=True))
print("results -> experiments/exp013.results.json")
