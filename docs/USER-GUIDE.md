# MicroMoth-quilt — User Guide

## What you get

Two things in one small repo:

1. **A minimal quantum simulator.** `micromoth.py` (standard library only, no
   dependencies) gives you `QuantumCircuit` + `simulate()`: build circuits
   from a nine-operation gate set, get exact statevectors, probability
   dictionaries, or sampled counts. It is deliberately feature-poor — all the
   basic features and only the basic features — so you can learn and verify
   every line.
2. **A receipt layer.** Fleet tools (`tools/`) turn circuits into hash-chained
   ledgers: seeded, tamper-evident collapse receipts whose cell ids re-derive
   and whose outcomes re-execute byte for byte. A 22-receipt experiment series
   (`receipts/`) shows the discipline applied to a real gate-search campaign,
   and `quantum-wow/` gives web projects an honest "quantum random" widget
   with no key required.

## Install

There is nothing to install. The Python simulator is a single file and needs
only Python 3 (the stdlib `random` and `math` modules):

```bash
git clone https://github.com/SuperInstance/MicroMoth-quilt.git
cd MicroMoth-quilt
python3 -c "import micromoth; print('ok')"
```

Optional extras, all stdlib or pytest:

```bash
python3 -m pip install pytest        # only for the test suite
```

The browser plugin (`quantum-wow/`) is two ES modules — copy
`quantum-wow/quantum-wow.js` and `quantum-wow/micromoth.js` into any web
project. No bundler, no dependencies, no API key.

## First success in 5 minutes

The Bell state — the "hello world" of quantum computing:

```bash
python3 -c "
import micromoth
q = micromoth.QuantumCircuit(2, 2)
q.h(0); q.cx(0, 1)
q.measure(0, 0); q.measure(1, 1)
print(micromoth.simulate(q, shots=256, get='counts'))
"
```

Expected output (your exact numbers will differ — sampling is unseeded):

```
{'11': 148, '00': 108}
```

Every one of the 256 shots lands in `{'00','11'}` and never in `{'01','10'}`:
that is entanglement, produced by the smallest simulator that can produce it.
To make the run replayable, mint a sealed receipt instead:

```bash
python3 tools/collapse_ledger.py
```

Expected output (deterministic):

```
{"cells":21,"sealed":true,"shots":16,"status":"EFFECT/SEALED","verify":{"ok":true,"why":"ok"}}
```

That line is 1 LINK cell + 4 BIND cells (h, cx, m, m) + 16 seeded collapse
EFFECT cells, chained by fnv1a-64, and `verify` has re-executed it live.

## Everyday usage

### Build and simulate a circuit

```python
import micromoth

qc = micromoth.QuantumCircuit(3, 3)   # 3 qubits, 3 output bits
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)          # GHZ state
qc.measure_all()     # creates the classical register if absent
counts = micromoth.simulate(qc, shots=1024, get='counts')
print(counts)        # only '000' and '111', roughly 50/50
```

### Get exact amplitudes instead of samples

```python
qc = micromoth.QuantumCircuit(2)
qc.ry(0.5, 0)        # sugar; expands to rx(pi/2), rz(0.5), rx(-pi/2)
sv = micromoth.simulate(qc, get='statevector')
# [[re, im], ...] — 2**n pairs of floats, index = computational basis state
```

`get='probabilities_dict'` returns `{'00': p, '01': p, ...}` (exact
probabilities, no sampling); `get='memory'` returns the per-shot bitstring
list instead of a histogram.

### Make a run replayable (seeded collapse receipt)

```python
from tools.collapse_ledger import collapse_receipt, verify
# (run from repo root, or sys.path.insert the repo root first)
import micromoth
qc = micromoth.QuantumCircuit(2, 2)
qc.h(0); qc.cx(0, 1); qc.measure(0, 0); qc.measure(1, 1)
r = collapse_receipt(qc, shots=512, seed=42)
print(r["status"])            # EFFECT/SEALED  (seed=None -> EFFECT/UNSEALED, honestly marked)
print(verify(r, qc))          # {'ok': True, 'why': 'ok'} — re-derives ids AND re-executes
```

Passing `seed=None` mints an `EFFECT/UNSEALED` receipt: it records what
happened but is honestly marked non-replayable. The tools never launder
unseeded randomness into a sealed claim.

### Add realistic readout error

```python
counts = micromoth.simulate(qc, shots=1024, get='counts', noise_model=0.02)
# one float -> per-qubit measurement flip probability 0.02; or a list of
# num_qubits probabilities for per-qubit control
```

The noise model is measurement error only (bit-flip mixing on the outcome
probabilities) — that is the entire noise scope, by design.

### A quantum random seed for a web page (no key)

```js
import { QuantumWow, mountWidget } from './quantum-wow.js';
const qw = new QuantumWow();                    // simulated mode, no key
const { seed, bits } = await qw.quantumSeed(32); // 32 H-gated qubits, measured
const { result } = await qw.quantumCoin();       // 'heads' | 'tails'
const field   = await qw.quantumField(8);        // 8 values in [0,1] for visuals
mountWidget(document.getElementById('slot'), qw);
// Optional: qw.setApiKey(pastedKey) upgrades to real IBM-hardware sampling
// (comet-qrng-v1) and degrades back to simulated, honestly flagged, on any failure.
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `assert ... 'Index for output bit out of range'` | `measure(q, b)` with b >= num_clbits | Create the circuit with enough classical bits, or use `measure_all()` |
| `assert ... 'Incorrect or missing measure command.'` | A gate acts on a qubit after its measure command (counts/memory paths only) | Move all gates before all measures for that qubit. Note the guard only arms for `measure(q,q)` — a `measure(q,b)` with b≠q does not arm it, so check circuits manually |
| `KeyError` / unexpected counts bit width | Reading counts from a circuit whose clbits were never all measured | Unmeasured clbits stay '0'; measure every bit you care about |
| Same circuit, different counts every run | Unseeded global-RNG sampling (by design — the CELL-MAPPING determinism hole) | Use `tools/collapse_ledger.py::collapse_receipt(qc, shots, seed)` or seed the RNG yourself |
| `ValueError: sugar op 'y' must never reach a ledger` | A hand-built `qc.data` contains y/z/ry tuples | Build circuits via the methods (`qc.y(q)` etc.); they decompose into primitives at append time |
| `pytest` shows 1 failure: `test_manifest_exists_and_matches` | Pre-existing, by-design RED: 4 tracked files added after the seal | Not yours. If you must clear it: `python3 tools/import_manifest.py`, commit `receipts/import-baseline.json` with your change |
| `SEAL DRIFT ... exit 1` from `tools/import_manifest.py --check` | Same drift, named in the output | Same remedy; never hand-edit the manifest |
| quantum-wow "real" mode fails fast in browser | api.mothquantum.com sends no CORS headers | Serve the call through a small server-side proxy; the adapter degrades to simulated and reports `degraded: true` either way |
| Real-mode job returns zero usable bytes | comet-qrng-v1's NIST SP 800-90B extractor can subtract the full ordering penalty when only counts (no per-shot memory) are returned | Honest "no usable output" from a job that really ran; degrade path is the designed behavior |

## FAQ

**Q: Is this a real quantum computer?**
No. Everything local is a dense statevector simulation — exact
 Born-rule sampling on your CPU. The only path to real hardware is
`quantum-wow/` "real" mode with your own Moth Quantum API key (comet-qrng-v1
on IBM quantum hardware), which the adapter treats as optional and degrades
gracefully from.

**Q: Why is the gate set so small?**
Because it is complete enough to be honest. The simulator dispatch recognizes
exactly nine operations (`init`, `m`, `x`, `h`, `rx`, `rz`, `cx`, `crx`,
`swap`); everything else (`y`, `z`, `t`, `ry`) is sugar that decomposes into
those nine at circuit-construction time. Nine ops means nine things to
verify, receipt, and port — and the CELL-MAPPING receipt pins that list, so
an op cannot silently appear.

**Q: How do I reproduce someone else's counts exactly?**
You need their circuit, their shots, their seed, and the seeded path.
Unseeded `simulate()` calls are deliberately not replayable. The receipt
format (`tools/collapse_ledger.py`) pins seed, shots, noise model, and every
gate in a hash chain, and its `verify()` re-executes the whole run.

**Q: Can I use more than ~25 qubits?**
Not meaningfully. The statevector is `2**n` amplitude pairs in plain Python
lists — memory and time grow exponentially and there is no tensor-network or
GPU path. This is a teaching/verification simulator, and the docs say so
rather than hiding it.

**Q: What do the experiments in receipts/ actually test?**
They run a champion-seeded evolutionary search over short circuits toward
target states (|01⟩, Bell balance, 3-qubit GHZ balance), with every run
sealed as a receipt and every receipt pinned by a test that re-derives the
hash chain. The series' findings (seed choice beats seed fitness, jitter
mutation wastes draws, desert-break rates are per-stream) are summarized in
AUDIT.md with honest limits inside each receipt.

**Q: Does the receipt layer change simulation results?**
No. `collapse_ledger.py` seeds the global RNG, calls the stock `simulate()`,
and restores RNG state; micromoth.py is unmodified (the receipts pin its
sha256). The ledger observes; it does not alter.
