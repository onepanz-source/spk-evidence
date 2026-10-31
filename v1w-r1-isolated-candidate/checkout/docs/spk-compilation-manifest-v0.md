# SPK Compilation Manifest v0: C2

Status: DRAFT, pending tests in authoritative repository
Baseline: spk-core-network-v0
Input: admitted `CompiledNetworkV0` from C1

## Contract

`dumps_compilation_manifest_v0(compiled)` produces deterministic UTF-8 JSON
with schema `spk-compilation-manifest/v0` and version `"0"`.

The document contains:

- canonical Network IR v0 in an embedded object;
- initial event occurrences in their original order (including duplicates);
- the full static logical resource profile;
- architecture and complete per-PE capacity declarations;
- node-to-PE placement, ordered canonically by node ID;
- both static admission results for independent verification.

Object keys are sorted; JSON contains no non-finite floating point values;
insignificant input whitespace and placement tuple order do not affect the
manifest. Node and edge declaration order remain meaningful and preserved.

`payload_sha256` is SHA-256 over UTF-8 bytes of the prefix
`spk-compilation-manifest/v0\n` followed by canonical JSON of `payload`.
This is an **integrity checksum, not a signature**: a malicious party can
rewrite the payload and recompute the hash. Consumers need trusted transport
or a separate signature mechanism for authentication.

`loads_compilation_manifest_v0` rejects duplicate JSON keys, unknown fields,
unsupported versions, hash inconsistencies and invalid structured inputs.
It reconstructs inputs, reruns Network IR validation and **both** static
admission gates, then compares derived values against the stored payload.
No C2 document alone confers permission to execute on a physical device.

## Boundaries

- No binary instruction encoding, relocations or hardware ISA lowering.
- No dynamic buffer feasibility guarantee, scheduling, or backpressure proof.
- Not a security sandbox; neither JSON checksums nor frozen Python dataclasses
  establish authenticity or protection from host-language object construction.
- Reproducibility is within the frozen v0 schemas and declared profiles.
- C3 will establish independent conformance gates; C4 will validate a clean
  checkout and freeze the Compiler v0 build and dependencies.
