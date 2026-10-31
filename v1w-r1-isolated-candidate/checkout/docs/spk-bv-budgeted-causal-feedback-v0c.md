# SPK Back Validation v0c: simulator-anchored, budgeted causal-feedback sidecar

**Status: RESEARCH CANDIDATE**. Not frozen, not production, not hardware, not in-simulator BV delivery, not adaptive learning.

## Aim and boundaries

BV v0b used actual frozen Network v0 execution and three A1b PE placements but reported `feedback_messages=0` since no return message was delivered. This extension creates a **separate executable sidecar** that schedules feedback packets in reverse order over event routes observed from the frozen engines. All work stays outside frozen `spk_*` modules. This is not an integration into A3d's service/backpressure, and sidecar admission budgets do not reserve PE or physical memory.

Frozen source: `spk-architecture-bounded-reference-v1`, commit `5af99cd1f4d603bf0c8e1557a6561c107765fdb5`.

## Controlled actual simulator experiment

Three neuron topology `A --(ch7→ch0, delay1)--> B --(ch7→ch0, delay1)--> C`; B and C execute the frozen relay program. A executes either `ACC; SHIFT; CMP; EMIT; RESET` or `SHIFT; ACC; CMP; EMIT; RESET`. Same initial states (0) and paired external event (one at A, timestamp 1..16). Every arm executes frozen Network v0 and each of the three A1b PE layouts, requiring identical observed projections. No training occurs and the program is changed manually as an intervention.

For the candidate arm, observed spike routes are identified with unique occurrence IDs `r1: A→B` and `r2: B→C`, with a witnessed `r2.parent_ids=['r1']`. Only after C emits a terminal response does an assessment originate at C. The BV v0 validator checks provenance, temporal consistency, program identity, observers and legal parent paths. **C→B** is a direct return on r2, followed by **B→A** on r1. These *two* feedback transmissions are executed by the new sidecar, not the Network/A1b engines.

For the baseline arm no spike route exists and therefore no return messages are fabricated. The 16 deterministic pairs require 128 Network/A1b simulator executions and 32 feedback messages in the sidecar.

## Budgets and ledger

Explicit parameters: max messages, enumerated causal paths, hop count, elapsed ticks, feedback operations, abstract memory accesses, peak in-flight packets, hop latency, and messages/link/tick. Admission is fail-closed: any exhaustion raises and returns no partial report. Each assessment charges one abstract operation and memory access; each emitted feedback packet charges three operations (send, receive, route check) and two memory accesses (store/load). A fixed four-word-per-packet proxy is recorded. These are **defined abstract accounting rules** for comparison; not measured instructions, memory transactions, joules, PE cycles or physical bandwidth.

Candidate arm per pair: 2 feedback messages, 7 abstract feedback operations, 5 abstract memory accesses, 8 notional words, peak 1 packet in flight. Feedback resource costs remain **separate** from the frozen runtime's event/execution cost and the external context-credit evaluator. No claim of end-to-end energy efficiency is made.

## Convergent histories and consensus

The frozen BV v0 fixture with `A --two parallel edges--> B --> C` is used **only as a synthetic structural adversarial stress case**, not as a Network/A1b execution. It produces an assessment from C along r3; upstream two parallel parent routes r1/r2 are bundled into one physical B→A sidecar packet retaining both route IDs. Hence **paths are never counted as independent observer votes**. Different assessment IDs remain distinct; saturating link/tick capacity serializes their packets. Further aggregation for arbitrarily re-entrant networks remains research.

## Evidence and limitations

A canonical SHA-256 report stores source program and frozen observed projection identities, PE placement digests, validated BV trace, delivered packet schedule and budgets. A separate Python verification process reruns all 128 frozen engine executions and reconstructs the entire sidecar ledger. A forged document with its outer hash recomputed is rejected by the independent replay. This assumes trusted checked-in source and is not a cryptographic protection against a hostile host.

Limitations: BV feedback remains sidecar-only, not actually integrated into frozen A3d service; three nodes only; derived occurrence identities are from read-only observer callbacks, and parent links are unambiguous *only for the controlled admitted fixture*. A BV assessment carries a synthetic local metric, not proved causal truth. No autonomous candidate synthesis, context inference, global merit learning, staging, promotion, online learning or energy measurements are present. The 16 cases are timestamp variants, not independent statistical samples. The inherited synthetic contextual-credit results are not new experiments on generalization.

**Next step:** connect a BV service to a *new* N-neuron experimental scheduler under separate resource budgets, with explicit security/authority policies and independent oracle; no modifications to frozen Architecture v1.
