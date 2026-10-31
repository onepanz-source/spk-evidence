# SPK Event Buffer Capacity Audit v0

Status: DRAFT — S3.6a experimental component
Baseline: frozen SPK Core v0 and Network v0
Dependencies: S3.3 Event Provenance, S3.5 Causal Service Scheduler

## 1. Scope

Audit resource occupancy of E-domain event buffers in a *completed*,
finite, causally scheduled SPK workload. This is post-hoc **SERVICE_TIME
replay**, not live event scheduling or a proof of admission.

An event slot represents one unconsumed spike occurrence, not one
unique `(timestamp, node_id, channel)` triple. Parallel deliveries retain
multiplicity. E-domain storage is counted as a **shared finite event-slot
budget per Processing Element** (`ProcessingElementV0.event_slots`).

The audit does not use Python's host-RAM consumption as its resource model.

## 2. Preloaded initial events

Every externally supplied initial event is considered resident at
SERVICE_TIME boundary 0. This v0 assumption is conservative and may
reject workloads that could run under a separately defined incremental
external-ingress policy.

This preloading does **not** assign an EVENT_TIME to SERVICE_TIME, or
specify physical arrival latency. External input service costs are not
accounted in S3.6a.

## 3. Routed events

A routed event occupies one slot on its destination PE at the SERVICE_TIME
completion boundary of its `ROUTE_ENQUEUE` transaction.

Routed events may have a future EVENT_TIME delivery timestamp. This v0
model keeps them resident in the same E-domain budget until their batch
consumes them. Hardware-specific delay queues are not modeled.

## 4. Consumed events

A completed `BATCH_CONSUME` transaction releases exactly the multiplicity
of its corresponding batch. The destination node is reconciled against
Event Provenance v0; any associated routed request must have completed
at a strictly earlier SERVICE_TIME boundary.

No event is deduplicated or silently discarded.

## 5. Same-boundary convention

If consumption and routed enqueue transactions complete at the same
SERVICE_TIME boundary, completed consumption frees slots before routed
enqueue consumes slots. This is an explicit resource-accounting convention,
not a statement of SRAM access order, cache coherence, or partial batch
execution. The resulting occupancy must be within the PE's capacity.

## 6. Failure semantics

If occupancy would exceed the PE's declared `event_slots`, the audit
raises `EventBufferOverflowV0` with the PE, service boundary, required
slots and capacity. It returns no successful partial audit result.

The existing causal schedule is **not** rewritten to avoid overflow.
No automatic backpressure, admission retry or overflow recovery exists.
A replay failure does not by itself prove that no feasible schedule exists.

Invalid request, completion, provenance or target mappings are rejected.

## 7. Conservation

For the completed finite trace:

    initial_occurrences + routed_occurrences = consumed_occurrences

All event buffers must be empty at the end of a successful audit.
The result records occupancy transitions and peak occupancy per PE.

## 8. Temporal separation

`EVENT_TIME` remains the functional Network v0 logical timestamp.
`SERVICE_TIME` is the boundary index of completed memory-service requests.
No conversion between them is defined by this audit.

## 9. Explicit exclusions

- Dynamic arrival-time modeling for external inputs
- Physical event ingress bandwidth / reservations
- Runtime backpressure or recovery from overflow
- Runtime enqueue/dequeue during live neuronal execution
- Separate interconnect, delay queues, channel-specific bank capacity
- Output and observation-buffer occupancy
- Persistent state/program memory contention
- Real hardware timing estimates

## 10. Acceptance

- Deterministic occupancy replay
- Correct initial preloading and overflow detection
- Routed enqueue only upon service completion
- Event consumption only after routed dependencies complete
- Strict PE capacity accounting and per-PE peak recording
- Conservation of individual event occurrences
- Explicit rejection of missing completions / inconsistent provenance
- Empty-workload and independent service-bandwidth cases

The audit assumes the upstream provenance and causal scheduler are trusted
components; it is not an independent cryptographic or formal verification
of those inputs. Real Network end-to-end integration remains a separate gate.
