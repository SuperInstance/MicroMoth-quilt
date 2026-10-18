# ATTESTATION.md — what this repo's ledgers actually prove

**Status:** normative for this repo's vocabulary. Read before using the word
*tamper-evident* about anything in `receipts/` or `tools/`.

This repo's ledgers are **attestable**. They are **not tamper-evident**, and
the difference is a security claim rather than a wording preference. This note
says which of the three legs each artifact has, so nobody has to guess.

## The three legs

A log earns the word **tamper-evident** only when all three hold:

| # | leg | what it means |
|---|---|---|
| 1 | **chain re-derives** | replay reproduces every linkage; a rewrite is *expensive* |
| 2 | **head signed** | the head is signed by a key we trust |
| 3 | **head published out of band** | the signed head lives where the log writer does not control it |

| legs held | the correct word |
|---|---|
| 1 only | **attestable** — "the chain re-derives" |
| 1+2 | **attested** — "the chain re-derives and the head is signed" |
| 1+2+3 | **tamper-evident** — and only then is the word earned |

## What this repo has

| artifact | linkage class | legs held | correct word |
|---|---|---|---|
| circuit cell ids (`tools/cell_receipts.py`, `tools/collapse_ledger.py`) | `chain` | **1** | **attestable** |
| `receipts/import-baseline.json` | `row-checksum` (529 flat sha256 rows, no linkage) | **1** | **attestable** |
| `receipts/exp0NN-*.json` | `chain` | **1** | **attestable** |

**Leg 2: no.** Nothing here is signed. `tools/` has no signing path at all.
**Leg 3: no.** There is no published head anywhere — no `receipts/heads/`, no
committed signature beside any receipt. The head is inside the log it would
anchor, and a writer can re-seal it for free.

So this repo is at **leg 1 only**, and *attestable* is the accurate word. That
is a **narrower** claim than the repo used to make, and it is still worth
having: the chain re-derivation means an edit is expensive, a naive edit is
*named* (`id_mismatch@i`, `chain_break@i`), and a re-execution mismatch is
reported rather than laundered.

## The two attacks re-derivation cannot see

**1. The re-chained rewrite.** Edit a collapse outcome, recompute the chain
over the edit, and every id re-derives. The attacker recomputed it, so the
residue agrees. Detection requires a commitment made *before* the edit.

**2. The tail truncation.** This one is cheaper and worse, because it needs no
competence at all. Delete the last N cells and the remaining chain is a
**shorter valid chain** — every surviving linkage is still correct, because
linkage is local. *A truncated chain is a shorter valid chain.* On the fleet's
`witness-chain/1` implementation, tail-truncating a 121-record log by 50
records leaves 71 that verify cleanly.

A re-chained rewrite at least shows up as an expensive operation. Truncation
is a `rm` on the last lines.

## "intact" is not producible for a row-checksum object

`receipts/import-baseline.json` is 529 independent sha256 rows. They do not
commit to each other, so there is no linkage to be "intact" *with respect to*.
A verdict on it says **"529/529 digests match"** and names the class
`row-checksum`. It does not say "intact".

For a `chain`, **"chain-intact"** is available and means precisely: the chain
verified.

## Vocabulary

- **attestable** — leg 1 alone. This repo.
- **chain-intact** — a `chain` verdict; the chain verified.
- **row checksums match** — a `row-checksum` verdict. Never "intact".
- **attested** — legs 1+2.
- **tamper-evident** — legs 1+2+3. Not yet available anywhere in this repo.

## The fix, when this repo wants the strong word

Not a wording change. It is one build: sign the receipt head (Ed25519, and a
verifier that **refuses** rather than degrades when the backend is absent),
and commit that signed head somewhere the log writer's own workflow cannot
push to. Until both halves exist, the honest word is *attestable*.

Fleet context and the normative definition:
[`SuperInstance/witness-spec`](https://github.com/SuperInstance/witness-spec) —
`SPEC.md`, *Linkage class* and *Tamper-evidence — the three legs*.
