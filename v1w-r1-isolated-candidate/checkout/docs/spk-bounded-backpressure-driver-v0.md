# SPK S3.7d/3b2b2b: Bounded Multi-Boundary Retry Driver v0

Status: candidate for verification on fwork.

A deterministic, pure SERVICE_TIME boundary sequence coordinator above the
frozen SPK Core, Network and Compiler v0 interfaces. The driver retains *only*
identities of not-yet-published atomic emissions and resubmits them at the next
SERVICE_TIME boundary. Previously denied ROUTE_ENQUEUE reservations continue to
be retained by `BackpressureArbiterStateV0`. Spike occurrences are never held
in these pending identity lists: their storage ownership is the upstream
uncompleted emission or the finite OUTPUT/EVENT buffers already modeled.

## Boundary contract

- Explicit consecutive SERVICE_TIME boundaries: 0,1,2,... (or continue from
  the preceding controller snapshot). No SERVICE_TIME from EVENT_TIME.
- The caller attests which emissions/routes become causally ready and which
  routing, consumption and external-arrival service actions have completed.
- A blocked atomic emission is retried automatically, without republishing a
  previously admitted group or partially publishing a denied group.
- An originally admitted emission's route occurrence identities must remain
  accounted for as OUTPUT, EVENT or consumed, subject to existing manifest.
- A previously submitted emission or route cannot be declared newly ready
  again. Retry ownership remains with the driver and arbiter, respectively.
- Non-backpressurable external arrivals are accounted at their due boundary;
  failures abort the call without mutating the input state.
- The maximum number of supplied frames is finite; exhausting it is a limit
  error and **is not evidence of deadlock**.
- Status `WAITING` only means outstanding work and no successful transition
  on this boundary. It does not prove a wait cycle or lack of future progress.

## Deliberately absent

This is **not yet a scheduler**. It does not assign PE service units, validate
causal predecessors, authenticate caller-supplied completions, invent missing
future service events, or infer deadlock. A further scheduler integration must
connect its input frames to the real AccessDependencyGraphV0 and PE service
capacities, then prove that no service begins before its preconditions.

Retained identities / completed tombstones are simulation diagnostic metadata;
no unlimited architectural event storage or payload queues are introduced.
