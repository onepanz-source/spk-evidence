# SPK V5 T3UVW | Original-source custody and dual-replay gate

Date: 2026-10-21. Additive research milestone for `spk-backvalidation-v0`.

## Exact invocation on Fedora

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T3UVW_Source_Custody_Milestone_20261021.tar.gz
bash search/spk_v5_t3uvw_source_custody_gate.sh /tmp/spk-v5-t3uvw-source-custody.json
```

This gate groups:

- **Inherited T3RST regression**: 36 tests.
- **T3U**: pin three legacy BV-v0e source files to historical known SHA-256 values from previous SPK native audits, and capture SHA-256 of four additional scripts, before and after execution.
- **T3V**: execute the **unchanged original** `search/spk_v5_t3opq_source_bridge_gate.sh` **twice** inside the same working checkout, and verify internal report accounting, exact JSON determinism, source pins, and non-mutation of the watched input files. A second execution is NOT an independent clone or independent attestation.
- **T3W**: enforce nonpromotion because original T3OPQ still uses two BV-v0e passes, and its host chooses the terminal observer retrospectively. C sensor value is host-prepared and unsigned. Even if the original gate passes, there is NO demonstrated native single-pass receiver-origin semantic judgment or native learning.
- **New harness tests**: 29 tests; includes negative cases for hash drift, broken accounting, forged status, nondeterminism, hidden host selection, and mutation during a producer run.

## Output

- `/tmp/spk-v5-t3uvw-source-custody.json` audit summary
- `/tmp/spk-v5-t3uvw-source-custody-original-{1,2}.json` actual, freshly produced reports
- `/tmp/spk-v5-t3uvw-source-custody-original-{1,2}.log` original gate logs

Paths can be changed via first positional argument. An existing prior output of the original producer is explicitly deleted before each rerun. The gate fails closed if there is no new result, pinned source hashes drift, reports are inconsistent, or reports differ in parsed JSON. Only the first two report files and logs are deleted/overwritten in the explicitly chosen output directory, not in the repository.

## What is and isn't verified

`source_sha256` in the T3U section is a real recomputation over selected files in your current checkout, compared to known v0e file hashes. It is **not** complete transitive dependency attestation, native receiver testimony, or authentication of external sensors. The recorded hashes of the T3OPQ and T3RST research code have no third-party signing authority.

The original `reference_report_sha256` string from the previous log is an *unverified reported reference* until its provenance and hashing rule are independently established. T3UVW does not confuse the historical reference string with the SHA-256 of a newly generated JSON report.

The T3UVW harness itself was locally exercised with 29 tests and a deliberately synthetic producer. The real T3OPQ source cannot be run in this creation environment. Only running this milestone in the user's checkout will supply original T3OPQ producer evidence.

**Frozen Core/Network, Compiler, Architecture, and BV-v0e files must not be modified.** No package file overwrites those paths. `tar --keep-old-files` retains earlier files when extracting new additive paths.

## Possible failure

If a historical frozen source pin differs, this is a deliberately blocking failure, not an invitation to override verification. Inspect the named file, Git state, and previous freeze; do not silently replace the pinned hash.

## Next evidence after T3UVW

A read-only instrumentation trace produced at the native scheduler boundary where C actually consumes a forwarded event, with provenance chain and sequential single-pass order, is still required. Validating T3OPQ's dual-replay research output twice is not a substitute for that trace.
