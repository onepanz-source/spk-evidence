# SPK Compiler v0: Conformance Gate C3

Status: CANDIDATE, pending authoritative repository validation
Baseline: frozen `spk-core-network-v0`
Prerequisites: C1 compilation pipeline and C2 compilation manifest.

## Scope

C3 adds an executable independent conformance check for the **observable
contract** of C1 and C2. It is a test-only gate and makes no changes to
the compiler, Core, Network, architecture or simulator runtime.

Run `bash search/compiler_v0_conformance_gate.sh` from any directory.
The gate first runs C1+C2+C3 targeted tests, then the entire pytest suite.

### Independent controls

- Canonical UTF-8 JSON and SHA-256 are recomputed using Python's standard
  `json` and `hashlib` packages, without calling private C2 functions.
- Embedded admission claims are checked against direct public resource
  and PE-admission entrypoints; they are NOT independently proved optimal.
- Reconstruction preserves parallel edges and identical event occurrences.
- Functional replay agrees with frozen `run_network_v0` for the reference
  stimulus.
- Tamper trials recompute the checksum adversarially and require the
  compiler to reject inconsistent resource/PE admission and mapping claims.
- Fresh Python interpreters with three distinct `PYTHONHASHSEED` values
  must produce byte-identical canonical manifest JSON.
- Unsupported schemas/versions, duplicate keys, unknown fields, NaN,
  and invalid public API argument types must fail closed.

### Security and correctness limits

- SHA-256 is a checksum **not an authenticator**. A malicious actor who
  changes a full self-consistent compilation input and recomputes all
  derived claims can create a valid different manifest. C3 does not
  establish document origin or trust.
- C3 exercises a representative two-node, two-PE profile and parallel
  routing edges. It is not exhaustive model checking or formal proof.
- Admission ensures only static compatibility for declared profiles.
  It does not establish dynamic bounded-memory feasibility, progress,
  deadlock freedom, or real-device safety.
- Functional equivalence here means identical results for the reference
  input through the frozen Network v0 runtime, not universal semantic
  equivalence of all possible workloads.
- C4 still needs a clean-checkout reproducibility and freeze audit before
  the Compiler v0 can be declared final.

## Acceptance gate

PASS requires:
1. Every C3 conformance test succeeds, including deterministic replay
   across fresh interpreters.
2. All pre-existing tests pass without a regression.
3. No frozen Core/Network source is modified.
4. Diff contains only these three C3 files.

Failure in any condition blocks promotion to S2=95%.
