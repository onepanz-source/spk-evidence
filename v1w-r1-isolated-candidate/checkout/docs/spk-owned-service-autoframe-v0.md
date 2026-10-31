# SPK S3.7d/3b2b2i: Storage Auto-Frame v0

Status: DRAFT, for verification against the real SPK repository.

## Scope

Generate `BackpressureServiceFrameV0` from an immutable, already-owned
`OwnedServiceTickStateV0` and causal service graph. No caller-provided completion,
route-ready, admission, or ingress-arrival list is accepted. The generated frame
is passed unchanged to the existing `advance_owned_service_tick_v0` path; real
storage effects are validated by Service Effect Authority and the bounded
boundary controller. The returned frame is retained for reproducible audits.

This is **a frame generator for storage-effect service only**, not yet a complete
SPK network scheduler. Other memory intent types are not authenticated here.

## Sources of authority

| Generated frame field | Authoritative source |
|---|---|
| `new_ready_emission_ids` | Finished `EMISSION_RECORD` plus active OUTPUT start reservation |
| `new_ready_route_ids` | Source OUTPUT resident, unsubmitted route, prior completed causal predecessors |
| `route_commits` | Finished `ROUTE_ENQUEUE` with a live destination EVENT reservation |
| `route_consumptions` | Finished `BATCH_CONSUME` with *all* routed occurrences physically resident |
| `external_consumptions` | Same finished batch, *all* external occurrences physically resident |
| `external_arrivals` | Bound external occurrences due at the exact SERVICE_TIME boundary |

No spike payload or `EVENT_TIME` is synthesized. Parallel edges have distinct
route request IDs. Emission/publication and route submission are conservatively
separated by at least one service boundary if the output becomes resident in the
current transition. A consumption of mixed routed/external inputs is all-or-none.

## Contracts

- Source of ROUTE start: **pre-boundary OUTPUT state** only.
- Source of memory effect completion: **finished service work plus real storage**.
- Internal/non-storage service completions: unsupported and rejected explicitly.
- Missing old ingress: rejected instead of silently treated as late.
- Future ingress: never injected early and never inferred from EVENT_TIME.
- Mutable/duplicate input identities: rejected or checked by downstream owners.
- `BackpressureServiceFrameV0` is a derived diagnostic artifact, not caller
  evidence or new storage.
- Failed tick: immutable state is not partially changed.

## APIs

```python
frame = derive_owned_storage_frame_v0(
    architecture, manifest, admission, requests, graph, state,
    ingress=ingress,
)
result = advance_autoframed_owned_tick_v0(
    architecture, manifest, admission, requests, graph, state,
    ingress=ingress,
)
# result.frame is the generated frame; result.result.state is the next state
```

## Acceptance gates

AF01 Frame generation without external completion lists
AF02 Atomic emission requires prior OUTPUT grant
AF03 Route start requires pre-boundary source OUTPUT and causal readiness
AF04 Route commit requires finished service and EVENT reservation
AF05 Batch consume requires all bound routed and external residents
AF06 Arrival at declared SERVICE_TIME, never EVENT_TIME conversion
AF07 Determinism, canonical IDs, no replay
AF08 Memory overflow remains fail-closed; no hidden queues
AF09 Positive multi-tick routed execution and external ingress
AF10 Congestion can remain waiting, without false deadlock claims
AF11 Unsupported internal service effect is rejected
AF12 Frozen Core, Network and Compiler components untouched

## Limitations and next work

- This implementation does not synthesize internal program/state/observation
  completion receipts. Real traced networks may include those requests.
- The caller still invokes exactly one tick at a time. A bounded run loop and
  rigorously justified progress/stall classification belong to subsequent steps.
- Successful replay on a small storage-only fixture is not proof of global
  deadlock freedom or architectural feasibility for arbitrary workloads.
- The local integration harness includes reduced substitutes for some frozen
  contracts: actual acceptance requires running the complete repository tests
  on fwork.
