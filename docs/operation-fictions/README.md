# The Smallest Honest Lab in Physics

*An operation fiction for MicroMoth-quilt. Written at the stand-down, 2026-10-06.*

---

Quantum computing has a scandal, and it is not decoherence, and it is not
error rates, and it is not the hardware money. The scandal is quieter:
*unseeded histograms.* A quantum circuit is run, shots are sampled, a
distribution is printed — and the printout is a claim nobody can re-verify,
because the sampling consumed a stream of randomness that was never named.
The result looks like knowledge. It is actually testimony about an event
that left no recording. In a field that measures its progress in
fidelities and cross-entropy benchmarks, the most quietly unscientific
object is the humble print statement — the place where physics is
converted into prose by a random number no one wrote down.

This repo's wager is that the cure is not more physics. The cure is fewer
features.

MicroMoth is the smallest, most feature-poor quantum framework there is —
nine executable operations, a statevector simulator you can read in an
afternoon, a README that brags about what it refuses to implement. And the
fleet bolted on the one thing the giants of the field kept leaving out: a
receipt discipline that treats every circuit as a hash-chained ledger.
Every gate a BIND cell. Every measurement a sealed collapse event, seeded,
re-executable, tamper-evident. Every view a VIEW cell whose digest is
pinned and never laundered into prose. When this lab prints a histogram,
the histogram carries its own trial record — which gates, in what order,
under which seed — and anyone, anywhere, on any afternoon, can replay the
experiment and check the physics against the claim.

Follow that wager up the ladder, because it climbs. Rungs one and two of
the IonQ ladder were pre-flighted in simulation with discriminators
designed to catch a classical impostor: the forbidden-sum measurement
lands at 0.49815 where coherence says 0.50 and an accumulator says 0.0 —
five hundred standard deviations of teeth. The weight algebra sweeps pin
the sin² bridge exact at π, catch additivity at 0.7494 against 0.75, catch
cancellation at exact zero. These pre-flights are not rehearsals for
quantum supremacy theater. They are *receipts of readiness* — the
simulator-native way of saying: when hardware credits arrive, the
experiment that runs on the QPU will be one whose every claim can be
replayed, whose every shot is bound to a named seed, whose provenance a
skeptic can audit without trusting a cloud dashboard.

That is the indescribable thing made describable: when this repo looks at
a quantum computer, it sees *a witness that must be cross-examined.*
Feature-poverty is the enabling virtue — with nine operations there is
nowhere for a result to hide from its derivation, no framework magic
between the claim and the circuit that justifies it. The honesty law of
the fleet — no receipt, no claim — was always going to find its sharpest
test bench here, because quantum is the one field where nature herself
deals in sampled events, where the boundary between *what happened* and
*what was claimed to have happened* is thinnest, and where an unseeded
histogram is not a small lie but the whole epistemology of the field,
quietly leaking.

The labs that will matter in the hardware decade are not the biggest ones.
They are the ones whose printouts can be put on trial — and win.

---

*Seed for the next cultivator.* Guard the poverty. Every feature added is
a place physics can hide from its receipts; add operations only when the
ledger can carry them honestly. Rung three waits for hardware and for an
owner's go — and when it runs, run it the way the first two rungs were
pre-flighted: discriminators first, receipts always, and the refusal —
refused-not-faked — louder than any result. The smallest honest lab in
physics stays honest by staying small.
