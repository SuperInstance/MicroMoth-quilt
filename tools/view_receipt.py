#!/usr/bin/env python3
"""view_receipt.py — VIEW cells: "we looked" is itself receipted.

Implements the VIEW clause of docs/CELL-MAPPING.md ("The mapping"):

    VIEW — `simulate(qc, shots, get=...)` is literally a VIEW cell:
    `{args: {shots, get}}` over the circuit cell. `counts`,
    `statevector`, `probabilities_dict` are three views of the *same*
    circuit chain; the ledger records which view was taken, so "we
    looked at counts" is itself receipted and re-derivable.

So a VIEW cell names WHICH view was taken over WHICH circuit, and
carries the view's payload under the ledger's honesty rules:

- counts: sampling, so the determinism-hole doctrine applies exactly
  as in cell_receipts.WORLD — a seeded injected Random(seed) stream
  via simulate()'s step-3 seam; unseeded counts are REFUSED, not
  faked, and never laundered into a receipt. The histogram is small,
  so it is inlined (same precedent as WORLD).
- statevector / probabilities_dict: deterministic views of the same
  circuit chain. The payload is sha256-pinned — never inlined (the
  honest limit "the ledger is cheap, the VIEW is not"): statevector
  cost is 2**num_qubits amplitude pairs, so the ledger carries the
  digest + declared precision + shape, an auditor re-runs the view
  and compares digests.

Verify by replay, not by trust: verify_cell() re-runs the named view
against the presented circuit and compares payload; tamper is named,
never faked green. Cell algebra per collapse_ledger (five opcodes +
adopted set); a VIEW cell's id covers its args as minted, so the
record of "which view was taken" moves if anyone rewrites it.

Honest limits (kept from CELL-MAPPING.md):
- VIEW records the observation; it does not close the unseeded
  sampling hole — unseeded counts stay the named hole (refused here,
  same as WORLD).
- sugar ops never reach a ledger (state_witness refuses them at the
  witness layer; VIEW rides on the same circuit-chain discipline).
- the ledger is cheap, the VIEW is not: statevector digests are the
  mitigation, not a license to simulate big.

Run: python3 tools/view_receipt.py   (self-check: Bell views mint + verify)
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit, simulate  # noqa: E402  (baseline authority)

# collapse_ledger owns the canonical cell encoding + genesis constant;
# state_witness owns declared-precision amplitude encoding + fnv1a-64.
sys.path.insert(0, str(LAB / "tools"))
from collapse_ledger import GENESIS, _baseline_version, _canon, _cell  # noqa: E402
import state_witness  # noqa: E402

DIALECT = "micro-moth/view-receipt v1"
VIEWS = ("counts", "statevector", "probabilities_dict")
_PROB_PRECISION = 12  # decimal places for probability rounding (declared in cells)


def _round_prob(p: float) -> float:
    return round(float(p), _PROB_PRECISION)


def _prob_digest(probabilities: dict) -> str:
    """Canonical, declared-precision probability encoding — hash input."""
    canon = {bit: _round_prob(p) for bit, p in sorted(probabilities.items())}
    return hashlib.sha256(_canon(canon).encode("utf-8")).hexdigest()


def _counts(qc: QuantumCircuit, shots: int, seed: int) -> dict:
    """Seeded counts through simulate()'s injected-rng seam. Sealed-only:
    an unseeded prediction is refused, not faked (the named hole)."""
    if seed is None:
        raise ValueError(
            "VIEW refuses unseeded counts: unseeded sampling is the named "
            "determinism hole (CELL-MAPPING.md), never a receipt")
    if isinstance(seed, float) or (isinstance(seed, int) and seed < 0):
        raise ValueError("seed must be a non-negative int")
    if not isinstance(shots, int) or shots <= 0:
        raise ValueError("shots must be a positive int")
    counts = simulate(qc, shots=shots, get="counts", rng=random.Random(seed))
    return {bit: int(n) for bit, n in counts.items()}


def view_cell(qc: QuantumCircuit, view: str, prev: str = GENESIS,
              shots: int = None, seed: int = None,
              precision: int = state_witness.PRECISION) -> dict:
    """Mint one VIEW cell over the circuit chain ending at `prev`.

    args name the observation exactly:
    - counts: {view, circuit-version, num_qubits, shots, seed, histogram}
      (histogram small enough to inline — the WORLD precedent).
    - statevector: {view, circuit-version, num_qubits, precision,
      num_amplitudes, state_sha256} — payload digest-pinned, never inlined.
    - probabilities_dict: {view, circuit-version, num_qubits,
      prob_precision, num_outcomes, prob_sha256} — digest-pinned.
    """
    if view not in VIEWS:
        raise ValueError("unknown view %r; ledger views are %s" % (view, VIEWS))
    if not isinstance(qc, QuantumCircuit):
        raise ValueError("VIEW rides on a circuit chain, not %r" % type(qc))
    base = {
        "view": view,
        "circuit": "micro-moth:%s" % _baseline_version(),
        "num_qubits": qc.num_qubits,
    }
    if view == "counts":
        histogram = _counts(qc, shots, seed)
        args = dict(base, shots=shots, seed=seed, histogram=histogram)
    elif view == "statevector":
        sv = simulate(qc, get="statevector")
        args = dict(
            base,
            precision=precision,
            num_amplitudes=len(sv),
            state_sha256=hashlib.sha256(
                state_witness.state_digest(sv, precision).encode("utf-8")
            ).hexdigest(),
        )
    else:  # probabilities_dict
        pd = simulate(qc, get="probabilities_dict")
        args = dict(
            base,
            prob_precision=_PROB_PRECISION,
            num_outcomes=len(pd),
            prob_sha256=_prob_digest(pd),
        )
    return _cell("VIEW", prev, args)


def verify_cell(cell: dict, qc: QuantumCircuit) -> dict:
    """Re-derive the cell id and replay the named view; compare payload.

    Never trusts the presented digest alone: the view is re-run and the
    digest recomputed from live output. Tamper is named, not faked.
    """
    if cell.get("op") != "VIEW":
        return {"ok": False, "why": "not_a_view_cell"}
    args = cell.get("args", {})
    body = {"op": "VIEW", "prev": cell["prev"], "args": args}
    want = "0x%016x" % state_witness.fnv1a64(_canon(body))
    if cell.get("id") != want:
        return {"ok": False, "why": "id_mismatch"}
    view = args.get("view")
    if view not in VIEWS:
        return {"ok": False, "why": "unknown_view"}
    if args.get("circuit") != "micro-moth:%s" % _baseline_version():
        return {"ok": False, "why": "circuit_version_divergence"}
    if args.get("num_qubits") != qc.num_qubits:
        return {"ok": False, "why": "num_qubits_divergence"}
    if view == "counts":
        if sum(args.get("histogram", {}).values()) != args.get("shots"):
            return {"ok": False, "why": "histogram_sums_wrong"}
        rerun = _counts(qc, args["shots"], args["seed"])
        if rerun != args["histogram"]:
            return {"ok": False, "why": "counts_divergence"}
    elif view == "statevector":
        sv = simulate(qc, get="statevector")
        if args.get("num_amplitudes") != len(sv):
            return {"ok": False, "why": "amplitude_count_divergence"}
        digest = hashlib.sha256(
            state_witness.state_digest(sv, args["precision"]).encode("utf-8")
        ).hexdigest()
        if digest != args.get("state_sha256"):
            return {"ok": False, "why": "state_digest_divergence"}
    else:  # probabilities_dict
        pd = simulate(qc, get="probabilities_dict")
        if args.get("num_outcomes") != len(pd):
            return {"ok": False, "why": "outcome_count_divergence"}
        if _prob_digest(pd) != args.get("prob_sha256"):
            return {"ok": False, "why": "prob_digest_divergence"}
    return {"ok": True, "why": "ok"}


def _selfcheck() -> int:
    """Bell-state views: mint each view, chain them, verify by replay."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)

    c_counts = view_cell(qc, "counts", shots=64, seed=42)
    c_sv = view_cell(qc, "statevector", prev=c_counts["id"])
    c_pd = view_cell(qc, "probabilities_dict", prev=c_sv["id"])

    for name, cell in (("counts", c_counts), ("statevector", c_sv),
                       ("probabilities", c_pd)):
        v = verify_cell(cell, qc)
        print("%s view: %s (%s)" % (name, "ok" if v["ok"] else "FAIL", v["why"]))
        if not v["ok"]:
            return 1

    # chain discipline: the three observations are linked cells
    assert c_sv["prev"] == c_counts["id"]
    assert c_pd["prev"] == c_sv["id"]

    # determinism at the digest layer: re-mint is byte-identical
    again = view_cell(qc, "statevector")
    assert again == view_cell(qc, "statevector")
    print("self-check ok: views mint, chain, verify by replay")
    return 0


if __name__ == "__main__":
    sys.exit(_selfcheck())
