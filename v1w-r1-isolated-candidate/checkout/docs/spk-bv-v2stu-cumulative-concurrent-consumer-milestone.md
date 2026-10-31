# SPK BV v2s–v2u: cumulative concurrent actor-consumer milestone

**Research boundary:** This is an additive, separately source-compiled *derived*
scheduler; the frozen v0e native scheduler, original compiler, Core, Network,
Architecture and native actor/learning semantics remain unchanged.

This **single release** combines three sequential advances that previously
would have required three separate `v2*` user round trips:

1. **v2s — true pre-forward consumer execution:** derive a fresh ACK-owned FIFO
   actor-consumer journal that spends its *own* one PE and two memory units per
   applied credit, before frozen forward batches run, when source budgets and
   native-ready precedence allow. Its `before-native-forward` phase is genuine,
   not a relabelled v2q `after-native-forward` application. The previous v2q
   consumer lane is explicitly disabled to forbid double application.
2. **v2t — causal three-way contention discrimination:** replay 90 original
   native contexts (15 source-backed workloads × 3 BV controls × original/one-PE
   capacity), 360 paid derived four-guard runs, and 180 controlled intervened
   runs (`pre_service_zero`, `consumer_tail_off`, `ACK_credit_zero`, loss).
   Contrast the entire native forward/feedback/event schedule, not just payload.
3. **v2u — exact resource inverse and adversarial gate:** independently audit
   source PE and O/E memory budgets, receipt ownership, ACK causality, FIFO,
   order, typed plans, timeline aliases, post-native tail custody, finite
   horizon and source pins. Tampering fails closed before native projection.

## Contract distinctions

| Claimed | Justification / boundary |
| --- | --- |
| Paid concurrent pre-forward consumer, derived only | Early charge mutates actual derived Counters, then native-derived forward sees diminished budgets. |
| Source-budget conservation | Every application spends an independent PE+RAM unit; predecessor v2l ACK already has its **own** independent resource charge. |
| Strict native-ready projection | With both native readiness guards, all source-pinned workloads project the full original native result. |
| Genuine scheduling interference | Disabling *only* early consumer service changes forward traces in the actor-first derived mode. |
| Credit replay/owner integrity | Each receipt is causally tied to an acknowledged delivered receiver judgment, original actor/PE owner and monotone actor sequence. |
| Negative judgment | A B-source negative event applies -1 to A exactly twice; no inference from lost messages or capacity. |
| Universal native actor/learning contract | **Not proven**; original frozen operator unchanged. |
| Universal starvation-freedom | **Not proven**; finite-horizon rejection is not silence or negative evidence. |

The independent consumer has a new typed plan and separately audited FIFO
journal. v2q's existing after-native lane is kept pinned and disabled; all
full result comparisons are against actual native source runs. A projection
subtracts only audited PE/RAM grants; it does **not** reverse any native-derived
event delay caused by real pre-forward pressure. `ACK_credit_zero` and transport
loss restore native execution; consumer-off does not erase upstream ACK priority.

## fwork execution

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2stu_Cumulative_Concurrent_Consumer_Milestone.tar.gz

bash search/spk_bv_v2stu_concurrent_cumulative_gate.sh \
  /tmp/spk-bv-v2r-three-way-causal-priority.json \
  /tmp/spk-bv-v2stu-concurrent-cumulative.json

bash search/spk_bv_v2stu_inherited_regression_gate.sh
```

The canonical output must not exist before the gate; the runner fails closed
instead of overwriting previous signed evidence. No release extraction should
overwrite an existing source file. `--contract-only` is a signed-predecessor
validation and explicitly **not** a simulation PASS.

Roadmap: the tracked **frozen native** stages and source contracts do not
change based on the number of cumulative derivative phases. Prior S1=100%,
S2=100%, S3=60%, S4=0%, S5=0% (equal-weight illustrative 52%) remain a
conservative unchanged estimate, not an earned higher percentage.
