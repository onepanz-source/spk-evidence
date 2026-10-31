# SPK v1 native Memory Contract readiness dossier (T10STU/VWX/YZA)

## Boundary
T10JKL counts only reference C/P grants in host SQLite. Its manifest is not the native Memory Contract. This milestone does not add a fake adapter that returns native grants.

## Evidence to collect on genuine fwork checkout
Survey Python candidates (read-only AST) from `spk_architecture_v1`, `spk_memory`, `spk_compiler`, `spk_simulator` with memory, admission, transaction, resource or ownership names. Record paths, source digests, classes and signatures. They are *candidates*, not validated entrypoints. Real API semantics must be reviewed separately.

## Obligatory checks for promotion of a subsequent runtime version
1. Actual native Memory Contract module identified and pinned to its frozen source.
2. A versioned write-intent interface with owner `C`, domain `P`, execute mode, context and expected version.
3. Native resource/ownership authority called at actual tick, not inferred from a host-side ledger.
4. Native grant consumed by the native P state owner, atomically with P CAS, with replay and crash recovery.
5. Independent A measurement provenance and adversarial privileged-host boundary explicitly characterized.
6. Baseline frozen BV-v0e and original PE unchanged and byte-exact historical regressions.

Until then: report zero native grants, zero native P writes and zero native learning. Never promote research reference grants on source-name similarity.
