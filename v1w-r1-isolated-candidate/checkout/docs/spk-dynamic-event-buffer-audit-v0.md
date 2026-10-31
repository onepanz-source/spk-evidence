# SPK Dynamic External-Ingress Buffer Audit v0

Status: DRAFT - S3.6b/3 experimental component
Baseline: frozen SPK Core v0 and Network v0
Dependencies: Event Buffer Audit S3.6a, External Ingress S3.6b/1,
Release-aware Scheduler S3.6b/2.

## Scope

Extend the post-hoc audit of E-domain PE event-slot occupancy with
per-occurrence external arrival boundaries. This audits a completed finite
service schedule; it does not generate events or apply backpressure.

### Compatible legacy mode

`audit_event_buffers_v0(..., ingress=None)` preserves S3.6a: all initial
spikes are preloaded at SERVICE_TIME boundary zero. A valid explicit
zero-boundary ingress produces identical results to legacy mode.

### Explicit ingress mode

`ingress=ExternalIngressBindingV0(...)` requires every initial event
occurrence to be bound exactly once. The audit re-derives the binding
from the original events, plan, and provenance. It rejects mismatched
indices, node/channel/event timestamp, target PE, consume ID and release
boundaries. The first slice of each affected BATCH_CONSUME transaction
must be at or after every associated arrival boundary.

At a SERVICE_TIME boundary `t`, apply completed consumptions first,
then routed enqueues and external arrivals. All enqueues consume slots
at the specified boundary. Capacity is checked after the complete
boundary transaction group; temporary physical-port ordering is NOT
modeled. This reuses S3.6a's same-boundary convention.

An external spike arriving at boundary `t` can first participate in
service tick `t`, so its BATCH_CONSUME cannot complete before boundary
`t+1` under the release-aware scheduler.

Per PE and boundary, `external_enqueued` records arrivals, not preloads.
The audit records the PE peak occupancy across boundaries and rejects
an overflow with `EventBufferOverflowV0`. Successful results conserve
all external + routed event occurrences and finish with zero occupancy.

## Separation of time domains

`EVENT_TIME` remains unchanged and is never inferred from
`SERVICE_TIME`. EVENT_TIME order is the functional reference; the
service audit merely accounts for storage and accesses.

## Limits

- Buffer audit remains post-hoc, not a live simulator.
- No admission/backpressure, ingress bandwidth or bus/arbitration costs.
- No delayed-reservation, independent routed queue, packetization or
  credit-based inter-PE flow control.
- Successful replay does not prove feasibility on a physical memory.
- Auditing a forged externally constructed schedule is not authentication.

## Acceptance

- Old S3.6a tests remain green.
- Explicit zero arrivals reproduce legacy occupancy exactly.
- Staggered arrivals can reduce false preload-only overflow.
- Parallel and duplicate spikes retain per-occurrence counting.
- Same-boundary external and routed arrivals share PE event slots.
- Early consumption, forged binding and over-capacity reject explicitly.
- Deterministic replay, event conservation, empty workload and no
  implicit EVENT_TIME to SERVICE_TIME conversion.
