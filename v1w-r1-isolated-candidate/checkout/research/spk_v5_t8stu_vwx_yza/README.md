# SPK V5 T8STU/VWX/YZA cumulative milestone

**Three advancements; one gate; no changes to frozen code.**

- T8STU: new V1 reference scheduler uses a SQLite-backed tick event queue.
  It invokes `_compute_local` from the original frozen PE on each C/B/A stage.
- T8VWX: semantic feedback is carried as queued A→B→C events with a grant and
  P transaction issued at the C receiving tick, plus precise crash recovery.
- T8YZA: compare sequential reference model to the original BV-v0e scheduler
  as a **read-only oracle after the event loop**; preserve exact source SHA
  parity from T8JKL/MNO/PQR and include host-controlled-goal negative control.

All three are reference-v1 research capabilities. The original SPK Core,
Network, Compiler, Architecture, BV scheduler and Memory Contract remain
immutable. Internal reference grant != native SPK grant.

Run on `fwork`:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T8STU_VWX_YZA_Integrated_Tick_Reference_Cumulative_20261022.tar.gz
bash search/spk_v5_t8stu_vwx_yza_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t8stu-vwx-yza-cumulative.json
```

The gate checks original hashes, 15 additive manifests, 12 original source
pins, genuine admission preflight, all inherited milestone tests, new tests,
and independent double-execution with byte-exact output comparison.
Output is fail-closed and refuses to overwrite evidence.
