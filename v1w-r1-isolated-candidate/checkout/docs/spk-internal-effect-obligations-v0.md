# SPK Internal Effect Obligations v0

Status: EXPERIMENTAL / NON-FROZEN. Phase S3.7d/3b2b2k/1.

## Scope

The service request has metadata (intent kind, PE, target, epoch, quantity,
service units) but **no proof of the actual memory operation**. The Service
Quantum's awaiting-confirmation state proves only that service work was spent.
This module joins the logical plan, the requests and the service lifecycle,
rejects target/epoch/owner mismatches and lists which *real effect witnesses*
are still required. **It never issues confirmation IDs.**

| Intent | Target domain | Space | Required witness |
| --- | --- | --- | --- |
| PROGRAM_REFERENCE | PROGRAM | ACTIVE | PROGRAM_READ |
| STATE_LOAD | STATE | ACTIVE | STATE_READ |
| STATE_COMMIT | STATE | ACTIVE | STATE_WRITE_WITH_TRANSITION |
| OBSERVATION_RECORD | OBSERVATION | ACTIVE | OBSERVATION_APPEND |
| OBSERVATION_READ | OBSERVATION | ACTIVE | OBSERVATION_READ |
| SNAPSHOT_READ | Target-defined | SNAPSHOT | SNAPSHOT_READ |
| CANDIDATE_PROGRAM_WRITE | PROGRAM | CANDIDATE | CANDIDATE_PROGRAM_WRITE |

The last two kinds are not authorized merely by binding: snapshot and candidate
lifecycle policies remain separate, future work. Storage-effect kinds
`BATCH_CONSUME`, `EMISSION_RECORD`, and `ROUTE_ENQUEUE` remain outside this gate.

## Evidence source (still missing)

Future read evidence must come from an actual versioned program/state/observation
memory image. STATE_COMMIT must be compared with the real, causally ordered
state transition of the frozen Network execution. OBSERVATION_RECORD must be
trace-bound, not fabricated by the service scheduler. A returned obligation
must NOT be passed to `confirmed_request_ids` as evidence.

## Invariants

- No implicit `EVENT_TIME` to `SERVICE_TIME` conversion.
- No semantic state update inferred from service unit exhaustion.
- No silent acceptance of unknown target, PE, epoch or wrong memory domain.
- A `UNVERIFIED_CONFIRMED` classification is a warning, NOT retroactive proof.
- Does not mutate the frozen Core/Network/Compiler interfaces.

## Roadmap

Next: identify an authoritative, versioned internal memory image and bind
actual program/state transitions from ObservedExecutionV0; then implement
replayable effect receipts, and only then integrate these with the autonomous
service loop. Avoid treating the classifier as the Internal Effect Authority.
