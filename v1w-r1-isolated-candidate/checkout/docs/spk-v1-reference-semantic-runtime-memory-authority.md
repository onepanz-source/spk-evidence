# SPK v1 Reference: semantic BV bus and C-owned P authority (T8JKL/MNO/PQR)

**Research-only executable reference. It is not an SPK architecture release, is not native SPK memory, and does not authenticate a hostile host.**

## Contract boundaries

1. Frozen BV-v0e and PE-v1b are SHA-pinned and *unchanged*. They still transport structural feedback only, in a three-node A/B/C topology. No direct semantic verdict appears in a frozen BV packet.
2. The NEW `semantic_bus_v1` executes after each actual BV-v0e epoch, interprets the original A PE 21/22 emission, and emits an explicit v1 reference payload along A→B→C. It binds decision, context, P policy version, source evidence, original structural deliveries, and causal parent. This is a new event-bus reference built on an original frozen source trace, **not an in-tick native v0e extension**.
3. The NEW `PAuthorityV1` is a working host-owned reference authority, storing `owner=C`, `domain=P`, `mode=execute`, issuing a one-shot grant **in the same SQLite transaction** as P compare-and-swap and settlement, and verifying full replay/ledger materialization on reopen. This is a real gate in v1 research runtime, rather than the T8ABC all-DENIED design candidate. **It is not an authorization granted by the frozen SPK Memory Contract**.
4. The v1 reference is orchestrated between self-contained epochs by a research driver. The driver provides synthetic choices of A's goal and creates the separate next frozen case, using the P state read at the beginning of the new epoch.

## State transition and negative controls

- `issue` reads C-owned reference P for the cue, version and value, records an outstanding decision, and rejects another outstanding decision.
- An original three-node BV epoch executes on the **unmodified original** scheduler. On genuine forward traversal A's original PE outputs semantic channel 21/22; v0e's two structural reverse deliveries remain unaltered.
- The new v1 bus binds original A and BV evidence into a reference-semantic packet. Missing forward traversal carries **no** reference verdict.
- The new reference P authority validates the emitted packet against the source and the outstanding decision. `WORSENED`, learning enabled, and remaining bounded budget can produce one consumed reference grant and one P update. No feedback, improvement, or budget exhaustion cannot grant. A stale version, altered receipt or duplicate commit is rejected; no partial writes occur.
- The next episode reads this P version, changing the frozen C program admitted by the external driver.
- Both a direct and a restarted run must produce deterministic results, and 96 baseline/96 adapted/24 dropped epochs must match T8 original scheduler source fingerprints **on full fwork only**.

## Nonpromotions and adversarial host

Reference grants are named `reference_v1_P_grants`, while `native_SPK_P_grants` remains zero. Reference semantic deliveries are named `reference_v1_semantic_receipts`, while native frozen BV semantic deliveries remain zero. **No native SPK learning or architecture promotion** is permitted.

A privileged host can provide a coherent counterfeit raw v0e source and manufacture an internally valid A judgment without running the scheduler. The reference P authority will accept it, exactly as a host-trusting simulator permits. Host rewrite/reseal of SQLite also remains possible. Independent producer/sensor authenticity requires a different trusted boundary; it must not be inferred from SHA hashes, a ledger, or separate processes.

## Required future native architecture work

- Define and implement a **new versioned tick-level scheduler** whose feedback event itself contains A's semantic assessment, rather than replaying a completed v0e trace.
- Implement native Memory Contract authorization and P-store transaction inside that new runtime, using explicit custody and memory target resolution. Do not reinterpret the frozen v0e message as v1.
- Show that native C PE computation reads updated native P and that a next native runtime tick reacts to it. Carry original v0e regressions forward unchanged.
- Extend beyond the three-node v0e topology via explicitly new admission contracts, not by smuggling a fourth node into v0e.
- Distinguish within-simulator causal effects from observed physical effects and authenticated sensor evidence.
