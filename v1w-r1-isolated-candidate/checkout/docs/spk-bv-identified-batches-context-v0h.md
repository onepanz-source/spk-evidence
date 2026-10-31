# SPK BV v0h – Identified Batches and Contextual Receptions

**Status:** RESEARCH CANDIDATE. Bounded logical executor only. Not a release, causal-merit estimator, learning engine, or hardware implementation.

## Motivation and inherited evidence

BV v0g intentionally rejected traces in which one neuron executed two separate input-ready groups during the same logical tick: `(node, tick)` was not a unique source batch identity. That ambiguity is real under shared-PE congestion. The v0g gate reproduced it explicitly. The 64-node convergence witness showed 528 feedback packets for 33 distinct assessment/receiver pairs; a repeated reception does not equal an independent vote, but it still consumes resources.

## v0h execution contract

- `batch_id` (`b1`, `b2`, ...) identifies one accepted input-ready group. Multiple batches in one neuron/tick **are permitted** and must have different IDs.
- `emission_id` (`e1`, `e2`, ...) identifies **each emitted output occurrence**. It is not just the channel name. Repeated EMITs of the same channel have different IDs.
- Forward routed occurrences reference **both** their source `batch_id` and `emission_id`. They preserve their full input-occurrence parent set.
- Terminal outputs reference their output emission identity. Feedback assessments reference the batch and terminal emission which led to the local observation.
- Feedback packet identity, assessment identity, arrival times, evidence IDs, PE mapping, resource credits, and deduplication behavior remain as in the v0f executor.
- The new scheduler is a copy-on-write *research successor*. The frozen v0f scheduler, Architecture v1 and A3d are not edited. A reference comparison strips only new identity fields and checks the remainder of the v0h result is exactly equal to v0f for multiple topologies, priorities and congestion profiles.
- A read-only audit reconstructs batch membership, source output occurrence, route multiplicity including parallel edges, received input-ready groups, assessment anchors, feedback return custody, and shared service/transport/memory accounting. Forged, missing, duplicate or inconsistent identities are denied.

## Contextual aggregation: observation, not traffic compression

A separate **read-only** function groups actually delivered feedback by `(assessment_id, receiver)`. Every packet ID, sender and causal evidence set is retained. It records first/last tick and path multiplicity. `n` paths to the same receiver for the same assessment remain **one recipient observation**, not `n` independent votes. This layer does not suppress packets, shorten routes, reduce actual cost, calibrate confidence, prove causal credit or promote a program. The cost ledger still accounts for all 528 packets in the large convergence witness.

## Open problems and safety of interpretation

1. Input occurrence is *membership in a batch*, not proof that it caused the particular output.
2. Correlated evidence at different recipients may remain statistically dependent. Grouping by receiver is not an independence guarantee.
3. The scheduler's abstract finite-capacity global clock, atomic memory reservation, event fragment and PE model are unchanged. No physical performance or power claim follows.
4. Feedback cannot yet change a neuron's active program. Counterfactual validation against an independent task objective remains future work.
5. True compression would need an online transport protocol with bounded buffering, causal-equivalence proofs, explicit aggregation delay and revalidated fairness; this research phase provides its measurement baseline only.

## Accept / reject

The gate requires: new identity/audit tests, negative controls against forged metadata, old v0f behavior equivalence, ten independent-process replay scenarios (including the formerly ambiguous same-tick case, a quiet recurrence, parallel routes, and 64 nodes), frozen-source guard, and inherited BV functionality. The six legacy Git custody tests bound to the `spk-architecture-v1` release branch remain outside the research suite and are neither altered nor counted as passed.
