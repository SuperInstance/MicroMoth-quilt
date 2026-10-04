# MicroMoth-quilt — CTO Brief

## One-paragraph value statement

MicroMoth-quilt is the fleet's reference implementation of "honest quantum
simulation": a 289-line, zero-dependency quantum simulator (a maintained
MicroQiskit fork) wrapped in a receipt discipline that makes every run
tamper-evident and re-executable. It is small enough to audit line by line
and disciplined enough that 22 sealed experiment receipts plus their
executable pins prove the method at scale. Its value to the organization is
twofold: a teaching-and-verification simulator that cannot silently rot
(import baseline, hash-chained circuits, drift checks), and a proven pattern
— claims ride on receipts, receipts ride on pins — demonstrated end to end
on a real research campaign.

## What it does & for whom

- **Learners and auditors:** a complete quantum simulator (`QuantumCircuit`,
  `simulate()`) with a nine-operation gate set and four output modes
  (statevector, probabilities, counts, memory), readable in an afternoon.
- **Experimenters:** seeded, replayable collapse receipts
  (`tools/collapse_ledger.py`), a 22-receipt evolutionary gate-search
  campaign (`receipts/`), and a bug-injection self-play instrument
  (`tools/selfplay.py`) that measures the test suite's catch rate (0.97
  overall, receipted).
- **Web developers:** a zero-key "quantum wow" plugin (`quantum-wow/`) for
  honest simulated randomness with an optional BYO-key upgrade to real
  IBM-hardware sampling, with graceful, honest degradation.
- **The fleet:** the canonical worked example of the CELL-MAPPING design
  (quantum ops as quilt cells), now coordinated with sibling
  `quilt-qcells` which implemented the premise inside the quilt engine.

## Maturity assessment

**Working (prototype-adjacent, but pinned like hardened).** Evidence:
- Simulator: import-baseline sealed (sha256 per file), Bell check pinned
  since day one; runs green today (255 passing pins, verified this wave).
- Receipt layer: SEALED receipt minting + verification verified live this
  wave (`{"status":"EFFECT/SEALED","verify":{"ok":true}}`).
- Experiment campaign: exp001–exp022 all SEALED with in-repo pins; the
  series' negative results are sealed alongside positives (FROZEN lanes,
  TRAP lanes, REFUTED hypotheses — the honesty posture is the product).
- Known defect, by design: one pre-existing RED (import-manifest drift, 4
  unsealed files) that fails loudly and names its remedy. This is the
  mechanism working, not rot — but it is an open chore.

## Risks

| Risk | Status / mitigation |
|---|---|
| Manifest drift (standing RED) | Open. Mitigation exists (check tool, CI seal-check, pre-push hook, named remedy); needs one regeneration commit. |
| Measure-guard seam (measure to non-matching clbit does not arm the gates-after-measure assert) | Code-read, unverified by a pin. Mitigation: convention + documented in this docs layer; a pin is the natural follow-up. |
| Unseeded sampling misused as reproducible | Mitigated: unsealed receipts are marked, tripwire fails on silent auto-seeding, docs state it everywhere. |
| Scale expectations (2^n memory) | Mitigated: documented envelope; feature-poverty is the design point. |
| Upstream provenance (parent repo 404) | Mitigated: self-governing sealed baseline, VERIFIED/RECORDED tags. |
| Security | Clean: no secrets in repo; the only key surface is BYO runtime key for real mode, never stored. No tokens/keys in docs. |

## Cost profile

- Compute: local CPU only; the whole pin suite runs in under a second; the
  heaviest receipted instrument (selfplay, 60 rounds) was budgeted at 25
  minutes. No servers, no workers, no paid services.
- External services: optional Moth Quantum API (visitor's own key) for real
  hardware randomness; the adapter degrades gracefully and the CORS
  limitation is documented (server-side proxy required for production).
- Fleet spend on the receipt series: $0 external spend recorded.

## Strategic options

- **Maintain (recommended):** the repo is the fleet's demonstrated
  quantum-receipts pattern; cost of upkeep is near zero (one manifest
  re-seal chore; pins do the watching). Keep it as the teaching + audit
  artifact and the launchpad for receipt-lane experiments.
- **Invest:** only if the org wants a browser-facing quantum-randomness
  product (quantum-wow is the seed) or a quantum-receipt standard other
  lanes adopt; both would benefit from a server-side proxy for real mode
  and a native-seed `simulate()`.
- **Harvest-learnings:** the CELL-MAPPING design + pins + the exp series'
  methodology (pre-registration, honest limits, tamper pins) are directly
  transferable to any simulator/ML lane; that transfer has already begun
  (quilt-qcells).
- **Retire:** not indicated — the pins are green, the docs layer now
  supports zero-shot onboarding, and deletion would orphan 22 receipts.

## Integration surface

- **Upstream lineage:** MicroQiskit (IBM) → MicroMoth (Moth Quantum) → this
  fork; ports for Python/Lua/Arduino/C#/JS live under `versions/`.
- **Fleet:** `SuperInstance/quilt-qcells` (the cell-mapping premise inside
  the quilt engine; sibling-port gate), `SuperInstance/micrograd-quilt`
  (labs/qcells — canonical lab home of the experiment series),
  `SuperInstance/moth-research` (Moth Quantum API exhibits), `qthe` and
  other web repos (drop-in targets for quantum-wow), and the fleet algebra
  canon in `SuperInstance/AI-Writings` (algebra.md) that the opcode mapping
  cites.
- **Journal:** SuperInstance/superinstance-lab → worklog.md (grep
  'MicroMoth-quilt'); wave-66 decomposition lane receipted the repo as
  "PARTIAL 19/20" on smoke — matching today's standing RED.
