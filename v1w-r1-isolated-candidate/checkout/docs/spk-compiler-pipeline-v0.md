# SPK Compiler Pipeline v0: C1

Status: DRAFT - pending validation in the authoritative repository
Baseline: spk-core-network-v0

## Purpose

Compose the existing strictly versioned Network IR decoder, static logical
resource admission, and static PE mapping admission into a single deterministic
operation that returns an admitted simulator input.

This pipeline does not emit machine code, perform Core optimization, or
alter the frozen Core/Network execution semantics.

## Inputs

- A JSON document under the existing `spk-network-ir/v0` codec.
- A tuple of initial `NetworkEventV0` occurrences (multiplicity preserved).
- A `ResourceProfileV0` representing logical compilation limits.
- An `ArchitectureProfileV0` representing PE capabilities.
- A complete, explicit tuple of `NodePlacementV0` assignments.

## Stages

1. Validate Python-side input types without coercion.
2. Decode Network IR with the existing strict version/schema codec.
3. Produce canonical Network IR with the same existing codec and require a
   lossless round trip.
4. Run existing `admit_network_v0` logical resource gate.
5. Run existing `admit_pe_mapping_v0` PE placement gate.
6. Return immutable `CompiledNetworkV0` only after every gate succeeds.

Placement entry order is canonicalized by node ID. Network declaration order,
parallel edges, and event occurrences are preserved.

## Rejection

Failures propagate the existing decoder and admission exceptions. An
incomplete or invalid compilation has no successful result. Error-code
normalization is deferred to the C2 compilation manifest/API contract.

## Boundaries

Admission is **static**, not a proof of dynamic execution feasibility.
Event buffers, backpressure, scheduling cycles, epochs, and learning are not
computed by the compiler. It does not call `run_network_v0`.

Host memory consumption and binary instruction encoding are not modeled.
Compiler backends/ISA lowering are future, separately versioned extensions.

## Next acceptance gates

- C1: Single network IR decoding and both admission gates in one operation.
- C2: Canonical machine-readable compilation manifest and reproducibility.
- C3: Independent end-to-end conformance gate and negative cases.
- C4: Clean checkout, documented freeze, reproducible tag.

All tests must run in the authoritative SPK checkout before changing status.
