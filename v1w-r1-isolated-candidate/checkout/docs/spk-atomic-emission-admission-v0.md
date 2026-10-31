# SPK S3.7d/3b2b0: Atomic Emission Admission v0

Status: DRAFT, simulator-only. No changes to frozen Core, Network or Compiler v0.

## Architectural choice

The existing `EMISSION_RECORD` is one logical completion. Its observed routed
occurrences are published into `OUTPUT` at its completion boundary. The v0
boundary controller has no partially produced-emission cursor. Therefore the
first live scheduler will treat the complete routed fan-out of an emission
as an **atomic offer**. All its route occurrences must fit in the **same
source PE** OUTPUT buffer at that publication boundary.

This makes `fanout > source.output_slots` **infeasible under the selected
atomic policy**, even if some future streaming-emission architecture could
execute it. It is **not** a proof that the functional Network is invalid.

## `admit_atomic_emissions_v0`

Validates physical PE identifiers, epoch, logical request coverage, observed
ROUTE_ENQUEUE identity, destination BATCH_CONSUME binding, and all emission
groups. Returns a canonical, immutable bundle manifest with route multiplicity.
Raises `AtomicEmissionCapacityV0` if any one complete emission exceeds the
source PE's finite OUTPUT capacity. Each parallel edge retains its own route ID.
Zero-fanout emission records are allowed.

## Not yet guaranteed

Passing static admission does not prove free output capacity **at runtime**.
Two individually fitting emissions may still contend for the same PE.
The live scheduler must delay `EMISSION_RECORD` completion until all slots are
actually free, without servicing the final unit prematurely. It must preserve
external arrivals, service DAG constraints, source ownership, and bounded
progress/error reporting. Any future streaming/fan-out partial delivery
requires an **explicit new architectural policy**, not a hidden queue.

`EVENT_TIME` is never converted into `SERVICE_TIME`.

## Next gate

Integrate this admission manifest into an **opt-in** active scheduler that
coordinates actual service slices with S3.7d/3b1. Keep S3.5 unchanged.
