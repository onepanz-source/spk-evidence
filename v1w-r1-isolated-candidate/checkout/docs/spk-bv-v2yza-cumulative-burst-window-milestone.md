# SPK BV v2y–v3a: source-backed multi-turn ACK window milestone

**Research-only, additive release.** No modification of the frozen SPK BV
native operator (`spk_backvalidation_v0/live_dual_scheduler_v0e.py`) or
Compiler, Core, Network, Architecture. Nothing in this release promotes a
derived queue policy into the frozen actor/learning contract.

Three consecutive research phases in one reproducible archive:

1. **v2y — real source burst pressure.** In v2v–v2x the policy's consecutive
   consumer-turn limit was implemented but *never activated*. This release
   tests a new source-native **two-PE global fabric** capacity, a source-owned
   receiver feedback delay of two ticks, and up to two real ACK resource
   services per tick. All ACKs originate in real source emission → ingress →
   receiver-local judgment → delivered mailbox records, never injected.
2. **v2z — an actually activated finite bound.** Compare `ACK-first`,
   `consumer-first` and `bounded-turns`. In the new 15-workload × 3 native-BV
   mode matrix, the unlimited consumer-first preference has a two-consecutive
   contended-turn streak in **7/45 cells**. The one-turn bounded policy
   activates in **7/45 cells and 9 source ticks**, gives real ACK priority at
   those windows and records **11 paid ACK grants**. Maximum competing consumer
   streak under the bounded regime is one, without weakening real budget
   accounting, either consumer or ACK digest-chain custody, or final forward
   functional payload parity. Both independent journals change in 7 cells.
3. **v3a — five causal ablations and adversarial closure.** One ACK global
   service per tick, one-tick receiver latency, zero early consumer capacity,
   zero credit and transport loss are run as separate 45-cell matrices.
   The first two eliminate observed two-turn streaks; zero consumer cannot
   mint receipts; zero credit and transport loss restore full original native
   without fake negative judgments. Forged mailbox, source/chain mutations,
   selection and fairness replay, resource counter tampering and signed
   predecessor mutations fail closed.

## Measured scope

| Evidence | New executions | Result |
| --- | ---: | --- |
| Frozen original native under the new two-PE budget | 45 | Replayed and source pinned |
| 3 queue policies × 2 native-ready guards × 45 cells | 270 | Functional payload equal in every cell |
| Five source-backed causal ablations × 45 cells | 225 | Loss and credit-zero restore native 45/45 each |
| Strict original native projection | 135/135 | Full equal (not merely final payload) |
| Bounded turn limiter (previous release: 0) | 9 tick windows | Activated, 11 actual ACK pre-forward grants |
| Bounded policy maximum contending consumer streak | 1 | No observed overrun |

The two-PE setting is a **new native source-capacity model run**; it does not
claim a new original native contract. The derived actor still observes
the original admissions, transport, true mailbox and executor callsites.
No source or frozen scheduler is rebound.

This establishes a **finite conditional safety and service witness**:
after one contending consumer turn, when both queues are source-ready and
there is no stronger native-ready veto, the derived arbiter selects the ACK
queue; actual granted ACK resources are separately measured. It does **not**
prove eventual service under arbitrarily prolonged overload, fair arbitration
among all actors, end-to-end completion, universal liveness or native
learning. Absence, loss and unspent credits are not negative certificates.

## Execution on fwork

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2yza_Cumulative_Burst_Window_Milestone.tar.gz

bash search/spk_bv_v2yza_burst_window_cumulative_gate.sh \
  /tmp/spk-bv-v2vwx-queue-precedence-cumulative.json \
  /tmp/spk-bv-v2yza-burst-window-cumulative.json

bash search/spk_bv_v2yza_inherited_regression_gate.sh
```

The output pathname must be new. The CLI rejects existing outputs, altered
SHA-pinned source, noncanonical/tampered predecessor or a path owned by the
repository. `--contract-only` is signed-predecessor validation and explicitly
not a research simulation PASS.

Frozen SPK roadmap remains unchanged: **S1 100%, S2 100%, S3 60%,
S4 0%, S5 0%, equal-weight total 52%**. More derived evidence does not close
the unfrozen native actor/learning, forward liveness or distributed transport
contracts and does not inflate these percentages.
