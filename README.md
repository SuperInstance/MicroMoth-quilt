# MicroMoth-quilt

**The smallest quantum computing framework, taught to keep receipts.**

This repo is two things, and this README says both up front:

1. **MicroMoth** — the smallest, most feature-poor quantum framework there is
   (a maintained fork of MicroQiskit). All the basic features, only the basic
   features. The full upstream README is preserved below, unchanged.
2. **The quilt-cell quantum lane** — a SuperInstance fleet experiment asking:
   what if a quantum circuit *were* a hash-chained receipt ledger? Every gate
   a BIND cell, every measurement a sealed collapse event, every view a VIEW
   cell — fnv1a-64 chained, replayable, tamper-evident.

A stranger's 60-second version: `micromoth.py` is pure Python you can read in
an afternoon. The fleet's addition treats its circuits as **cell ledgers** in
the fleet's five-opcode algebra (`BIND / LINK / EFFECT / VIEW / TICK`, adopted
`FORGET / PROOF`) — the same receipt idiom the org uses across its WALs,
gossip ledgers, and import manifests. Run a circuit, and the ledger can say
*exactly* which gates were applied, in what order, under which seed — then
re-execute to prove it.

## Try it (no install, verified output)

```bash
git clone https://github.com/SuperInstance/MicroMoth-quilt.git && cd MicroMoth-quilt
python3 -c "
import micromoth
q = micromoth.QuantumCircuit(2, 2)
q.h(0); q.cx(0, 1)
q.measure(0, 0); q.measure(1, 1)
print(micromoth.simulate(q, shots=256, get='counts'))
"
# -> {'00': ~128, '11': ~128}   (Bell state; every shot in the entangled subspace)

python3 -m pytest tests/ -q     # import baseline + cell-mapping + collapse-ledger pins
```

Standard library only. No simulator binaries, no cloud, no API keys.

## What the fleet added (upstream tree untouched)

| addition | what it is | status |
|---|---|---|
| [`AUDIT.md`](AUDIT.md) | import-baseline receipt: provenance, baseline commit, live checks performed at seal | **SEALED** |
| [`receipts/import-baseline.json`](receipts/import-baseline.json) | sha256 per tracked file (267 files), regenerable and pinned | **SEALED** |
| [`tools/import_manifest.py`](tools/import_manifest.py) | the manifest tool (fnv1a-64 + sha256; excludes itself by name and records the exclusion) | tool |
| [`tests/test_import_baseline.py`](tests/test_import_baseline.py) | reruns the Bell check on every invocation — the import can never silently rot | pin |
| [`docs/CELL-MAPPING.md`](docs/CELL-MAPPING.md) | design receipt: quantum ops as quilt cells — op inventory parsed from `simulate()`, the five-opcode mapping, hash conventions | **DESIGN** |
| [`tests/test_cell_mapping.py`](tests/test_cell_mapping.py) | pins the DESIGN: doc's op table ≡ `simulate()` dispatch | pin |
| [`tools/collapse_ledger.py`](tools/collapse_ledger.py) | seed-plumbed collapse receipts: BIND/LINK/EFFECT chains minted SEALED; `verify()` re-derives every cell id and **live re-executes** sealed receipts | tool, **SEALED** output |
| [`tests/test_collapse_ledger.py`](tests/test_collapse_ledger.py) | pins the ledger: id re-derivation, tamper naming, live re-execution | pin |

Provenance honesty: the declared upstream `moth-quantum/MicroMoth` returned
404 at import time, so this fork is **self-governing** — the sealed baseline
in [`AUDIT.md`](AUDIT.md) is the authority, and every claim there is tagged
VERIFIED (run, dated) or RECORDED (read from repo metadata).

## Why receipts on a quantum simulator?

A quantum circuit is already almost a ledger: an ordered list of operations
ending in measurement events. The fleet's doctrine is that *every
computational act deserves a receipt it can be challenged with* — and quantum
adds a sharp reason: **collapse is an event, not a state**. A seeded collapse
receipt turns "this shot gave 01 under seed s" into a re-executable claim
instead of a number in a histogram. The design note
([`docs/CELL-MAPPING.md`](docs/CELL-MAPPING.md)) works this out op by op; the
short version: primitives, not sugar — `y`/`z`/`ry` decompose at append time,
so a circuit cell chain never contains them.

## Status & roadmap

- [x] Import baseline sealed (sha256 manifest, Bell check pinned)
- [x] Cell-mapping DESIGN receipt + pins
- [x] Seeded collapse receipts (SEALED BIND/LINK/EFFECT chains, live re-execution)
- [ ] PROOF statevector witness cell at a TICK — the next cell in the ledger
- [ ] Quilt-native plugin — note: the org's `quilt-qcells` repo (wave 49) has
      since claimed the quantum-ops-as-cells premise for the engine itself;
      this lane coordinates rather than duplicates (sibling-port gate)

Languages: the upstream ships ports for MicroPython/Python, Lua, Arduino,
C#, and JavaScript under [`versions/`](versions/) — the receipt lane targets
the canonical Python template (`micromoth.py`).

---

## Upstream README (preserved verbatim)

# MicroMoth

There are many well-developed and feature-rich frameworks for quantum computing. These allow quantum programs to be created and then run on either advanced simulators or real prototype quantum devices. Though it's obviously a good thing to have many features and support many use-cases, it can sometimes be too much of a good thing!

For this reason we present MicroMoth: the smallest and most feature-poor framework for quantum computing. It has all the basic features and only the basic features. Making it much easier to learn, and much easier to get running.

MicroMoth is an actively maintained fork of [MicroQiskit](https://github.com/qiskit-community/MicroQiskit), which was initially conceived as a version of the [Qiskit](https://www.ibm.com/quantum/qiskit) SDK that could run on microcontroller devices. The strict need for simplicity and a lack of complex dependencies was the main guidance for the design. MicroMoth has some additional features in comparison with the original MicroQiskit.

MicroMoth also contains ports for other languages, so you can bring the world of quantum into your familiar workflows. If you don't see your favourite language, note that it might be available for [MicroQiskit](versions/update_required) instead since we haven't finished upgrading all the ports.


### Documentation

* [Documentation for MicroMoth](https://micromoth.readthedocs.io/en/latest/#)

### Tutorial

* [Tutorial for MicroPython/Python 2/Python 3 version](versions/MicroPython/tutorials/index.ipynb)

### Installation

Installation guides for the various versions of MicroMoth can be found in the corresponding README files.

* [MicroPython/Python 2/Python 3](versions/Python/README.md)
* [Lua](versions/Lua/README.md)
* [Arduino](versions/Arduino/MicroMothArduino.md)
* [C#](versions/Csharp/MicroMothCSharp.md)


### Template Version

The [micromoth.py](micromoth.py) file found in this folder is intended as a template version. It contains comments to explain how each part of MicroMoth works, both to aid understanding and to help in the writing of ports. The MicroPython version is directly constructed from this template.

