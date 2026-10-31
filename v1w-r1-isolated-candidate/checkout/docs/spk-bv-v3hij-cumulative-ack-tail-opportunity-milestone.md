# SPK BV v3h–v3j — finite native-safe ACK tail opportunities

Source-derived actor research only. Frozen native BV scheduler, Core/Network,
Compiler and Architecture are not modified or rebound.

## Three research steps

* **v3h:** repeat 27 signed native contexts, with strict native-forward and
  native-feedback priority preserved, testing two *real* derived ACK service
  quotas: one or two global ACK grants per tick, at most one per actor.
* **v3i:** cut the genuine actor-control tail at 0, 1, 2, 4, 8, 16 or 32
  ticks plus two adaptive cutoff witnesses. Confirm that extending the
  permitted service horizon never rewrites any already-issued ACK: smaller
  canonical journals are exact causal prefixes of the largest one.
* **v3j:** find the **minimal observed** tail horizon `H` which actually
  clears the source-delivered controls. `H` must finish, while `H−1` must
  leave pending controls if `H > 0`. Compare this real finish point to the
  resource-theoretic lower bound based on global capacity and per-actor
  throughput; use independent zero-credit and transport-loss nulls.

## Pinned measured matrix

| Source-backed measure | Result |
| --- | ---: |
| Original native executions (nine schedules × three BV arms) | 27 |
| Derived quota/tail horizon executions | 454 |
| Independent causal nulls | 54 |
| Verified original-native result projections | 454 + 54 |
| Exact ACK journal prefix comparisons | 454/454 |
| Monotone ACK service capacity comparisons | 400/400 |
| Verified cutoff `H` succeeds, `H−1` insufficient | 54/54 |
| Lower bound met for each finite source context | 54/54 |
| Longest necessary finite tail, global ACK quota=1 | 16 ticks |
| Longest necessary finite tail, global ACK quota=2 | 8 ticks |
| Sum of necessary ticks across 27 native contexts, quota=1 | 265 |
| Sum of necessary ticks across 27 native contexts, quota=2 | 138 |
| Real delivered controls across each quota group | 330 |

Here `H` is measured relative to the completion of the *unchanged frozen
native source*; it is not a bound on time since receiver judgment creation.
The native-ready veto may last arbitrarily long outside the pinned matrix.

The measured lower bound is
`max(ceil(N_tail/global_quota), max_actor N_tail_actor)`; it is attained in
all 54 finite contexts **after native completion** for the selected two-PE
source budget, due times and tail service plans. This is an observed finite
capacity-optimal drain, **not** a proven universal schedulability theorem.

With a zero-tick tail, delivered-but-unACKed packets remain pending, not
negative receiver evidence. Source loss admits no control; zero-credit
policy may deliver judgments but does not issue an ACK. Both remain exact
native projections. An ACK still differs from an independently PE/memory
charged actor consumer receipt.

## Commands on `fwork`

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3hij_Cumulative_ACK_Tail_Opportunity_Milestone.tar.gz

bash search/spk_bv_v3hij_ack_tail_opportunity_cumulative_gate.sh \
  /tmp/spk-bv-v3efg-native-veto-attribution.json \
  /tmp/spk-bv-v3hij-ack-tail-opportunity.json

bash search/spk_bv_v3hij_inherited_regression_gate.sh
```

The report is canonical, create-only, SHA-pinned to its v3e–v3g signed
predecessor and frozen/source-derived ancestor scripts. Repeated attempts
must use a new output filename; never overwrite historical evidence.

## Boundary and roadmap

We have measured finite source opportunity *after* the frozen native
timeline, subject to explicit PE/RAM quotas. We still lack a native
guaranteed-free-slot/fairness/priority contract during unbounded native
work, so no universal ACK service deadline, starvation-freedom or native
learning is promoted. Next: define/test a genuinely source-backed
native-scheduler opportunity assumption, with an explicit failing
counterexample when its premises do not hold.

Roadmap unchanged: S1=100%, S2=100%, S3=60%, S4=0%, S5=0%,
equal-weight total=52%, Δ=0 points. Stage labels are research iterations,
not percentages of correctness or remaining mathematical proof.
