# SPK V5 T3XYZ hotfix: trace volume recovery

## Scope

This is an **additive research-only audit** of already generated files. Does not override T3XYZ's original fail-closed gate and does not edit any frozen source file. It preserves that incident as `FAIL_CLOSED_PROBE_TRACE_SIZE_INVALID` while recovering validated host-level visibility.

### Root cause

Original T3XYZ uses `MAX_TRACE_BYTES = 32_000_000`. On 2026-10-21 its CPython sitecustomize instrumentation captured 47,545,722 bytes / 64,615 JSONL records from 19 processes: 32,298 `_compute_local` calls and 32,298 returns; two PIDs reached `SPK_T3XYZ_MAX_EVENTS=25000`. The production report remained byte-identical SHA `813753af...c790d2`.

### Changes

- JSONL is validated line-by-line, streaming, with new 128MB hard limit; rejects oversize records, corrupted JSON, invalid sequences, unbalanced calls/returns, incorrect frame source, missing pinned source or altered original report.
- Cap-hit processes are identified. Even absent a hit, `complete_execution_coverage_proven` stays false: Python host tracing is not an authenticated native observation.
- No rerun of 421 earlier tests; their outcome is authenticated only as matching original report hash plus presence of the recorded log PASS, not an independent blind replay.
- Research-only semantic nonpromotion remains mandatory.

Run from `~/workspace/spk-backvalidation-v0`:

```bash
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T3XYZ_Trace_Volume_Recovery_Milestone_20261021.tar.gz
bash search/spk_v5_t3xyz_trace_recovery_gate.sh /tmp/spk-v5-t3xyz-trace-recovery.json
```

Original evidence prefix is `/tmp/spk-v5-t3xyz-passive-observation` by default; second argument overrides prefix.

Captured evidence is pinned to the exact uploaded bytes: profile SHA-256 `21ac7a5197c56cdff3edb816b86233d1c4749e601848eadac1c7413232e17484` and log SHA-256 `1554f4f89a46a7b889c1986f5ab1e5305b0926c535e60230e8e734e0833cc110`. Re-capturing these volatile CPython timestamps/PIDs will produce a different trace and **should fail** this incident-specific recovery, rather than pretending byte parity.
