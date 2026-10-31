# SPK S3.7d/3b2b2h — OUTPUT-authorized Service Tick v0

Status: EXPERIMENTAL / before fwork verification.

## Scope

A pure, serialized **one-boundary composition** of existing SPK modules:

1. `Causal Service Frontier` classifies candidate `EMISSION_RECORD` requests.
2. `Output Start Reservation` grants entire atomic fan-out bundles **against the pre-boundary snapshot**.
3. `Service Effect Authority` advances the bounded backpressure driver and witnesses completed storage effects.
4. Successful `OFFER` effects settle the old `OUTPUT` start reservations, replacing the claim by physical residents. Invalid claims fail closed.
5. `Causal Service Frontier` rejects premature route submissions; `Service Quantum` spends per-PE service units only with derived grants and authenticated effect completions.
6. All updated owner state is returned immutably; exceptions return no new snapshot.

The module neither changes nor reinterprets the frozen SPK Core v0, Network v0 or Compiler v0 contracts. `EVENT_TIME` is never transformed into `SERVICE_TIME`.

## API

- `OwnedServiceTickStateV0(boundary, output)`
- `advance_owned_service_tick_v0(architecture, manifest, admission, requests, graph, state, frame, *, ingress=None)`
- `OwnedServiceTickResultV0(service_boundary, output_start_decision, authenticated_effects, quantum, state)`

Inputs `frame` remain explicitly supplied by the caller. It declares proposed storage effects (`new_ready_emission_ids`, `route_commits`, etc.), **not** independently authenticated service completions. The Service Effect Authority rejects storage effects lacking finished service, and ledger checks reject emission publication without an earlier OUTPUT start grant.

## Admission and timing policy

- Ready emission group G at boundary s requires an uncompleted causal dependency graph, an admitted atomic fan-out, and finite available `OUTPUT` slots.
- Allocation follows canonical emission request IDs; each grant claims the whole group, never a fraction.
- `OUTPUT` availability is measured before applying the boundary-s storage transitions. Space freed during boundary s may enable a new service start at **s+1**, not at s.
- An active grant remains charged while emission work is partial, finished-but-unconfirmed, or submitted to driver backpressure.
- Successful, witnessed publication removes its `OUTPUT` grant and occupies physical `OUTPUT`. Route transfers and later consumption retain event multiplicity and identity through existing ledgers.
- Route reservations are independently authorized by the existing route arbiter, not by an OUTPUT grant.
- No event is silently lost, duplicated, or deduplicated; all memory capacity claims remain finite.

## Failure semantics

- `OUTPUT` overcommit / invalid grants: explicit error or blocked emission decision.
- Premature emission effect (no earlier grant or no finished work): explicit error.
- Premature route submission against DAG: explicit error.
- Corrupted ledger or mismatch among driver, quantum and OUTPUT claims: explicit error.
- Ingress requiring a release binding must be passed explicitly.
- No state mutation on an exception because every transition is pure and immutable.

## Explicit limitations

- This is **not** the autonomous multi-cycle scheduler. Callers still submit a `BackpressureServiceFrameV0` for each boundary, including effects they claim have occurred. The authority validates storage effects, but does not synthesize the frame.
- No independent authentication of a caller's initial `ServiceQuantumStateV0` or upstream work history. A trusted bootstrap and single persistent owner are still needed.
- Internal/non-storage access kinds still require future completion authority. This module does not conjure `PROGRAM_FETCH`, `STATE_COMMIT`, or other internal confirmations.
- No interconnect bandwidth model, hardware atomic operations, progress guarantees or deadlock proof.
- Tick/resource claims are simulation time, not Python host memory occupancy.

## Verification

`python -m pytest -q tests/test_owned_service_tick_v0.py`

Then run `python -m pytest -q` on the actual fwork SPK repository. The control-environment tests are not substitutes for the repository-wide gate.
