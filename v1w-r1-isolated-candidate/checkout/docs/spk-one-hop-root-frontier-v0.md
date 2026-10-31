# SPK S3.7d/3b2b2k/17: One-Hop Root Frontier Audit v0

## Scope and contract

This is a **read-only prerequisite audit** for a candidate destination `(node, EVENT_TIME)` directly downstream from source neurons. It does not execute Core, create dynamic batches, activate staged requests, grant EVENT capacity or authorize `BATCH_CONSUME`.

All incoming topology edges are considered, including duplicates/parallel edges. For each incoming edge `source -> target` with delay `d` and queried destination EVENT_TIME `t`, the required source cutoff is `t - d`. A negative cutoff is vacuous because v0 disallows negative event times. Otherwise, the source must be a root with a positive certificate **recomputed** via `analyze_owned_root_emission_frontier_v0(...)` over the **same owned state**, including sealed external ingress, authenticated EVENT consumptions, and Core commit history. No caller-authored source watermark is accepted.

A separate `analyze_owned_external_prefix_v0(...)` confirms all finite, sealed external input occurrences targeting the destination with EVENT_TIME <= `t` are accounted. At `t` exactly, already-consumed external occurrences are detected as history, not offered for another batch. The stored routed occurrences from the **existing static routing manifest only** are inspected separately, distinguishing `OUTPUT`, `EVENT`, `CONSUMED` and not-yet-resident. Provenance and resource checks are delegated to the existing validators.

Even when these checks all pass, the result is only `ONE_HOP_STATIC_PRECONDITIONS_MET`. **It is not a destination batch-closure certificate.** Both result and per-destination evidence retain `supports_consume_admission=False`.

## Trust boundaries

1. The external schedule is an explicit immutable, finite epoch seal; this does not apply to live/open ingress.
2. The inspected boundary is the one embedded in the owned `OwnedInternalReadStateV0`; no separately supplied storage snapshot or claimed cutoff is accepted.
3. A static `RoutedBindingManifestV0` is *not* an exhaustive record of all future Core-derived dynamic routes. Absence of a known static route is not evidence that future dynamic routes cannot exist.
4. The root frontier authority and historical P/S/EVENT/Core audit provide source cutoffs only for nodes with **zero incoming edges**. An upstream non-root source is not certified by this component, except for vacuous negative cutoffs.
5. A known routed occurrence being physically resident is not by itself a proof that every Core emission was registered. The global single-owner dynamic request/route ledger must later provide that proof.
6. EVENT_TIME frontiers are never inferred from SERVICE_TIME, idle time, or a fixed retry count.

## Status interpretation

- `NO_INCOMING_EDGES`: query outside one-hop destination scope.
- `NONROOT_SOURCE_UNPROVEN`: some nonvacuous upstream cutoff requires inductive (multi-hop) proof.
- `ROOT_SOURCE_PREFIX_PENDING`: owned root source cutoff failed or is incomplete.
- `EXTERNAL_PREFIX_PENDING`: an external occurrence within the prefix is not accounted.
- `EXTERNAL_SAME_TIME_PENDING`: an exact-time external occurrence is not available.
- `EXTERNAL_SAME_TIME_ALREADY_CONSUMED`: historical external occurrence must not be re-admitted.
- `STATIC_ROUTE_ALREADY_CONSUMED`: historical static route must not be re-admitted.
- `STATIC_ROUTE_NOT_RESIDENT`: at least one manifest route for the queried destination/time is still STAGED or OUTPUT.
- `ONE_HOP_STATIC_PRECONDITIONS_MET`: the checked source-root and static-delivery prerequisites hold; **closure is still unproven**.

## Verification

`python -m pytest -q tests/test_one_hop_root_frontier_v0.py`

This candidate adds 37 tests: nontrivial one-hop topologies, parallel edges and delays, vacuous early cutoffs, blocked static deliveries, sealed pending ingress, real committed external consumption, malformed/altered seal, incomplete commit history, deterministic read-only behavior, type enforcement, and non-admission invariants.

Expected test total on fwork after S3.7d/3b2b2k/16: **2059**.

## Next acceptance gate

Build a single-owner, monotonic dynamic route registry that is causally bound to **actual** atomic Core state/output commits and reconciled against controller storage. Only then combine inductive source frontiers, exact ingress state, and an exhaustive ledger to issue a dynamic batch-closure certificate. Until that is established, any nonempty `BATCH_CONSUME` derived from this module would be unsafe.
