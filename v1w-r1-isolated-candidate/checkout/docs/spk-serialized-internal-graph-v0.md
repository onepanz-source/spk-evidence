# SPK S3.7d/3b2b2k/5 — Serialized Internal Service Graph v0

## Motivation

The validated Owned Internal Reads owner may finish STATE_LOAD for a later batch
of the *same neuron* before STATE_COMMIT for the preceding batch. A real commit
then invalidates the read's version and would force the owner to fail closed.
No amount of successful replay tests proves this is safe.

## Contract

A pure deterministic transform `serialize_internal_access_graph_v0` produces a
canonical AccessDependencyGraphV0 from genuine MemoryServiceRequestV0 entries.
For each (epoch, neuron, EVENT_TIME, PE), it requires exactly one
PROGRAM_REFERENCE, STATE_LOAD, BATCH_CONSUME and STATE_COMMIT. It preserves all
prior edges and inserts:

- PROGRAM_REFERENCE -> STATE_COMMIT
- STATE_LOAD -> STATE_COMMIT
- BATCH_CONSUME -> STATE_COMMIT
- previous STATE_COMMIT -> next STATE_LOAD of the same neuron

Only STATE_LOAD, not immutable-P program prefetch or EVENT consumption, is held
behind the preceding commit. That is deliberate: EVENT_TIME is not SERVICE_TIME.
Graph cycles, orphan internal requests, conflicting per-batch identities and
wrong target/domain/epoch/PE are rejected before running service.

## Non-goals and remaining hazards

This graph does **NOT** execute a STATE_COMMIT or prove an emission was admitted
atomically. A commit owner must authenticate and persist the actual Core image
and return evidence before the next STATE_LOAD can consume PE service. The
existing OwnedInternalReadStateV0 validates historical STATE_LOAD receipts
against the *current* neuron image, so that owner **also requires a historical
commit/receipt-retirement contract**. The graph is a prerequisite, not a
workaround for historical validation.

Never treat caller-created completed_request_ids as proof of a committed state.
Existing frozen Core/Network/Compiler remain unchanged.

## Acceptance

- 38 new unit tests cover ordering, preservation, adversarial graphs,
  distinct neurons and long dependency paths. 433 combined tests passed in
  the local reconstructed harness (including 38 new tests); fwork remains authoritative.
- Run `python -m pytest -q tests/test_serialized_internal_graph_v0.py` and full suite.
- Real fwork tests are authoritative; local reconstructed architecture is not.
