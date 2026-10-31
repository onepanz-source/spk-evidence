# SPK BV v2v–v2x: cumulative ACK/consumer queue precedence milestone

**Scope:** Three consecutive, additive research phases in one release. The
frozen `spk_backvalidation_v0/live_dual_scheduler_v0e.py` and SPK Compiler,
Core, Network and Architecture are not modified. This is evidence for a
**separately compiled derived** executor, not admission of a native policy.

1. **v2v — real two-queue arbitration.** An ACK-service queue competes with
   the independently PE/RAM-paid actor-consumer queue before native forward.
   Test `ACK-first`, `consumer-first` and `bounded-turns` with source-owned
   records, actor custody and monotone ACK journal. No fabricated negative
   credit, no conflation of upstream ACK with consumer receipt.
2. **v2w — finite source-backed contention and turn window.** Introduce a
   preference for the waiting ACK queue after one contending consumer turn,
   with an explicit probe of actual ready ACKs, consumer backlog, resource
   availability and forward source readiness. The present pinned workloads
   **never activate** this two-consecutive-turn limiter. It is *not* a
   fairness/liveness theorem or a completion certificate.
3. **v2x — causal ablation and integrity closure.** Contrast genuine consumer
   priority with `pre_consumer_zero`, upstream `credit_zero`, and transport
   loss; audit source hashes, the signed predecessor, native/derived outputs,
   independent resource grants, ACK/consumer journals, source queue probes,
   actor attribution and malicious mutation. Reject on custody or budget
   drift rather than weakening native projection.

## Native/derived differential evidence

The pinned matrix contains 15 real recipes × 3 native BV modes × original
or one-PE source capacity. The research gate executes **90 new original
native runs**, **540 derived policy/guard runs**, and **135 controlled causal
nulls**. Both guards (`strict_native_ready` and `actor_first_null_guard`) are
replayed across three queue policies, and all 45 strict-native-ready cells
per capacity/policy preserve the *full* original native result. Functional
payload parity is checked in every derived cell.

With explicit two-tick receiver feedback latency and one globally bounded
ACK service per tick, **37 of 45 one-PE, actor-first/null-guard cells** expose
a real ready-ACK/paid-consumer collision. ACK-first versus consumer-first
also produces different signed causal ACK journals in **37/45 cells**. These
are source-scheduled interventions, not renamed post-native operations.

The finite bounded-turn limiter activated in **0 cells**; the maximum
contested consumer streak is one. The matrix therefore does not witness
whether the limiter eventually breaks a longer adversarial ACK backlog.
Loss and zero-credit controls restore native behavior without inventing an
ACK, a negative judgment, or paid consumer work. Zero pre-consumer capacity
preserves pending credit without spending consumer resources.

## What remains BLOCKED

- **Frozen native ACK/consumer/forward scheduling**: no native event policy
  was changed; derived priority changes are not native adoption.
- **Universal ACK fairness, termination or starvation freedom**: finite
  source-backed evidence cannot close the general proof, particularly with
  the bound never triggered.
- **Native actor learning, intake, cross-node authenticity and hardware
  calibration**: no new contract in this release.

SPK roadmap numbers remain **S1=100%, S2=100%, S3=60%, S4=0%, S5=0%,
aggregate 52%**. The extra versions increase test coverage and research
evidence, not these stage-completion percentages.

## fwork execution

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2vwx_Cumulative_Queue_Precedence_Milestone.tar.gz

bash search/spk_bv_v2vwx_queue_precedence_cumulative_gate.sh \
  /tmp/spk-bv-v2stu-concurrent-cumulative.json \
  /tmp/spk-bv-v2vwx-queue-precedence-cumulative.json

bash search/spk_bv_v2vwx_inherited_regression_gate.sh
```

The output file must **not** already exist: the gate rejects existing
targets instead of overwriting a signed report. If extraction reports
`File già esistente`, stop and inspect versions; do not silently replace
existing code. `--contract-only` validates predecessor identity but is not a
simulation PASS.
