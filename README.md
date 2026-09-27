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

### JavaScript / Web

* [JavaScript port](versions/JavaScript/micromoth.js) — a faithful, zero-dependency ES module port of the template, for the browser and Node. Same gates (`x`, `h`, `rx`, `rz`, and the `y`/`z`/`t`/`ry` gates built from them), same `cx`/`crx`/`swap` two-qubit gates (plus a `crz` extension, wired into the simulator the same way `crx` is), and the same measurement/`simulate()` semantics (`counts`, `memory`, `probability_dictionary`, `statevector`).
* [`quantum-wow/`](quantum-wow/) — a modular **"quantum wow" plugin** built on that port: a drop-in for quilt, cargo-line, qthe, or any other web project that wants a genuine quantum wow, click-and-play, with no key required.

#### `quantum-wow` plugin

`quantum-wow/quantum-wow.js` is a zero-dependency ES module exposing:

- **`quantumSeed(nbits = 32)`** — a random seed drawn from a real (simulated, by default) quantum circuit: `nbits` qubits put into superposition with Hadamard gates, then measured. Returns `{ seed, bits, mode, degraded }`.
- **`quantumCoin()`** — a single quantum coin flip (`{ result: 'heads'|'tails', bit, mode, degraded }`).
- **`quantumField(n = 8)`** — a small quantum-circuit-driven value field: `n` values in `[0, 1]`, cheap enough to drive a visual effect (a dot grid, a shimmer) without being a full engine.
- **A backend adapter with two modes, same interface:**
  - **`simulated` (default, no key)** — runs MicroMoth locally, right in the visitor's browser. This is the click-and-play, no-key wow.
  - **`real` (BYO key)** — when a visitor supplies their own [Moth Quantum](https://platform.mothquantum.com) API key, calls route to the real `comet-qrng-v1` engine (`https://api.mothquantum.com/api/v1`, async job: `POST /engines/comet-qrng-v1/process` → poll `GET /jobs/{id}/status` → `GET /jobs/{id}/result`), for genuine Born-rule measurements on IBM quantum hardware. **If the real call fails for any reason it degrades gracefully back to `simulated` and says so** — every public method always returns a usable result, plus `{ mode, degraded, error }` so the caller (or the bundled widget) can be honest about what actually happened. A key is never hardcoded: it's supplied by the visitor at runtime (`quantumWow.setApiKey(...)`), or, for a server deployment, resolved at call time from a `keyProvider` you wire to your own secrets store.
- **`mountWidget(container, quantumWow)`** — a small embeddable, framework-free, cream/ink-themed widget: a live "⚛️ quantum: simulated / real" status, a one-line explanation with a link placeholder, and a key-input field ("Have a Moth key? Paste it for real IBM-quantum results ↗") that flips the widget to real mode live and shows the degrade reason honestly if a real call doesn't go through.

`quantum-wow/index.html` is a click-and-play demo of all of the above — draw a seed, flip a coin, sample a field, then paste a key to try the real-hardware upgrade.

To drop this into another project (quilt, cargo-line, qthe, ...), copy the two files `quantum-wow/quantum-wow.js` and `quantum-wow/micromoth.js` into it (they're a self-contained pair — no bundler, no dependencies) and `import { QuantumWow, mountWidget } from './quantum-wow.js'`.

**Note on the "real" mode:** `api.mothquantum.com` does not currently send CORS headers, so a real-mode call made directly from client-side JS in a browser will be blocked by the browser itself (visible as a fast network-level failure, which the adapter treats like any other failure and degrades from) — a production deployment wanting the real upgrade to actually complete in-browser would route it through a small server-side proxy (a Cloudflare Pages Function/Worker), which is also where the `keyProvider`/secrets-store pattern is meant to be used. Separately, even server-to-server, the `comet-qrng-v1` engine's certified hardware (`mode: 'qpu'`) path can legitimately return zero extractable bytes for modest shot counts, since its NIST SP 800-90B extractor subtracts a large "ordering penalty" when the backend returns counts only (no per-shot memory) — that's a real, honest "no usable output" outcome from a job that did run for real on IBM hardware, not a bug, and it degrades the same way a scope/permission error would.

