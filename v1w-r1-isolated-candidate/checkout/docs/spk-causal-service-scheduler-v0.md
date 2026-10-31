# SPK Causal Service Scheduler v0

Status: DRAFT - implementation under validation
Baseline: spk-core-network-v0

## 1. Purpose

Assign architectural SERVICE_TIME to a finite,
previously constructed graph of memory requests.

The scheduler does not execute Core instructions,
create neuronal events, or mutate memory.

## 2. Inputs

- ArchitectureProfileV0
- Authorized MemoryServiceRequestV0 collection
- AccessDependencyGraphV0
- ArbitrationPolicyV0
- Maximum service-tick budget

All requests and dependencies must be known
before scheduling begins.

## 3. Readiness

A request without predecessors is initially ready.

A dependent request becomes ready only after
every predecessor has completed.

A completion at service tick s enables its
successors no earlier than service tick s+1.

A completion_tick value of k indicates that
the transaction completed at the boundary
after service ticks 0 through k-1.

## 4. Arbitration

Each PE has an independent service budget.

Requests compete on the PE containing the
target resource.

Priority comes from the declared arbitration
policy and the authorized activity.

Same-priority ties are resolved deterministically
using principal_id and request_id.

Incomplete requests may receive more service
in later ticks.

Higher-priority newly ready requests may
preempt incomplete lower-priority requests
at service-tick boundaries.

## 5. Service conservation

For each request:

sum(granted_units) = service_units

No request is completed before all required
service units have been granted.

For each PE and service tick:

sum(granted_units) <= accesses_per_service_tick

All admitted requests must complete or the
simulator must report an execution limit.

## 6. Parallelism

Independent PEs may serve requests concurrently.

The scheduler imposes no global ordering
between independent requests beyond its
deterministic output-record ordering.

Interconnect contention is not modeled.

## 7. Temporal domains

EVENT_TIME is preserved without modification.

SERVICE_TIME does not represent neuronal
spike propagation delay.

No conversion between EVENT_TIME and
SERVICE_TIME is defined in v0.

## 8. Functional reference

Network v0 is the independent functional
execution reference.

The current integration constructs access
requests from a completed functional trace.

Consequently it is an architectural
service replay, not live neuronal execution.

## 9. Trust boundary

The scheduler assumes input requests were
obtained through authorized transaction mapping.

The scheduler is not an authentication
or access-control authority.

## 10. Exclusions

Not implemented:

- runtime event arrivals;
- dynamic request creation;
- external input service;
- bounded event-buffer occupancy;
- backpressure;
- memory banking;
- interconnect arbitration;
- instruction execution latency;
- starvation guarantees for unbounded workloads;
- execution-epoch activation.

## 11. Conformance

Required checks include:

- predecessor completion barriers;
- same-PE and cross-PE dependencies;
- capacity limits;
- priority arbitration;
- tick-boundary preemption;
- deterministic replay;
- EVENT_TIME immutability;
- independent PE progress;
- service-unit conservation;
- exact execution-budget boundaries;
- equivalence with A4 for dependency-free inputs.

Passing finite tests does not establish
general formal equivalence.
