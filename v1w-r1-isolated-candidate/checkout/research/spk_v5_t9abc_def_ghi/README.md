# T9ABC / T9DEF / T9GHI (research-only)

Cumulative checkpoint for 3 related V1 research capabilities:

1. **T9ABC**: bounded admission of multiple pending epochs with serialized FIFO
   dispatch slots, not physical/global clocks.
2. **T9DEF**: atomic C-policy version check under competing receiver feedback,
   with durable stale-vote veto and independently versioned contexts.
3. **T9GHI**: restart, delayed feedback, fairness, budget, original T8 serial
   behavioral parity and negative host/native boundaries.

The source PE compute kernel is the frozen `_compute_local`, the frozen BV-v0e
code remains unchanged. Prior T8 oracle source data is SHA pinned; T9's own
scheduler is independent and research-owned. It is not native SPK.

Run from project root: `bash search/spk_v5_t9abc_def_ghi_cumulative_gate.sh /path/report.json`

Standalone research-only report (when original frozen PE and BV modules are
present):
`python3 -m research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate --root . --out /tmp/t9.json`

No native semantic BV, source-authenticated A measurement, native Memory Contract
P grants, or native learning is claimed. One *reported loss* under concurrency
(88 -> 84 successes) is intentionally a fixed test expectation.
