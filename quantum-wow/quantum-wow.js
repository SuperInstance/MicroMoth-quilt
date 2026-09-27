// quantum-wow.js — a modular "quantum wow" plugin built on MicroMoth.
//
// Zero-dependency ES module. Drop this file and its sibling `micromoth.js`
// into any web project (quilt, cargo-line, qthe, or anything else) to get:
//
//   - a genuine quantum-simulated random seed / coin flip, click-and-play,
//     with NO API key required (it runs a real (simulated) quantum circuit
//     — Hadamard gates + measurement — locally, via MicroMoth), and
//   - an optional upgrade path: if a visitor supplies their own Moth Quantum
//     API key (https://platform.mothquantum.com), the same calls are routed
//     to real IBM-hardware quantum measurements instead. If that call fails
//     for any reason (missing scope, network error, etc.) it degrades
//     gracefully back to the local simulation and says so honestly.
//
// (C) Copyright Moth Quantum 2025.
// (C) Copyright SuperInstance 2026.
//
// This code is licensed under the Apache License, Version 2.0. You may
// obtain a copy of this license in the LICENSE.txt file in the root directory
// of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
//
// -----------------------------------------------------------------------
// Quick start
// -----------------------------------------------------------------------
//
//   import { QuantumWow } from './quantum-wow.js';
//
//   const qw = new QuantumWow(); // mode: 'simulated', no key needed
//   const { seed, bits } = await qw.quantumSeed(32);
//   const { result } = await qw.quantumCoin();
//
//   // Optional: BYO Moth API key to attempt real IBM-hardware measurements.
//   qw.setApiKey(pastedKey); // flips to mode: 'real' (degrades automatically
//                            // on failure — see `degraded` on each result)
//
//   // Optional: embeddable widget (status + explanation + key input)
//   import { mountWidget } from './quantum-wow.js';
//   mountWidget(document.getElementById('quantum-wow-slot'), qw);
//
// -----------------------------------------------------------------------

import QuantumCircuit, { simulate } from './micromoth.js';

/** The two backend modes. Same public interface either way. */
export const MODES = Object.freeze({
  SIMULATED: 'simulated',
  REAL: 'real',
});

const MOTH_API_BASE = 'https://api.mothquantum.com/api/v1';
const MOTH_QRNG_ENGINE = 'comet-qrng-v1';

/** Error thrown for any failure talking to the real Moth API. Callers of
 * the low-level helpers see this; QuantumWow itself catches it internally
 * and degrades to simulated mode. */
export class MothApiError extends Error {
  constructor(message, status = null, body = null) {
    super(message);
    this.name = 'MothApiError';
    this.status = status;
    this.body = body;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function trimKey(key) {
  return typeof key === 'string' ? key.trim() : key;
}

async function safeText(res) {
  try {
    return await res.text();
  } catch {
    return '';
  }
}

/**
 * Run `nbits` worth of Hadamard-then-measure on the local MicroMoth
 * simulator and return them as a bitstring, e.g. "01101...".
 * Chunked so we never build a statevector larger than 2^16 amplitudes.
 */
function simulatedBits(nbits) {
  const CHUNK = 16; // 2^16 amplitudes per batch — instant, and well under
                     // MicroMoth's own 20-qubit ceiling.
  let bits = '';
  while (bits.length < nbits) {
    const n = Math.min(CHUNK, nbits - bits.length);
    const qc = new QuantumCircuit(n, n);
    for (let i = 0; i < n; i++) qc.h(i);
    qc.measure_all();
    // shots=1, get='memory' -> a single raw measured bitstring, sampled
    // from the (uniform, thanks to Hadamard) probability distribution.
    const [sample] = simulate(qc, 1, 'memory');
    bits += sample;
  }
  return bits.slice(0, nbits);
}

/** Turn a hex string into a bitstring. */
function hexToBits(hex) {
  let out = '';
  for (const ch of hex.trim()) {
    const v = parseInt(ch, 16);
    if (Number.isNaN(v)) return null;
    out += v.toString(2).padStart(4, '0');
  }
  return out;
}

/** Best-effort extraction of a bitstring from an unknown-shaped value:
 * a bitstring, a hex string, an array of 0/1, or an array of byte values. */
function coerceToBits(value) {
  if (value == null) return null;
  if (typeof value === 'string') {
    if (/^[01]+$/.test(value)) return value;
    if (/^(0x)?[0-9a-fA-F]+$/.test(value)) return hexToBits(value.replace(/^0x/, ''));
    return null;
  }
  if (Array.isArray(value) && value.length > 0) {
    if (value.every((v) => v === 0 || v === 1)) return value.join('');
    if (value.every((v) => Number.isInteger(v) && v >= 0 && v <= 255)) {
      return value.map((b) => b.toString(2).padStart(8, '0')).join('');
    }
  }
  return null;
}

/**
 * Extract a bitstring from a `comet-qrng-v1` job result. The engine's real
 * shape (confirmed live against api.mothquantum.com) is
 * `result.output.random.{hex,bytes,bits}` — but a few other shapes are
 * tried too, defensively, in case the engine or API version changes.
 *
 * Note: in `mode: 'qpu'` (genuine IBM hardware) this engine applies a
 * certified NIST SP 800-90B entropy-extraction pipeline that, for a
 * backend returning counts only (no per-shot memory), subtracts a large
 * "ordering penalty" — for modest shot counts this legitimately yields
 * `random.bytes: 0` even though the job ran for real on IBM hardware and
 * consumed real qpu_seconds. That is a real, honest "no usable output"
 * case, not a bug — we surface it distinctly so it degrades gracefully.
 */
function extractBits(resultJson, nbits) {
  const random = resultJson?.result?.output?.random;
  if (random && typeof random === 'object') {
    if (random.bytes === 0 || random.hex === '') {
      throw new MothApiError(
        'Moth engine ran but certified zero extractable bytes for these parameters ' +
          '(counts-only readout on real hardware often has no usable entropy budget ' +
          'below very large shot counts)',
        0,
        JSON.stringify(resultJson?.result?.output?.entropy ?? {}).slice(0, 500)
      );
    }
    const bits = coerceToBits(random.hex) || coerceToBits(random.bits);
    if (bits && bits.length >= nbits) return bits.slice(0, nbits);
  }

  // Defensive fallbacks for other/older response shapes.
  const candidates = [
    resultJson?.data?.bits,
    resultJson?.bits,
    resultJson?.data?.bytes,
    resultJson?.bytes,
    resultJson?.data?.hex,
    resultJson?.hex,
    resultJson?.result?.bits,
    resultJson?.result?.bytes,
    resultJson?.result,
    resultJson?.data,
  ];
  for (const candidate of candidates) {
    const bits = coerceToBits(candidate);
    if (bits && bits.length >= nbits) return bits.slice(0, nbits);
  }
  throw new MothApiError(
    'Could not find random bits in Moth job result',
    0,
    JSON.stringify(resultJson).slice(0, 500)
  );
}

const TERMINAL_OK = new Set(['completed', 'succeeded', 'done', 'success']);
const TERMINAL_FAIL = new Set(['failed', 'error', 'cancelled', 'canceled']);

/**
 * Low-level call to the real Moth API: submit an async engine job, poll
 * for completion, fetch the result, and normalize it to a bitstring.
 * Exported for advanced/testing use; QuantumWow wraps this with graceful
 * degradation for normal use.
 */
export async function mothRequestBits(apiKey, nbits, opts = {}) {
  const {
    fetchImpl = (typeof fetch !== 'undefined' ? fetch.bind(globalThis) : null),
    pollIntervalMs = 1000,
    maxPolls = 90, // real IBM-hardware jobs can take up to ~90s to clear the queue
    base = MOTH_API_BASE,
    engine = MOTH_QRNG_ENGINE,
    // 'qpu' = genuine Born-rule measurements on real IBM hardware (the
    // "true version"); 'emu' would be Moth's own server-side simulator,
    // which defeats the point of the BYO-key upgrade path.
    mode = 'qpu',
    shots = 4096,
    bellWitness = false,
  } = opts;

  if (!fetchImpl) throw new MothApiError('No fetch implementation available');
  const bearer = trimKey(apiKey);
  if (!bearer) throw new MothApiError('No Moth API key supplied');

  const nbytes = Math.max(1, Math.ceil(nbits / 8));
  const numQubits = Math.min(20, Math.max(8, nbits));

  const submitRes = await fetchImpl(`${base}/engines/${engine}/process`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${bearer}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      params: {
        output_bytes: nbytes,
        num_qubits: numQubits,
        shots,
        mode,
        bell_witness: bellWitness,
      },
    }),
  });
  if (!submitRes.ok) {
    throw new MothApiError(
      `Moth engine submit failed (HTTP ${submitRes.status})`,
      submitRes.status,
      await safeText(submitRes)
    );
  }
  const submitJson = await submitRes.json();
  const jobId = submitJson.job_id || submitJson.id || submitJson.jobId;
  if (!jobId) {
    throw new MothApiError('Moth submit response had no job id', submitRes.status, JSON.stringify(submitJson));
  }

  let status = 'queued';
  for (let i = 0; i < maxPolls; i++) {
    const statusRes = await fetchImpl(`${base}/jobs/${jobId}/status`, {
      headers: { Authorization: `Bearer ${bearer}` },
    });
    if (!statusRes.ok) {
      throw new MothApiError(
        `Moth job status check failed (HTTP ${statusRes.status})`,
        statusRes.status,
        await safeText(statusRes)
      );
    }
    const statusJson = await statusRes.json();
    status = (statusJson.status || statusJson.state || '').toLowerCase();
    if (TERMINAL_OK.has(status)) break;
    if (TERMINAL_FAIL.has(status)) {
      throw new MothApiError(`Moth job ${status}`, statusRes.status, JSON.stringify(statusJson));
    }
    await sleep(pollIntervalMs);
  }
  if (!TERMINAL_OK.has(status)) {
    throw new MothApiError(`Moth job timed out (last status: ${status})`, 0, status);
  }

  const resultRes = await fetchImpl(`${base}/jobs/${jobId}/result`, {
    headers: { Authorization: `Bearer ${bearer}` },
  });
  if (!resultRes.ok) {
    throw new MothApiError(
      `Moth job result fetch failed (HTTP ${resultRes.status})`,
      resultRes.status,
      await safeText(resultRes)
    );
  }
  const resultJson = await resultRes.json();
  return extractBits(resultJson, nbits);
}

/**
 * The plugin's main entry point: a small backend adapter with two modes
 * behind the same interface, plus the wow-surface primitives on top.
 */
export class QuantumWow {
  /**
   * @param {object} [opts]
   * @param {string|null} [opts.apiKey] - a Moth API key supplied by the
   *   visitor at runtime (BYO-key, client-supplied pattern — the default
   *   for this demo). Presence of a key flips the adapter to 'real' mode.
   * @param {() => Promise<string|null>} [opts.keyProvider] - for server
   *   deployments: an async function that resolves the key from wherever
   *   it's held server-side (e.g. a Cloudflare Secrets Store binding).
   *   Checked at call time; takes priority over `apiKey` if it returns a
   *   non-empty value.
   * @param {Function} [opts.fetchImpl] - override for `fetch` (tests, or
   *   non-browser/non-Node runtimes).
   * @param {(mode:string, info:object) => void} [opts.onModeChange] -
   *   called whenever the *effective* mode of a call changes, including
   *   graceful degradation from real -> simulated.
   */
  constructor(opts = {}) {
    const { apiKey = null, keyProvider = null, fetchImpl, onModeChange } = opts;
    this.apiKey = apiKey ? trimKey(apiKey) : null;
    this.keyProvider = keyProvider || null;
    this.fetchImpl = fetchImpl || (typeof fetch !== 'undefined' ? fetch.bind(globalThis) : null);
    this.onModeChange = typeof onModeChange === 'function' ? onModeChange : () => {};
    this.lastDegradation = null;
  }

  /** The mode the adapter is *configured* for (real if a key is present). */
  getMode() {
    return this.apiKey || this.keyProvider ? MODES.REAL : MODES.SIMULATED;
  }

  /** Set (or clear, with a falsy value) the BYO Moth API key at runtime. */
  setApiKey(key) {
    const trimmed = trimKey(key);
    this.apiKey = trimmed || null;
    this.lastDegradation = null;
    this.onModeChange(this.getMode(), { source: 'setApiKey' });
    return this.getMode();
  }

  clearApiKey() {
    return this.setApiKey(null);
  }

  async _resolveKey() {
    if (this.keyProvider) {
      try {
        const k = await this.keyProvider();
        if (k) return trimKey(k);
      } catch {
        /* fall through to client-supplied key */
      }
    }
    return this.apiKey;
  }

  /**
   * Core call: get `nbits` of quantum-measured randomness. Same shape
   * regardless of mode: { bits, requestedMode, mode, degraded, error }.
   */
  async _getBits(nbits) {
    const key = await this._resolveKey();
    const requestedMode = key ? MODES.REAL : MODES.SIMULATED;

    if (requestedMode === MODES.REAL) {
      try {
        const bits = await mothRequestBits(key, nbits, { fetchImpl: this.fetchImpl });
        this.lastDegradation = null;
        this.onModeChange(MODES.REAL, { source: 'call' });
        return { bits, requestedMode, mode: MODES.REAL, degraded: false, error: null };
      } catch (err) {
        const info = {
          message: err.message,
          status: err instanceof MothApiError ? err.status : null,
          at: Date.now(),
        };
        this.lastDegradation = info;
        this.onModeChange(MODES.SIMULATED, { source: 'degrade', ...info });
        return {
          bits: simulatedBits(nbits),
          requestedMode,
          mode: MODES.SIMULATED,
          degraded: true,
          error: info,
        };
      }
    }

    return {
      bits: simulatedBits(nbits),
      requestedMode,
      mode: MODES.SIMULATED,
      degraded: false,
      error: null,
    };
  }

  /**
   * A random seed drawn from a (simulated, by default) quantum circuit:
   * `nbits` qubits in superposition (Hadamard) then measured.
   * @param {number} [nbits=32]
   * @returns {Promise<{seed:string, bits:string, mode:string, degraded:boolean, requestedMode:string, error:object|null}>}
   *   `seed` is the hex encoding of `bits`.
   */
  async quantumSeed(nbits = 32) {
    const { bits, ...rest } = await this._getBits(nbits);
    const seed = BigInt('0b' + bits).toString(16).padStart(Math.ceil(nbits / 4), '0');
    return { seed, bits, ...rest };
  }

  /** A single quantum coin flip. */
  async quantumCoin() {
    const { bits, ...rest } = await this._getBits(1);
    const bit = bits[0];
    return { result: bit === '1' ? 'heads' : 'tails', bit, ...rest };
  }

  /**
   * A small quantum-circuit-driven value field: `n` values in [0, 1], each
   * derived from one measured byte. Cheap enough to redraw on every frame
   * of a small visual effect (a dot grid, a shimmer, a noise texture seed)
   * without being a full simulation engine.
   */
  async quantumField(n = 8) {
    const { bits, ...rest } = await this._getBits(n * 8);
    const values = [];
    for (let i = 0; i < n; i++) {
      const byte = bits.slice(i * 8, i * 8 + 8);
      values.push(parseInt(byte, 2) / 255);
    }
    return { values, ...rest };
  }
}

// ---------------------------------------------------------------------
// Embeddable widget: a small, framework-free status + key-input control.
// ---------------------------------------------------------------------

const WIDGET_STYLE_ID = 'quantum-wow-widget-style';
const WIDGET_CSS = `
.qw-widget {
  --qw-cream: #faf6ec;
  --qw-ink: #1c1a16;
  --qw-ink-soft: #55503f;
  --qw-accent: #6b4fd6;
  --qw-border: #e4dcc6;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--qw-cream);
  color: var(--qw-ink);
  border: 1px solid var(--qw-border);
  border-radius: 12px;
  padding: 14px 16px;
  max-width: 420px;
  box-sizing: border-box;
  font-size: 14px;
  line-height: 1.4;
}
.qw-widget * { box-sizing: border-box; }
.qw-status {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.qw-status .qw-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--qw-ink-soft);
  display: inline-block;
}
.qw-widget[data-mode="real"] .qw-dot { background: #2e8b57; }
.qw-widget[data-mode="simulated"] .qw-dot { background: var(--qw-accent); }
.qw-explain {
  margin-top: 6px;
  color: var(--qw-ink-soft);
  font-size: 12.5px;
}
.qw-explain a { color: var(--qw-accent); text-decoration: none; }
.qw-explain a:hover { text-decoration: underline; }
.qw-key-row {
  margin-top: 10px;
  display: flex;
  gap: 6px;
}
.qw-key-input {
  flex: 1;
  min-width: 0;
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid var(--qw-border);
  background: #fff;
  color: var(--qw-ink);
  font-size: 12.5px;
}
.qw-key-input:focus { outline: 2px solid var(--qw-accent); outline-offset: 1px; }
.qw-key-clear {
  border: 1px solid var(--qw-border);
  background: #fff;
  border-radius: 8px;
  padding: 0 10px;
  cursor: pointer;
  color: var(--qw-ink-soft);
  font-size: 14px;
}
.qw-key-clear:hover { color: var(--qw-ink); }
.qw-note {
  margin-top: 8px;
  font-size: 12px;
  color: #9a5b2e;
  display: none;
}
.qw-note.qw-show { display: block; }
@media (max-width: 420px) {
  .qw-widget { max-width: 100%; }
}
`;

function ensureWidgetStyle() {
  if (typeof document === 'undefined') return;
  if (document.getElementById(WIDGET_STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = WIDGET_STYLE_ID;
  style.textContent = WIDGET_CSS;
  document.head.appendChild(style);
}

const MODE_LABEL = {
  [MODES.SIMULATED]: 'simulated',
  [MODES.REAL]: 'real (IBM quantum hardware)',
};

const MODE_EXPLANATION = {
  [MODES.SIMULATED]:
    'Simulated quantum (MicroMoth) — runs entirely in your browser. No key, no network call.',
  [MODES.REAL]:
    'Real quantum measurements from IBM hardware, via the Moth Quantum API and your key.',
};

/**
 * Mount the status + key-input widget into `container`.
 * @param {HTMLElement} container
 * @param {QuantumWow} quantumWow
 * @param {object} [opts]
 * @param {string} [opts.explainerUrl] - link target for "what does this mean?"
 */
export function mountWidget(container, quantumWow, opts = {}) {
  if (typeof document === 'undefined') {
    throw new Error('mountWidget requires a DOM (browser environment)');
  }
  const { explainerUrl = '#quantum-wow-explainer' } = opts;
  ensureWidgetStyle();

  const root = document.createElement('div');
  root.className = 'qw-widget';

  const status = document.createElement('div');
  status.className = 'qw-status';
  status.innerHTML = `<span class="qw-dot"></span><span>&#9883; quantum: <span class="qw-mode-label"></span></span>`;

  const explain = document.createElement('div');
  explain.className = 'qw-explain';
  const explainText = document.createElement('span');
  explainText.className = 'qw-explain-text';
  const explainLink = document.createElement('a');
  explainLink.href = explainerUrl;
  explainLink.textContent = ' Learn more ↗';
  explainLink.target = explainLink.href.startsWith('#') ? '' : '_blank';
  explainLink.rel = 'noopener noreferrer';
  explain.appendChild(explainText);
  explain.appendChild(explainLink);

  const keyRow = document.createElement('div');
  keyRow.className = 'qw-key-row';
  const keyInput = document.createElement('input');
  keyInput.type = 'password';
  keyInput.className = 'qw-key-input';
  keyInput.autocomplete = 'off';
  keyInput.spellcheck = false;
  keyInput.placeholder = 'Have a Moth key? Paste it for real IBM-quantum results ↗';
  const keyClear = document.createElement('button');
  keyClear.type = 'button';
  keyClear.className = 'qw-key-clear';
  keyClear.textContent = '×';
  keyClear.title = 'Clear key, back to simulated';
  keyRow.appendChild(keyInput);
  keyRow.appendChild(keyClear);

  const note = document.createElement('div');
  note.className = 'qw-note';

  root.appendChild(status);
  root.appendChild(explain);
  root.appendChild(keyRow);
  root.appendChild(note);
  container.appendChild(root);

  function render(mode, degradeInfo) {
    root.setAttribute('data-mode', mode);
    root.querySelector('.qw-mode-label').textContent = MODE_LABEL[mode] || mode;
    explainText.textContent = MODE_EXPLANATION[mode] || '';
    if (degradeInfo) {
      note.textContent = `Real quantum call didn't go through (${degradeInfo.status ?? 'error'}: ${degradeInfo.message}) — showing simulated results instead.`;
      note.classList.add('qw-show');
    } else {
      note.classList.remove('qw-show');
    }
  }

  render(quantumWow.getMode(), quantumWow.lastDegradation);

  const previousOnModeChange = quantumWow.onModeChange;
  quantumWow.onModeChange = (mode, info) => {
    previousOnModeChange(mode, info);
    const isDegrade = info && info.source === 'degrade';
    render(mode, isDegrade ? info : null);
  };

  keyInput.addEventListener('change', () => {
    const mode = quantumWow.setApiKey(keyInput.value);
    if (mode === MODES.SIMULATED) keyInput.value = '';
  });

  keyClear.addEventListener('click', () => {
    keyInput.value = '';
    quantumWow.clearApiKey();
  });

  return {
    root,
    destroy() {
      quantumWow.onModeChange = previousOnModeChange;
      root.remove();
    },
  };
}

export default QuantumWow;
