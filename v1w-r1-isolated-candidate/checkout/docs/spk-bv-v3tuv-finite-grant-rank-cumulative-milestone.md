# SPK BV v3t–v3v: finite global FIFO grant-rank certificate

Source-backed, **derived research only**. Frozen native scheduler, SPK Core,
Network, Compiler and Architecture are untouched. This cumulative milestone
keeps the native forward output *bit-identical* and does not implement native
Back Validation actor learning.

## Question and precise answer

When source feedback for actor B is ready but a global ACK grant instead
serves actor A, can we say *when* B will finally be serviced?

The source allows a **conditional ordinal answer**, not a clock deadline.
For every real native-tick ACK grant in the new 72-context matrix, the granted
judgments are exactly a prefix of the waiting queue ordered by
`(due_tick, judgment_id)`. For a ready judgment with ordinal rank **r** in
that queue on its due tick:

- If it is served, its ACK is precisely the **r-th real global grant after
  its due tick**, counting same-tick grants.
- If it is still unserved at the native horizon, **fewer than r grants**
  occurred after its due tick.
- Nothing in the source ensures that **r grants will ever arrive**; rank is
  neither a maximum tick wait nor a universal actor fairness/liveness proof.

This is separate from the v3q–v3s negative finding: global ACK progress can
coexist with another actor remaining ready and unserved.

### Three cumulative research stages

1. **v3t**: source-owned, tick-by-tick global FIFO prefix verification with
   causal custody and ACK/resource ledger inherited from v3q–v3s.
2. **v3u**: exact ordinal rank accounting in real *grant units*; observed
   service gets an exact certificate, pending judgments receive a censored
   certificate—not a synthetic negative receiver vote.
3. **v3v**: three fresh admitted eight-external-event workloads; cross BV
   modes, native PE budgets 1/2, derived ACK-first/bounded-turn policies and
   quota 1/2. Causal-null variants and exact original-native projection.

### New measured results

| Source measure across all 72 derived contexts | Count |
|:--|--:|
| Fresh original-native replays | 18 |
| Derived FIFO/rank replays, exact original-native projection | 72/72 |
| Causal-null runs without fabricated ACK/absence certificate | 36/36 |
| Native ticks containing at least one real source ACK grant | 286 |
| Real source ACK grants with verified **exact** rank | **329** |
| Source-delivered native-due controls | 1,096 |
| Native-horizon **censored**, grant threshold not reached | **767** |
| Explicit post-native deliveries, excluded from native-ready | 56 |
| Ticks where another actor waits during global grants | 162 |
| Contexts with at least one such tick | 49/72 |
| Largest observed due-queue grant rank | 16 |

Accounting: `1,096 = 329 + 767`; the 56 post-native deliveries are kept
separate. These are sums over the 72 replay contexts, not unique global
judgments or a population estimate.

### Adversarial boundary

- A *causally valid* ACK for B bypassing an older pending ACK for A passes
  the inherited per-actor custody checker but is **rejected** by the new
  independent FIFO-prefix verifier.
- Duplicate grants, forged ACK custody, altered due tick, ledger counters,
  changed predecessor JSON and changed source SHA are rejected.
- An explicit no-grant tick only censors ready controls; it cannot create
  a negative vote, absence certificate or learning state change.
- Post-native delivery is distinguished from a native-due judgment; a
  fabricated ninth external event is not admitted by the source fixture.
- Source-owned identity and ordering are not cryptographic authentication.

The preceding v3q–v3s report and every inherited source is SHA-256-pinned
and rechecked after replay. Output JSON is canonical, deterministic,
**create-only**; use an unused output path.

### Reproduction on `fwork`

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3tuv_Finite_Grant_Rank_Cumulative_Milestone.tar.gz

bash search/spk_bv_v3tuv_grant_rank_cumulative_gate.sh \
  /tmp/spk-bv-v3qrs-actor-service-gap.json \
  /tmp/spk-bv-v3tuv-grant-rank.json

bash search/spk_bv_v3tuv_inherited_regression_gate.sh
```

Do not re-use an already existing JSON output file. `REJECTED` text from
deliberate adversarial tests is expected if the parent unittest finishes `OK`.

### Contractual stop and honest roadmap

Native per-actor fair scheduling, minimum global grant-opportunity rate,
bounded wall-clock service, native neuron update/learning and mesh transport
semantics remain **unproven**. In particular, a finite rank theorem cannot
conjure new PE service opportunities after the observed native horizon.

| Simulator/Compiler phase | Progress | Delta |
|:--|--:|--:|
| S1 | 100% | 0 pp |
| S2 | 100% | 0 pp |
| S3 | 60% | 0 pp |
| S4 | 0% | 0 pp |
| S5 | 0% | 0 pp |
| **Equal-weight total** | **52%** | **0 pp** |

An additional finite research certificate does not satisfy an unfulfilled
native release criterion; it cannot justify moving the percentage.
