# SPK/* Back Validation v2o — Native-causal-ready actor admission

## Decision

**Derived native-causal-ready research gate PASS. Frozen-native actor
consumption, general liveness and scheduler admission remain BLOCKED.**
No frozen source, Core, Network, Architecture, Compiler, operator weights,
physical resource definition or neuron state was modified.

v2n demonstrated that reserving a forward PE slot alone can restore a
forward terminal trace while breaking BV feedback timing and the full
bounded logical horizon. v2o adds an explicit source-audited pre-forward
observation of **both** already-ready native work classes:

1. Native forward batches ready for PE service, with no blocking outbox;
2. Native feedback/BV packets whose `ready <= tick` in the original
   scheduler's `ready_feedback` list.

In strict mode, an actor-credit pregrant is **vetoed** if either class is
ready. Only an otherwise idle native-causal-ready tick can receive derived
actor-control service. These control grants are still committed to actual
DERIVED abstract PE/memory budgets, and exactly one v2l causal ACK journal
entry is created for each serviced judgment. Native transport, peer
assessment, backward message routing, actor computations and operator values
are unchanged.

The compiler reuses frozen source bytes with pinned hooks: native batch
arbitration at **158**, resource snapshot/admission at **296**, finish/tail at
**307**, and inherited receiver, clock, emission, batch, callsite and actor
ownership anchors. The extra read-only feedback inventory is obtained in
the derived AST scope; it is not inserted into frozen-native code.

Four paired source-backed variants are compared:

| Mode | Ready native forward protected | Ready native BV protected |
|---|---|---|
| `strict_native_causal` | Yes | Yes |
| `forward_only` | Yes | No |
| `feedback_only` | No | Yes |
| `actor_first_null_guard` | No | No |

The last reproduces v2n's signed large-window actor-first baseline, including
each actor-credit journal and terminal time. The two one-sided variants test
whether either protection can be removed without invalidating native parity.

## Full 15 recipes × 3 BV modes × 2 PE-capacity experiment

Independent native v0e is re-executed for all **90** paired cells. The v2n
predecessor's canonical SHA, workload names, per-mode original native result
SHA, full actor-first credit journal and source pins are rechecked.

### Contended global capacity: 1 PE service unit per tick

| Audited metric, per 45 cells | Both protected | Forward only | BV only | Neither |
|---|---:|---:|---:|---:|
| Complete original-native result recovered after exact derived-cost projection | **45/45** | 15/45 | 0/45 | 0/45 |
| Exact forward trace | **45/45** | 45/45 | 0/45 | 0/45 |
| Exact native feedback trace | **45/45** | 15/45 | 15/45 | 15/45 |
| Final states and functional terminal payload | **45/45** | **45/45** | **45/45** | **45/45** |
| Pre-forward derived actor resource grants | **32** | 106 | 101 | 141 |
| Cells with at least one real pre-forward actor grant | **31** | 31 | 45 | 45 |
| Native-causal-ready veto ticks | 338 | 234 | 152 | 0 |
| Exactly-once actor-control ACKs | **156** | 156 | 156 | 156 |
| Sum of ACK wait after source-caused due tick | **1025** | 537 | 538 | 0 |
| Maximum individual ACK wait | **18** | 9 | 16 | 0 |

The combined guard produces **45/45 exact full-native parity** and
nonvacuous early actor service: 32 distinct resource-charged pregrants in
31 cells. Actor messages are not merely parked in the post-native tail.
All 156 delivered controls are eventually ACKed, while waiting longer
relative to actor-first service. An extended deadline for actor ACKs is a
real cost, not a reward for priority policy.

The failure of `forward_only` is particularly diagnostic: its forward
trace is exact in all 45 cells, yet the full native result differs in 30
because BV feedback causality and its PE service schedule were not
protected. Equality of forward terminals is not a sufficient oracle.

### Original global capacity: 3 PE service units per tick

| Audited metric, per 45 cells | Both protected | Forward only | BV only | Neither |
|---|---:|---:|---:|---:|
| Complete original-native result recovered | **45/45** | **45/45** | 40/45 | 38/45 |
| Pre-forward derived actor grants | 88 | 110 | 129 | 140 |
| Cells with at least one early actor grant | 33 | 33 | 45 | 45 |
| Total ACK wait ticks | 433 | 192 | 198 | 2 |
| Maximum individual ACK wait | 14 | 5 | 9 | 1 |

With additional PE capacity, protection of native-ready forward work is
already sufficient for full native parity on **this specific corpus**.
Thus the experimental conclusion is deliberately capacity-conditional:
both protections are necessary in the **strict single-PE deadline witness**,
not under all resources and workloads.

## Explicit bounded-horizon discrimination

Fixed real native fixture, global PE capacity **1**, `max_ticks=11`:

| Native or derived plan | Actual source-backed result |
|---|---|
| Independent frozen native | Completed in 11 native ticks |
| Derived strict native-causal guard | **Completed; exact full native cost projection; 1 real early actor pregrant** |
| Forward-only guard | `LiveBVRejected`: bounded horizon |
| BV-only guard | `LiveBVRejected`: bounded horizon |
| Null guard / original actor-first | `LiveBVRejected`: bounded horizon |

This isolates an experimental contribution from native-ready feedback
protection. It **does not** prove arbitrary-workload termination or
starvation freedom. A control that is not due, lost, quota-refused or still
unconsumed is not a negative judgment or absence certificate.

### Adversarial and negative controls

- **135 additional source-backed causal-null executions**: all-loss,
  callback-fault and zero-credit, each 45/45 exact original-native parity;
  no forged actor pregrant, native learning or negative silence certificate.
- A real negative-B fixture again produces two receiver-origin negative
  judgments, actor A credit register `−2`, exact-once actor ACKs and no
  frozen native learning.
- Unsupported plans and source drifts fail closed; forged mailbox identity,
  modified native feedback-ready probes, modified forward-computation
  counts and unaccounted resource grants are rejected.
- Ready BV inventory is a native source-owned input with explicit type
  checks. This is a local causal custody guard, **not** a distributed mesh
  authentication or proof against arbitrary external injection.

## Reproducibility and exclusions

- Exact signed predecessor v2n canonical SHA:
  `1fbb75ad2ff7f8a9f0124b94bd72e7dac1d4f559e23a07b4d65e95981e162459`.
- Frozen v0e source SHA:
  `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- The signed v2n predecessor is larger than the historical 2 MB evidence
  cap. v2o locally accepts up to **8 MB**, still rejecting symlinks, input
  paths within the project, missing/oversized files and checksum drift.
- **17 dedicated adversarial unittest methods**, with independently signed
  predecessor loaded by `SPK_V2N_REPORT`.
- **90 native + 360 derived policy + 135 derived causal-null = 585**
  complete matrix executions; plus **5** horizon executions/attempts
  (three intentional bounded rejections). Repeat the full report into
  a fresh path and compare byte-for-byte.
- Inherited selected regression gate delegates to v2n, v2m … v2e,
  including 413 pytest cases in `fwork`. This development environment
  may not have pytest installed.
- No source modification to frozen modules; no physical power/latency
  result, N-node guarantee, hardware-equivalence or native actor contract.

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2o_Native_Causal_Admission_Milestone.tar.gz

bash search/spk_bv_v2o_native_causal_admission_gate.sh \
  /tmp/spk-bv-v2n-actor-forward-fairness.json \
  /tmp/spk-bv-v2o-native-causal-admission.json

bash search/spk_bv_v2o_inherited_regression_gate.sh
```

Output paths must be absent before execution. Run additive extraction once,
without replacing any existing frozen or research source file.

## Roadmap and next gate

S1 = 100%, S2 = 100%, S3 = 60%, S4 = 0%, S5 = 0%: overall **52%** by
equal-weight average, unchanged from the previous SPK/* checkpoint. v2o
strengthens bounded S3 research evidence but is not a promotion of
the frozen native actor contract. These percentages remain conservative
project acceptance estimates, not mathematical completeness measures.

**v2p:** Specify and discriminate the actor-consumer event handoff
contract, with retained native source parity, credit replay prevention,
bounded actor backlog/throughput and accountable deadline conditions.
Nothing in v2o authorizes native actor/learner promotion on its own.
