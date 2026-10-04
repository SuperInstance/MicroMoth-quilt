#!/usr/bin/env python3
"""midcircuit_boundary.py — close a witness boundary AT a mid-circuit measurement.

The seam (witness_collapse_seam.py) welds collapse outcomes to the state
after the LAST unitary moment — end-of-circuit semantics. Real hardware
does something strictly harder: a measurement MID-circuit collapses the
state and the gates after it act on the COLLAPSED state, conditioned on
the declared outcome. This tool closes that boundary honestly:

    LINK -> TICK* (pre-boundary moments) -> PROOF (boundary state)
         -> EFFECT (declared boundary outcome, seeded)
         -> INIT-STATE (projected + renormalized collapsed statevector)
         -> TICK* (post-boundary moments) -> PROOF (final state)

Conventions (declared, replayed by verify(), never trusted):
- The boundary is the index of ONE 'm' gate in qc.data. Exactly one
  measurement op per circuit is v1 scope: multiple mid-circuit
  collapses are refused, not silently linearized (CELL-MAPPING.md
  honesty rule — refuse what you cannot witness).
- The outcome is sampled ONCE, seeded, from the boundary state's
  qubit probability (collapse_ledger doctrine: the seed IS the EFFECT
  parameter; unsealed outcomes are refused, never laundered).
- Collapse math: project onto the outcome subspace, normalize at full
  precision, round to the declared precision, renormalize the rounded
  values. Residual drift is O(precision^-1) and documented, not hidden.
- Post-boundary gates act on the collapsed state (that is the whole
  point of the tool). verify() replays them from the INIT-STATE hash's
  preimage recomputed by the same projection — recomputation, not trust.

Honest limits (kept):
- sugar ops never reach a ledger (refused, as everywhere in this lane).
- a boundary with no executable op after it is refused: plain
  tick_witnesses / the seam already cover end-of-circuit measurement
  honestly; closing a boundary nobody crosses is ceremony.
- 'init' mid-circuit is refused (replay ambiguity).

Run: python3 tools/midcircuit_boundary.py   (self-check, prints a receipt)
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

from micromoth import QuantumCircuit  # noqa: E402  (baseline authority)

sys.path.insert(0, str(LAB / "tools"))
# Same-package private imports, the established pattern (the seam
# imports both lanes' helpers; this tool composes the same machinery).
from collapse_ledger import GENESIS, _baseline_version, _canon, _cell  # noqa: E402
from state_witness import (  # noqa: E402
    PRECISION, _apply, _qubits_of, layers, state_digest, state_hash,
)

DIALECT = "micro-moth/midcircuit-boundary v1"
PROB_DIGITS = 6  # declared rounding for pinned outcome probabilities


class _Data:
    """Duck-type wrapper: layers() reads only .data (state_witness)."""

    def __init__(self, data):
        self.data = data


def _run_moments(gates, n, init_k):
    """Apply gate moments to a kernel copy; returns the final kernel.

    Kernels and loop order come from state_witness verbatim (port rule 8:
    fp addition is not associative — identical op sequence is the only
    honest parity claim)."""
    k = [list(e) for e in init_k]
    for moment in layers(_Data(gates)):
        for gate in moment:
            _apply(k, gate, n)
    return k


def _zero_state(n):
    k = [[0.0, 0.0] for _ in range(2 ** n)]
    k[0] = [1.0, 0.0]
    return k


def _qubit_prob(k, n, q, bit):
    return sum(c[0] ** 2 + c[1] ** 2
               for i, c in enumerate(k) if ((i >> q) & 1) == bit)


def _collapse(k, n, q, outcome, precision=PRECISION):
    """Project onto the outcome subspace, normalize, round, renormalize.

    Returns (collapsed_kernel, p_outcome_full_precision)."""
    ob = int(outcome)
    p = _qubit_prob(k, n, q, ob)
    if p <= 0:
        raise ValueError(
            "declared outcome %r has zero probability on the boundary state "
            "— a forced collapse is not a sample, refuse rather than launder" % outcome)
    s = p ** 0.5
    nk = [[c[0] / s, c[1] / s] if ((i >> q) & 1) == ob else [0.0, 0.0]
          for i, c in enumerate(k)]
    nk = [[round(c[0], precision), round(c[1], precision)] for c in nk]
    s2 = sum(c[0] ** 2 + c[1] ** 2 for c in nk) ** 0.5
    nk = [[c[0] / s2, c[1] / s2] for c in nk]
    return nk, p


def _sample_outcome(p_zero, seed):
    """One seeded draw against P(0); collapse_ledger seed doctrine.

    Draws from an injected `random.Random(seed)` instead of the retired
    seed/run/restore global plumbing (CELL-MAPPING.md step-3 adoption):
    the fresh Random(seed) stream is the same MT19937 sequence the
    module-global RNG draws after random.seed(seed), so outcomes are
    byte-identical, and receipt lanes no longer mutate global state."""
    draw = random.Random(seed).random()
    return "0" if draw < p_zero else "1"


def midcircuit_receipt(qc: QuantumCircuit, boundary: int, seed: int,
                       precision: int = PRECISION) -> dict:
    """Mint the mid-circuit boundary chain. See module docstring."""
    if seed is None or isinstance(seed, bool) or isinstance(seed, float) or \
            (isinstance(seed, int) and seed < 0):
        raise ValueError(
            "midcircuit v1 requires a sealed boundary (seed: non-negative int); "
            "EFFECT/UNSEALED must not hide behind a witnessed boundary")
    data = qc.data
    if not isinstance(boundary, int) or boundary < 1 or boundary >= len(data):
        raise ValueError("boundary must be the qc.data index of a measurement gate")
    if data[boundary][0] != "m":
        raise ValueError("boundary gate %r is not a measurement op" % (data[boundary],))
    ms = [i for i, g in enumerate(data) if g[0] == "m"]
    if len(ms) != 1:
        raise ValueError(
            "midcircuit v1 closes exactly one boundary; %d measurement ops found "
            "(multiple mid-circuit collapses are refused, not linearized)" % len(ms))
    if data[0][0] == "init" and any(g[0] == "init" for g in data[1:]):
        raise ValueError("init may appear at qc.data[0] at most once")
    if any(g[0] == "init" for g in data[1:boundary]):
        raise ValueError("init inside the pre-boundary segment is replay-ambiguous; refused")
    if any(g[0] == "init" for g in data[boundary + 1:]):
        raise ValueError(
            "init after the boundary would silently discard the collapsed state "
            "(_apply replaces the whole kernel) — refused, not laundered")
    seg1, seg2 = data[:boundary], data[boundary + 1:]
    if not any(g[0] not in ("m", "init") for g in seg2):
        raise ValueError(
            "no executable op after the boundary — end-of-circuit measurement "
            "is the seam's honest territory; closing an uncrossed boundary is ceremony")

    n = qc.num_qubits
    bgate = data[boundary]
    # Pre-boundary witness: reuse tick_witnesses on the sliced gate list
    # for the LINK+TICK chain, AND extract the boundary kernel for the
    # collapse (kernels via _run_moments, the same _apply sequence).
    from state_witness import tick_witnesses  # local: keeps top import small
    qc1 = _Data(seg1)
    qc1.num_qubits = n
    w1 = tick_witnesses(qc1, proof_at=-1, precision=precision)
    boundary_k = _run_moments(seg1, n, _zero_state(n))
    w1_ticks = [c for c in w1["cells"] if c["op"] == "TICK"]
    if not w1_ticks or w1_ticks[-1]["args"]["state_hash"] != state_hash(boundary_k, precision):
        raise AssertionError("internal: kernel extraction diverged from tick_witnesses")

    p_zero = _qubit_prob(boundary_k, n, bgate[1], 0)
    if not (0.0 < p_zero < 1.0):
        raise ValueError(
            "degenerate boundary distribution (P(0)=%r) — nothing is collapsed "
            "by a forced outcome; refuse rather than mint ceremony" % p_zero)
    outcome = _sample_outcome(p_zero, seed)
    p_out = p_zero if outcome == "0" else 1.0 - p_zero
    collapsed, _p = _collapse(boundary_k, n, bgate[1], outcome, precision)

    # EFFECT pins the probability it was sampled FROM (declared rounding).
    effect = _cell("EFFECT", w1["cells"][-1]["id"], {
        "kind": "midcircuit-collapse", "qubit": bgate[1], "clbit": bgate[2],
        "outcome": outcome, "prob": round(p_out, PROB_DIGITS), "seed": seed,
    })
    init_state = _cell("INIT-STATE", effect["id"], {
        "state_sha256": hashlib.sha256(
            state_digest(collapsed, precision).encode()).hexdigest(),
        "precision": precision, "encoding": "canonical-rounded-pairs",
        "source": "boundary-collapse projection+renormalization",
    })

    # Post-boundary moments continue the ticker from the collapsed state.
    cells = list(w1["cells"]) + [effect, init_state]
    prev = init_state["id"]
    ticker = len(w1_ticks)
    k = collapsed
    moms2 = layers(_Data(seg2))
    for mi, moment in enumerate(moms2):
        for gate in moment:
            _apply(k, gate, n)
        ticker += 1
        c = _cell("TICK", prev, {"ticker": ticker, "moment": mi,
                                 "qubits": sorted(set().union(*[_qubits_of(g) for g in moment])),
                                 "gates": len(moment),
                                 "state_hash": state_hash(k, precision)})
        cells.append(c)
        prev = c["id"]
    final_proof = _cell("PROOF", prev, {
        "tick": ticker, "precision": precision,
        "state_sha256": hashlib.sha256(state_digest(k, precision).encode()).hexdigest(),
        "encoding": "canonical-rounded-pairs",
    })
    cells.append(final_proof)

    return {
        "dialect": DIALECT,
        "witness_dialect": w1["dialect"],
        "micromoth_version": _baseline_version(),
        "precision": precision,
        "boundary": boundary,
        "outcome": outcome,
        "boundary_state_hash": w1_ticks[-1]["args"]["state_hash"],
        "final_state_hash": state_hash(k, precision),
        "cells": cells,
    }


def verify(receipt: dict, qc: QuantumCircuit = None) -> dict:
    """Chain integrity + full replay: boundary state, seeded outcome,
    collapsed state, post-boundary ticks. Tamper -> named failure."""
    from collapse_ledger import fnv1a64  # local: keeps top import small
    cells = receipt["cells"]
    prev = GENESIS
    for i, c in enumerate(cells):
        body = {"op": c["op"], "prev": c["prev"], "args": c["args"]}
        want = "0x%016x" % fnv1a64(_canon(body))
        if c["id"] != want:
            return {"ok": False, "why": "id_mismatch@%d" % i}
        if c["prev"] != prev:
            return {"ok": False, "why": "chain_break@%d" % i}
        prev = c["id"]
    ops = [c["op"] for c in cells]
    if ops.count("EFFECT") != 1 or ops.count("INIT-STATE") != 1:
        return {"ok": False, "why": "boundary_shape"}
    ei = ops.index("EFFECT")
    ii = ops.index("INIT-STATE")
    if ii != ei + 1:
        return {"ok": False, "why": "initstate_not_welded"}
    if not any(o == "TICK" for o in ops[ii + 1:]):
        return {"ok": False, "why": "no_post_boundary_ticks"}
    if qc is None:
        return {"ok": True, "why": "ok"}
    # Replay against the actual circuit.
    boundary = receipt.get("boundary")
    data = qc.data
    if not isinstance(boundary, int) or boundary < 1 or boundary >= len(data) \
            or data[boundary][0] != "m":
        return {"ok": False, "why": "boundary_record_divergence"}
    n = qc.num_qubits
    seg1, seg2 = data[:boundary], data[boundary + 1:]
    boundary_k = _run_moments(seg1, n, _zero_state(n))
    if state_hash(boundary_k, receipt.get("precision", PRECISION)) != \
            receipt["boundary_state_hash"]:
        return {"ok": False, "why": "boundary_state_mismatch"}
    btick = [c for c in cells[:ei] if c["op"] == "TICK"]
    if not btick or btick[-1]["args"]["state_hash"] != receipt["boundary_state_hash"]:
        return {"ok": False, "why": "boundary_tick_mismatch"}
    eff = cells[ei]
    bgate = data[boundary]
    if eff["args"]["qubit"] != bgate[1] or eff["args"]["clbit"] != bgate[2]:
        return {"ok": False, "why": "measurement_record_divergence"}
    p_zero = _qubit_prob(boundary_k, n, bgate[1], 0)
    if not (0.0 < p_zero < 1.0):
        return {"ok": False, "why": "degenerate_boundary_distribution"}
    outcome = _sample_outcome(p_zero, eff["args"]["seed"])
    if outcome != eff["args"]["outcome"]:
        return {"ok": False, "why": "outcome_divergence"}
    p_out = p_zero if outcome == "0" else 1.0 - p_zero
    if round(p_out, PROB_DIGITS) != eff["args"]["prob"]:
        return {"ok": False, "why": "prob_divergence"}
    collapsed, _ = _collapse(boundary_k, n, bgate[1], outcome,
                             receipt.get("precision", PRECISION))
    if cells[ii]["args"]["state_sha256"] != hashlib.sha256(
            state_digest(collapsed, receipt.get("precision", PRECISION)).encode()).hexdigest():
        return {"ok": False, "why": "collapsed_state_mismatch"}
    k = collapsed
    rticks = [c for c in cells[ii + 1:] if c["op"] == "TICK"]
    if len(rticks) != len(layers(_Data(seg2))):
        return {"ok": False, "why": "tick_count_divergence"}
    ticker_expect = len(btick) + 1
    for c, moment in zip(rticks, layers(_Data(seg2))):
        for gate in moment:
            _apply(k, gate, n)
        if c["args"]["state_hash"] != state_hash(k, receipt.get("precision", PRECISION)):
            return {"ok": False, "why": "state_divergence@tick%d" % c["args"]["ticker"]}
        if c["args"]["ticker"] != ticker_expect:
            return {"ok": False, "why": "ticker_continuity_break"}
        ticker_expect += 1
    proofs = [c for c in cells if c["op"] == "PROOF"]
    if len(proofs) != 2 or proofs[-1]["args"]["state_sha256"] != hashlib.sha256(
            state_digest(k, receipt.get("precision", PRECISION)).encode()).hexdigest():
        return {"ok": False, "why": "final_proof_mismatch"}
    if receipt.get("final_state_hash") != state_hash(k, receipt.get("precision", PRECISION)):
        return {"ok": False, "why": "final_state_mismatch"}
    return {"ok": True, "why": "ok"}


if __name__ == "__main__":
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)   # boundary: mid-circuit collapse on qubit 0
    qc.x(1)            # acts on the COLLAPSED state, not the GHZ pair
    r = midcircuit_receipt(qc, boundary=2, seed=42)
    print(_canon({"dialect": r["dialect"], "cells": len(r["cells"]),
                  "outcome": r["outcome"],
                  "boundary_state_hash": r["boundary_state_hash"],
                  "final_state_hash": r["final_state_hash"],
                  "verify": verify(r, qc)}))
