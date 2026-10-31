# SPK/* Back Validation v4j–v4l — native ACK shadow slot arbitration

**Status:** `COUNTERFACTUAL_NATIVE_SLOT_ARBITER_NO_CAUSAL_REEXECUTION`

**Scope:** isolated research over signed native executions and derived-source
ACK contexts. **No change** to SPK Core v0, Network v0, Compiler v0,
Architecture v1 or frozen `live_dual_scheduler_v0e.py`. This is a bounded
**shadow service-slot arbiter**: not an operational native ACK scheduler,
receiver delivery, learned update, runtime policy, or proof of deadlines.

## Technical question

The preceding v4g–v4i frontier showed that, in the original native execution,
W=4 ACK windows cannot all be served solely in unused PE and O/E memory
capacity. An unconstrained mathematical candidate tick is not necessarily
available for a real ACK service. Which **identified native PE operation**
would be displaced if one additional shadow ACK slot were proposed, and what
remains unproven after that choice?

## Versioned research steps

1. **v4j — typed native PE accounting.** Rerun and digest-check all 18
   original native executions. Identify forward-computation batches with
   their node and PE, and existing native BV grants with their sender PE.
   Per native tick, reconcile every typed forward/BV operation with the
   original PE service counters; reject any mismatch or identity collision.
   The source has **640 tick records and 624 typed PE service units**.
2. **v4k — resource-gated shadow arbiter.** For each of 72 signed derived
   source ACK contexts, observe the original ready/no-grant runs. Compare
   `deadline-only` to `opportunistic-spare` for W in `{2,4,8}`. The strict
   mode admits only genuinely spare original owner/global PE and O/E memory
   capacity. The conditional mode may *hypothetically* replace exactly one
   identified native PE service, with either forward or BV preferentially
   protected. It **never** reclaims the donor's memory: the new ACK O/E
   charge must fit independently. Both strategies make online decisions on
   the original fixed timeline, without future-tick access.
3. **v4l — adversarial custody and no-adoption gate.** Test PE/owner mismatch,
   O/E memory exhaustion, forged native totals, source digest drift,
   identity conservation, deterministic comparative outcomes and create-only
   output. Every would-be donor is retained in an **unresolved native service
   debt ledger**, never silently marked as executed at another tick.

## W=4 measurements — related source contexts, not independent trials

| Shadow mode | Strategy | Complete finite source-window coverage | Synthetic ACK slots | Native PE services that *would* be displaced |
|---|---|---:|---:|---:|
| Spare only | Deadline only | 13/72 | 120 | 0 |
| Spare only | Opportunistic spare | 22/72 | 257 | 0 |
| Conditional PE reassignment, protect forward | Deadline only | 72/72 | 399 | 291 (190 forward, 101 BV) |
| Conditional PE reassignment, protect BV | Deadline only | 72/72 | 399 | 291 (195 forward, 96 BV) |
| Conditional PE reassignment, protect forward | Opportunistic spare | 72/72 | 537 | 280 (182 forward, 98 BV) |
| Conditional PE reassignment, protect BV | Opportunistic spare | 72/72 | 537 | 280 (184 forward, 96 BV) |

These are **per-context synthetic reservation totals** on overlapping
native replays. A context being fully covered means only that each complete
W-tick interval of the *original fixed ready/no-grant trace* contains a
synthetic reservation. It does **not** mean its ACK was actually granted,
received, credited or executed. No output state or subsequent native
services are recomputed after a donor is hypothetically displaced.

**Avoid vacuous coverage:** only **65 of 72** W=4 contexts contain at least
one complete four-tick source-ready/no-grant window. The remaining seven
are counted as covered because there is no qualifying window to miss. Thus
the substantive W=4 comparisons are **6/65** (strict deadline), **15/65**
(strict opportunistic), and **65/65 conditional**, still purely synthetic.
For W=2 all 72 contexts are nonvacuous; for W=8 only 56 are.

In particular, the conditional result **72/72 is not an implementation
success**. It exposes the size and identity of the native causal debt that
must be rescheduled and verified by a real versioned scheduler. The spare-only
result is the actual observed resource constraint on this fixed source.

## Sensitivity by ACK window size

For conditional PE reassignment (protect forward):

| Source window | Deadline-only reservations | Deadline-only native donor units | Opportunistic-spare reservations | Opportunistic-spare native donor units |
|---|---:|---:|---:|---:|
| W=2 | 846 | 626 | 1128 | 610 |
| W=4 | 399 | 291 | 537 | 280 |
| W=8 | 161 | 120 | 232 | 112 |

All 72 contexts obtain finite source-window *coverage* under the conditional
counterfactual for W=2/4/8. A shorter window produces more proposed work
displacements. An opportunistic strategy can reduce donors at the cost of
many additional spare-slot reservations. These are **not** measured output
latencies, energy usage, or transport costs.

## Explicit limitations and next admission boundary

- The input is exogenous: the original derived-source readiness, grants and
  FIFO ranking are **not recomputed** after a synthetic reservation.
- No displaced forward/BV service is reexecuted later. Reordering one source
  operation can change downstream spikes, packet generation and PE/memory
  occupation; this causal graph has not been replayed.
- No receiver-side credit, real ACK link arbitration or payload delivery is
  performed. A slot is only a resource reservation *proposal*.
- Conservatively, the conditional donor frees just one PE unit; O/E and owner
  memory must independently fit the new candidate. This is a modeled
  sufficient memory guard, not a proof that a different scheduler is impossible.
- Source windows are finite. No guarantee extends to unfinished tail debt,
  fresh arrivals after the horizon, native forward fairness or BV liveness.
- 72 contexts reuse 18 native traces; they must not be read as 72 independent
  real-world experiments or as a probability sample.

The next useful engineering gate is a **separate, versioned native causal
reexecution prototype** with explicit owner PE authority, O/E custody,
real ACK credits/link services, rescheduling and preservation of forward/BV
causality. The frozen runtime should remain untouched until such a variant
has independent negative tests and a formal admission decision.

## Reproduce safely on fwork

Extract this research overlay into the existing Back Validation checkout;
use `--keep-old-files` so the archive cannot overwrite prior files. Provide
the four existing **signed** predecessor reports and a *new* output path:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_BV_v4jkl_Native_ACK_Shadow_Arbiter_Research_Milestone.tar.gz
bash search/spk_bv_v4jkl_native_ACK_shadow_arbiter_gate.sh \
  /tmp/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4abc-native-contract-candidate.json \
  /tmp/spk-bv-v4def-native-capacity-envelope.json \
  /tmp/spk-bv-v4ghi-exact-native-coverage-frontier.json \
  /tmp/spk-bv-v4jkl-shadow-arbiter.json
bash search/spk_bv_v4jkl_inherited_regression_gate.sh
sha256sum spk_backvalidation_v0/live_dual_scheduler_v0e.py
```

The required frozen native source SHA-256 is
`2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
The CLI refuses altered code and signed reports, symlinks, missing files,
changed native replay digests and output overwrites. The output report is
create-only. **No application or release adoption is authorized.**
