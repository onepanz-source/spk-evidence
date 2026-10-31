# T9JKL / T9MNO / T9PQR grouped milestone

- T9JKL `stale_evidence_v1.py`: live V1 SEM_B_C + veto lineage, archival evidence-only SQLite ledger; reject replay or tamper; no P authority.
- T9MNO `admission_frontier_v1.py`: serial vs batch3 vs per-context single-inflight admission on the unmodified T9 V1 scheduler.
- T9PQR `cumulative_evidence_frontier.py`: real PE stale-recredit counterexample, full source report comparisons, cross-process determinism and restart parity.
- `reference/t9abc-def-ghi-cumulative.json` is the pinned T9 predecessor produced on fwork, SHA-256 `3e664630227170e105aa945f550518a442ac8ee08086ee13ff721163527b8b92`.
- The report and test suite are research-only and must preserve zero native SPK grants and learning.
- Apply the archive with `tar --skip-old-files` inside `~/workspace/spk-backvalidation-v0`; one gate script runs all regression suites, verifies all predecessor manifests, 12 frozen source pins and the genuine V0e admission preflight.
- Gate refuses to overwrite an existing report. No file below frozen SPK components is installed or changed.
