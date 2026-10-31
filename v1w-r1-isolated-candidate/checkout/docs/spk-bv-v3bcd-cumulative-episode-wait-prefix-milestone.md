# SPK BV v3b–v3d: source episodes, causal prefixes and native-veto ACK waits

This **research-only additive** release extends the already SHA-pinned
v2y–v3a *derived* ACK/consumer executor. The frozen original native
`spk_backvalidation_v0/live_dual_scheduler_v0e.py`, SPK Compiler, Core,
Network and Architecture are not edited or rebound.

Three phases delivered together:

1. **v3b — longer genuine source episodes.** Use six source-authorized
   external-input schedules with 2, 3, 4, 6, or 8 events (both regular and
   dense eight-event schedules). Each schedule is freshly admitted by the
   original source fixture and consumes the original native two-PE budget;
   no synthetic receiver mailbox controls or abstract ghost work is used.
   Measure the true interval from each receiver-owned judgment's `due_tick`
   to its *actual* resource-charged ACK `serviced_tick`, as well as separately
   paid consumer receipts.
2. **v3c — causal prefix nonanticipation.** For four source extensions
   along the two→three→four→six→eight-event series, check the complete
   already-executed ACK, paid consumer and forward-terminal prefix strictly
   earlier than the first newly appended external input. Across three native
   BV modes, two causal guards and three queue policies this makes **72
   prefix comparisons**, all identical in the pinned finite domain.
3. **v3d — native-veto counterexample to a global ACK deadline.** With both
   native-readiness guards intentionally disabled, the bounded one-turn
   consumer policy reduces **maximum observed ACK wait from 3 to 1 tick**
   versus unbounded consumer-first priority; total ACK wait drops from 121
   to 49 source ticks over 18 native contexts. **But** with frozen native
   forward and feedback readiness protected, ACK wait reaches **29 ticks**
   under both derived policies. Thus a local one-turn consumer fairness
   constraint cannot imply a global one-tick ACK deadline. Transport loss
   and zero-credit controls independently restore all 18 full native
   executions without inventing ACKs, consumer payments or negative credit.

## Differential evidence and limits

| Source-backed check | Outcome |
| --- | --- |
| New original native contexts | 18 = 6 schedules × 3 BV modes |
| New derived queue contexts | 108 = 18 × 2 guards × 3 policies |
| New causal-null contexts | 36 = 18 × loss/credit-zero |
| Full native projection under strict source guard | 54/54 exact |
| Full functional forward payload parity across all derived queue cells | 108/108 |
| ACK, independently charged consumer and forward prefixes | 72/72 equal |
| ACK count per guard and queue policy | 186 source-owned ACKs, all paid exactly once |
| Null-guard bounded/unbounded maximum ACK wait | 1 / 3 ticks |
| Native-ready protected maximum ACK wait | 29 ticks |

**Interpretation:** The 29-tick witness directly falsifies an *unqualified*
one-tick global ACK deadline inferred from the derived local consumer-turn
policy. It does not falsify eventual ACK service (all 186 ACKs in these finite
runs are eventually served), nor establish universal starvation freedom,
termination, throughput or hardware metrics. Prefix nonanticipation is a
source-pinned finite comparison, not a theorem over every possible scheduler
execution. Nothing here adopts native learning or changes actor contracts.

## Execution on fwork

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3bcd_Cumulative_Episode_Wait_Prefix_Milestone.tar.gz

bash search/spk_bv_v3bcd_episode_wait_prefix_cumulative_gate.sh \
  /tmp/spk-bv-v2yza-burst-window-cumulative.json \
  /tmp/spk-bv-v3bcd-episode-wait-prefix.json

bash search/spk_bv_v3bcd_inherited_regression_gate.sh
```

The canonical output must be a **nonexistent** pathname outside the repo.
The gate refuses overwrite, unsafe paths, source drift or a modified
SHA-pinned predecessor. `--contract-only` is not simulation evidence.

The official equal-weight SPK/* roadmap stays **S1 100%, S2 100%, S3 60%,
S4 0%, S5 0%, total 52%**, unchanged. This report improves research
discrimination but does not meet the blocked native actor scheduling,
learning, global liveness or future network obligations.
