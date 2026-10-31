# SPK Memory Contract v0

Status: DRAFT
Baseline: spk-core-network-v0
Scope: Compiler v0 / Simulator v0

## 1. Purpose

Define the architectural memory model of SPK/*.

The contract specifies:
- logical memory domains and ownership;
- processing-element locality;
- access permissions and priorities;
- resource capacity and admission;
- contention and exhaustion semantics;
- configuration isolation and activation;
- externally observable behavior.

The contract is implementation-independent.

The simulator must reproduce and expose the
specified architectural behavior.

Host-language allocation and memory management
are outside the architectural specification.

Frozen Core v0 and Network v0 are unchanged.

## 2. Memory domains

P - Program Store
- Contains CoreConfig and CoreProgram definitions.
- Programs must not mutate during execution.
- Sharing immutable programs is permitted.
- Program size must be bounded at compilation.

S - State Store
- Each node owns an independent logical state.
- Persistent state: raw, last_timestamp.
- Transient Core guard belongs to one batch.
- Nodes cannot directly modify other node states.
- No silent numerical overflow is permitted.

E - Event Store
- Holds pending events, routed events and outputs.
- Event multiplicity must be preserved.
- Event ordering follows Network v0 semantics.
- Pending and generated events require budgets.
- No implicit event dropping or deduplication.

O - Observation Store
- Holds diagnostics, traces and measurements.
- Observation must not alter computational results.
- Observation buffering must be bounded.
- Observation resource exhaustion must not
  silently modify or truncate computation.

## 3. Memory ownership

A logical neuron owns its persistent state.

Multiple neurons may reside in one Processing
Element and share physical memory resources.

The active execution context owns its program
and topology version.

The event router owns pending event delivery.

Observation and candidate configuration storage
are logically isolated from active execution.

Memory sharing is permitted only when access
rights and observable semantics are preserved.

Logical isolation does not require a dedicated
physical memory bank for every neuron.

## 4. Compiler resource admission

Before execution, the Compiler must validate
the selected resource policy.

Static checks include:
- maximum node count;
- maximum edge count;
- maximum instructions per node;
- maximum output instructions per node;
- maximum outgoing fanout;
- maximum initial events;
- maximum permitted timestamp and delay values;
- maximum conservative emission bound.

Resource limits are external to the Core IR
and Network IR semantics.

A valid SPK program may be rejected for exceeding
the selected execution resource profile.

Such rejection does not imply semantic invalidity.

## 5. Conservative emission bound

Let:

B = configured maximum processed batches.

M = maximum number of CoreEmit instructions
    in any node program.

A conservative upper bound on emissions is:

    emissions <= B * M

This bound does not require knowledge of
whether CoreEmit guards will become true.

The Compiler admission step must reject an
execution profile when this upper bound exceeds
its declared output-event budget.

This bound is conservative, not an estimate
of the actual number of emitted spikes.

## 6. Architectural resource budgets

The machine exposes finite resource capacities.

Resource classes include:
- program storage capacity;
- state storage capacity;
- event-buffer capacity;
- output-buffer capacity;
- observation storage capacity;
- memory access bandwidth;
- service capacity per Processing Element.

Capacities may be local to a Processing Element
or shared across a defined hardware domain.

Active execution resources must be reserved
before admitting competing activities.

Available capacity may be borrowed by
lower-priority activities.

Borrowing must not invalidate active
execution reservations.

The architecture must define exhaustion
behavior for every finite resource.

No architectural guarantee may depend on
the memory allocator of the simulator host.

## 7. Numerical overflow

Core numerical state must remain within its
declared representation.

The existing Core validation remains authoritative.

No implicit wrapping or saturating arithmetic
may be introduced by Compiler or Simulator.

A Core state-range violation is an execution
failure, not a valid output.

## 8. Architectural resource exhaustion

The architectural machine distinguishes:

ADMISSION_REJECTED
- Required resources cannot be reserved.
- Execution has not started.

EXECUTION_LIMIT
- A declared computational limit is reached.

EXECUTION_ERROR
- A computational invariant is violated.

RESOURCE_EXHAUSTED
- A simulated architectural resource cannot
  satisfy the applicable capacity contract.

CONTENTED
- Access is delayed by competing requests.
- Contention alone is not execution failure.

For every execution failure:
- no complete successful result is reported;
- no spike is silently discarded;
- incomplete traces are explicitly identified;
- the failure origin is exposed if available.

Failure does not imply atomic rollback of
previously executed operations.

Host crashes or host out-of-memory conditions
are simulator failures, not SPK architectural
RESOURCE_EXHAUSTED events.

## 9. Access protection and backpressure

Every memory domain has explicit access rights.

An activity may access only its authorized
memory domains and execution epoch.

Memory access authorization is independent
of scheduling priority.

Finite event buffers may introduce backpressure.

Backpressure must be represented explicitly
in the architectural execution model.

It must not silently discard, duplicate
or alter the logical identity of spikes.

Canonical batching and multiplicity rules
of Network v0 remain authoritative.

If architectural progress cannot be guaranteed
under the selected resource policy, the machine
must signal the specified failure condition.

A finite resource system cannot guarantee
unlimited event acceptance.

## 10. Determinism and temporal domains

The architecture distinguishes:

EVENT_TIME
- Logical timestamps of SPK events.
- Governed by Core and Network semantics.

SERVICE_TIME
- Simulated memory and resource service cycles.
- Used to represent contention and latency.

Resource arbitration must not implicitly
rewrite EVENT_TIME timestamps.

Any future mapping from service latency
to event delivery time requires an explicit,
versioned semantic extension.

For equivalent inputs and configuration,
deterministic architectural policies must
produce reproducible execution results.

The simulator must expose both temporal
domains when service timing is modeled.

## 11. Architectural resource manifest

Each admitted configuration must expose:

- architecture profile identifier;
- Processing Element mapping;
- node and edge counts;
- instruction counts;
- memory-domain requirements;
- per-PE resource reservations;
- event and output buffer capacities;
- maximum static fanout;
- conservative emission bound;
- memory bandwidth assumptions;
- arbitration policy identifier;
- execution epoch identifier.

Resource units must be explicitly defined
by the selected architecture profile.

Physical byte sizes are not required until
the relevant machine encoding is specified.

The manifest is independent of the simulator
host memory layout.

## 12. Validation requirements

Required tests:

M01 - Program size admission
M02 - Node count admission
M03 - Edge count admission
M04 - Fanout admission
M05 - Static emission bound
M06 - Initial event budget
M07 - Core numerical overflow
M08 - Scheduler event limit
M09 - Scheduler batch limit
M10 - No silent event loss
M11 - Bounded observation storage
M12 - Observer non-interference
M13 - Architectural resource exhaustion
M14 - Explicit failure classification
M15 - Successful execution equivalence

## 13. Locality and memory mapping

SPK defines a Processing Element (PE) as
an abstract unit hosting computational state
and access to execution resources.

A PE may host multiple logical neurons.

Preferred logical placement:

P - Program memory local to the PE.
S - Neuron state logically private within the PE.
E - Event buffers near computation and routing.
O - Isolated observation storage.

Physical banks may be shared or partitioned.

Locality, capacity, bandwidth and latency
are independent architectural properties.

A future Compiler mapping stage must validate
resource placement and PE reservations.

The architecture does not mandate a specific
SRAM organization, cache or host-memory model.

## 14. Access permissions and arbitration

Permissions, priorities and service guarantees
are separate architectural dimensions.

Access roles:

EXECUTE
- Read active program and topology.
- Read/write owned runtime state.
- Consume and produce authorized events.

ROUTER
- Manage authorized event buffers.
- Preserve routing and multiplicity semantics.

VERIFY
- Read authorized state or snapshots.
- No implicit modification of active execution.

LEARN
- Read authorized observations.
- Write isolated candidate data.
- No direct mutation of active program memory.

REMODEL
- Build isolated candidate configurations.
- No direct mutation of active runtime state.

ACTIVATE
- Validate and authorize an epoch transition.
- Apply changes only at a defined boundary.

Illustrative service priority classes:

P0 - Active execution and essential validation.
P1 - Authorized configuration activation.
P2 - Online learning and candidate calculation.
P3 - Experimental verification.
P4 - Offline training and remodeling.
P5 - Extended diagnostics.

These are service classes, not Core opcodes.

Priorities govern contention for resources,
not logical ordering of SPK events.

Resource reservations take precedence over
opportunistic capacity borrowing.

Admitted P0 work requires bounded service
under the selected architecture profile.

Lower-priority progress guarantees, if any,
must be defined separately.

Priority inversion and starvation must be
explicitly modeled and tested.

A scheduling policy cannot promise bounded
service without capacity and workload bounds.

## 15. Operational modes and execution epochs

Operational modes:

EXECUTE
VERIFY_ONLINE
LEARN_OBSERVE
VERIFY_OFFLINE
TRAIN_OFFLINE
REMODEL_OFFLINE
ACTIVATE

An Execution Epoch identifies a coherent
active configuration of programs, topology
and associated computational parameters.

Candidates remain isolated from active epochs.

An active Core batch must be observationally
atomic with respect to configuration changes.

Physical suspension or resumption is allowed
when observable semantics remain unchanged.

An epoch transition requires an explicit
activation boundary.

Future online activation must define:
- state migration;
- pending-event handling;
- configuration version consistency;
- rollback or failure semantics.

The frozen Network v0 supports no active
program or topology hot-swap.

Its compatible activation boundary is the
start of a new execution.

Future dynamic activation requires a
separately versioned semantic extension.

Additional validation requirements:

M16 - Active program immutability
M17 - Memory ownership isolation
M18 - Reserved execution capacity
M19 - Priority inversion resistance
M20 - Background progress policy
M21 - Candidate version isolation
M22 - Activation boundary enforcement
M23 - Event ordering under contention
M24 - Per-PE capacity and bandwidth admission

These requirements are not yet implemented.

## 16. Compatibility

Core v0 and Network v0 remain frozen.

The present Network v0 defines functional
event execution but not physical memory
contention or PE-local service cycles.

Architectural memory simulation must be
implemented in a separate simulation layer.

That layer must not silently modify frozen
Core or Network semantics.

Any incompatible change requires explicit
versioning and independent validation.

The implementation language and host platform
are not architectural constraints.

## 17. Simulator conformance

The Simulator must eventually expose:

- active execution epoch;
- logical node-to-PE mapping;
- resource occupancy by domain;
- authorized and rejected memory accesses;
- arbitration decisions and service order;
- contention and simulated waiting cycles;
- event queue and buffer occupancy;
- resource exhaustion and backpressure;
- program and state transitions;
- emitted and delivered spikes;
- candidate validation and activation events.

These observations form a machine-readable
architectural trace suitable for future GUI
visualization and independent replay.

The trace must distinguish EVENT_TIME from
SERVICE_TIME whenever both are represented.

Tracing must not change the computational
result of a successful execution.

A simulator that only produces final network
outputs does not establish compliance with
the full architectural memory model.

The existing Network v0 is a functional
execution reference, not a complete
architectural memory simulator.

Additional tests:

M25 - Memory access permission enforcement
M26 - Deterministic arbitration replay
M27 - Event/service time separation
M28 - Resource occupancy trace consistency
M29 - Contention without semantic corruption

## 18. Acceptance

Status remains DRAFT until:

- architectural resource units are specified;
- static admission is implemented and tested;
- permission and arbitration semantics are tested;
- simulated exhaustion behavior is verified;
- traces are reproducible and independently checked;
- unavailable capabilities are explicitly declared.

Acceptance of the contract does not imply that
all architectural mechanisms are implemented.

