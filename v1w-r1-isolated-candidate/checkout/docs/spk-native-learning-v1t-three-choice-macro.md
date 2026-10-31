# SPK Native Learning v1t: bounded three-choice endogenous PE learning

**Release candidate.** The original Core/PE/BV and v1/v1r/v1s remain frozen. A new versioned scheduler `generalized_scheduler_v1t` is an additive fork of v1r.

## One macro, six integrated contracts

1. Three genuine candidate C PE programs emit `11`, `12` or `15` in the **same PE/BV scheduler**. Candidate map: C→B target channels 1/2/5, B→A 3/4/6.
2. Original PE `_compute_local` runs A's finite comparator for every candidate, emitting `21` positive or `22` negative plus structural assessment `7`. **The host sets the declared goal**, but does not provide a per-tick verdict.
3. Negative A verdict transported by BV A→B→C rotates C's next candidate deterministically `11→12→15→11`. Positive feedback never changes P. This is finite exploration, not gradient learning or optimal policy induction.
4. Each same-tick P transition requires original resource admission, exact causal occurrence ancestry, P version CAS and budget. The *next* real C PE computation consumes the updated program.
5. SQLite durable replay, deterministic all-tick recomputation, advisory flock, P continuity and crash recovery generalized from v1s to three candidates. Existing binary v1s store is never migrated or opened by v1t.
6. Independent nine-pair acceptance, three epoch P0→P2→P2→P3, seven restart cuts, adversarial mutation and frozen-original BV parity when learning disabled.

## Scope and exclusions

Still 3 nodes A/B/C, a finite known list of 3 programs and a predeclared goal in A's program. `P` version and grant count are identical under this bounded CAS reference. Input and outcomes are synthetic; no physical sensor or independent goal issuer. No N-node/distributed safety, stochastic dynamics, irreversible external effects, cryptographic host resistance, hardware efficiency or general program synthesis. SQLite genesis replay may recompute expensive workloads. POSIX flock is cooperative only. Original BV-v0e does **not** learn; only the new v1t scheduler learns within this bound.

## Promotion and regression gate

Prerequisite: verified v1s report SHA `af6c8323cc23f3eee8471751027532abd6919b6e7e6d325217acd3a03e679067`. Original frozen PE/BV hashes and original v1r/v1s manifests must match exactly. Gate denies existing output and test-only execution. The genuine v1t conformance invokes the frozen PE and BV source. Run the shell gate once, and only if it emits the final PASS, the release is accepted on fwork.
