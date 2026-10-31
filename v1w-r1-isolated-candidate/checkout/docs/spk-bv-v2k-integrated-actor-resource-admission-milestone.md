# SPK/* Back Validation v2k — Integrated DERIVED actor-resource admission

## Decision and exact claim

**Pinned derived research gate PASS; native actor-event admission and credit
policy still BLOCKED.** v2k is not a frozen-native promotion. Core, Network,
Compiler, Architecture, instruction set, native scheduler and actor state are
untouched. The work is strictly additive and can be removed independently.

v2j allocated actor-control service in a *shadow ledger*, keeping every
original native resource row exactly equal. v2k advances the experiment: an
AST-compiled derivative of the byte-pinned `execute_live_v0e` scheduler
books each admitted actor-control grant directly into **its own running**
`service_used`, `pe_total`, `mem_pe_used`, `mem_dom_used`, and `mem_total`
resource counters. Its resource timeline therefore differs intentionally
from native v0e. The original native forward result and native BV/feedback
result must remain exactly equal.

The derived executor invokes the service commit just before the frozen
resource-timeline append at line **296** (after native tick work), and
appends independently labelled *control-only* resource rows after original
native termination at line **307**. Existing v2h semantic anchors and v2g
callsite checks are still independently enforced. Native ownership comes
from the pinned in-process `_admit` result. Mailbox custody and rejection
of wrong-owner, forged, or replayed judgments are inherited and retested.

### Exact original-native projection

The derivative is **not** asserted to be raw whole-result-equivalent to the
frozen native program. Instead `project_original_native_result`:

1. Checks each derived tick's five resource keys against its *recorded,
   witnessed* original native baseline plus only precisely admitted grants.
2. Rejects unexplained inline counter edits, extra rows, changed tail rows
   and broken tick custody, rather than masking arbitrary differences.
3. Reverses just the witnessed resource increments and removes just the
   synthetic post-native control-only rows.
4. Requires the reconstructed **entire native result**, including all
   native resource, timing, forward and feedback data, to be byte-equivalent
   to independently executing frozen v0e for the same input.

Thus full original-native **projection** parity is 45/45, while the raw
derived resource timeline differs in **45/45** cells. These statements are
not contradictory and must not be interchanged. The projection is a
strong test of no unaccounted change, not proof of native admission.

## Bounded research resource policy

The inherited explicit costs are **1 abstract PE service unit and 2 local
memory units (1 O + 1 E)** per grant. Native residual PE/global/memory
budgets gate inline admissions, with at most two per tick and one per actor;
up to 32 bounded research tail ticks are allowed. No preemption of native
forward activity or competing scheduling priority is established. A tail
row represents *new research time*, not an extra tick secretly executed by
the frozen native scheduler. Costs are experimental proxies, not hardware
or algebraic theorems.

## Measured source-pinned 15 x 3 workload/BV matrix

| Measurement | Result |
|---|---:|
| New original native executions | 46 |
| New derived integrated executions, normal | 46 |
| New derived loss/fault/overflow/no-tail/tight interventions | 225 |
| Total new runtime executions | **317** |
| Exact complete *projected* native results | **45/45** |
| Intentionally modified raw derived resource timelines | **45/45** |
| Derived actor-control PE grants committed | **156** |
| Commits during frozen-native tick's residual budget | 140 |
| Commits in post-native derived control-only ticks | 16 |
| Delivered controls left unconsumed under normal derived plan | 0 |
| Derived abstract PE units booked | 156 |
| Derived abstract O/E memory units booked | 312 |
| Extra derived control-only timeline rows | 16 |
| Genuine negative B judgments in separate fixture | 2 |
| Negative-B derived actor A credit | -2 |
| Native learner/operator changes | **0** |
| Frozen-native actor-control resource grants | **0 proven** |

The negative-B example is negative receiver-authored evidence and derived
per-actor credit only, **not native learning**. Transport loss and callback
failure generate no phantom grants, no-tail prevents synthetic tail work,
and memory/PE pressure and overflow can leave controls unconsumed without
claiming that silence is a negative certificate. Adversarial tests reject
unaudited counter/tail mutations, source drift, forged mailbox entries,
wrong context, signed-predecessor changes and invalid policies.

## Reproduction and audit

The required signed v2j canonical report SHA-256 is
`8fd1919c0bf197e83064828f074daa533038a1f798ea6398f8e0b88b0e6ae396`.
The frozen native scheduler SHA-256 remains
`2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
The CLI verifies exact predecessor bytes and pinned v2h-v2k source files,
rejects symlinks and unsafe output, then rechecks source bytes after replay.
All output reports are canonical, and existing outputs are deliberately
rejected: use a **fresh** file path for re-execution. The archive is additive;
do **not** extract the same archive a second time with `--keep-old-files`.

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2k_Integrated_Derived_Actor_Resource_Admission_Milestone.tar.gz

bash search/spk_bv_v2k_integrated_actor_admission_gate.sh \
  /tmp/spk-bv-v2j-shadow-actor-control-service.json \
  /tmp/spk-bv-v2k-integrated-actor-resource-admission.json

bash search/spk_bv_v2k_inherited_regression_gate.sh
```

The new local stdlib suite has **14** tests. The inherited selected regressions
must also pass on `fwork`; the isolated preparation runtime may not have
`pytest`. The reproducible CLI can be rerun with `--out` pointing at a
previously nonexistent report and the resulting SHA-256 compared.

## Remaining gate

To call this native instead of derived, a separately reviewed actor-event
admission contract must specify service wakeups, independent owner/identity
and mailbox semantics, PE/memory charge authority, queue discipline,
priority against forward work, contention, safe credit-consumption, replay
policy, bounded time horizon, and non-silence under loss. No native learning,
hardware N-node equivalence, distributed cryptographic identity, rollback,
or cold promotion follows from v2k.
