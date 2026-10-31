# SPK BV v0i: Evidence & Transport Cost (research-only)

## Problem
The BV v0h replay reported 528 feedback packets, 495 duplicated-path
receptions, 33 distinct receiver votes across a max-neurons-64 scenario,
and one extra batch resolved in the same tick. These figures are **observed
external gate evidence**, not something the v0i module has verified by
reading the original v0h trace.

v0i separates each *physical reception* from the *contextual vote* it may
represent. It does NOT create credit, a learning signal, local program
adaptation, deduplicating transport, compression, or new scheduler policy.

## Exact identity semantics

- Physical transmission ID key: `(epoch, transmission_id)`. Replaying an
  identical audit record has no additional cost; a second actual physical
  transport observation MUST carry a new transmission ID. ID reuse with a
  different payload is an error.
- Identified batch key: `(epoch, origin, batch_id)`. Every reception of a
  batch must agree on its originating `batch_tick`.
- Contextual vote key: `(epoch, origin, batch_id, receiver, context_id)`.
  Distinct batches in the same tick, different receivers, and different
  contexts remain distinct. A vote with the same key and conflicting
  `evidence_code` is rejected. A vote is not a statistically independent
  piece of evidence by virtue of having a distinct key.
- Route/path and observation tick do not change a contextual vote's key.
  They DO change the physical trace and its transport cost.
- Tokens (`evidence_code`) are opaque symbolic labels. No positivity,
  truth, usefulness or reward is assigned.

## Cost semantics

The caller assigns each observed transmission a strictly positive integer
`transport_units`. Units represent an **abstract accounting choice**, not
measured bytes, cycles, bandwidth, wall-clock latency or joules. Totals are
additive across recorded physical transmissions. Offline hypothetical
per-tick and per-link limits report overloads but NEVER drop, suppress,
reserve, schedule or arbitrate traffic. Real spike traffic and host runtime
resource arbitration are **not** modeled.

`physical_transmissions / distinct_contextual_votes` is only an
amplification indicator. Zero denominator means undefined. The count
`physical_transmissions - distinct_contextual_votes` is the number of
additional receipts, not a proof they can be removed.

## Output hashes and replay

`physical_sha256` hashes the canonically ordered set of physical records,
while `contextual_vote_sha256` hashes the canonical distinct vote ledger.
Adding a new physical path for an existing vote changes the first hash,
not the second. Reordering inputs does not change either hash. JSON
canonicalization uses sorted keys and compact ASCII with no floats.

## Integration boundary

v0i uses a stand-alone **normalized input contract**. It has no direct
import of BV v0h source files: their exact Python API is not present in
this handoff. Therefore the synthetic 528/33/495 witness proves only the
v0i contract, not equivalence to the genuine BV v0h trace. The next
integration step must implement a read-only v0h -> Reception adapter,
verify a packet-for-packet bijection, and independently cross-check
`528/495/33` and the original v0h evidence SHA against its original trace.
No assumptions should be made about the meaning of `context_id` or
`transmission_id` until that adapter is defined against actual v0h records.

## Complexity and boundedness

For `P` unique transmission IDs and `V` unique contextual vote keys,
stream ingestion is expected O(P) dictionary work with O(P + V)
retained memory; canonical snapshot is O(P log P + V log V).
Hard `max_transmissions` and `max_votes` bounds prevent unlimited
ledger growth. On inconsistent provenance the module raises without
partially admitting the rejected reception. Batch `ingest_all` is
sequential, not a transaction over the entire iterable.

## Execution

From the SPK research worktree (not the Architecture v1 frozen tag):

```bash
bash search/spk_bv_v0i_research_gate.sh
bash search/spk_bv_credit_v0a_full_regression.sh
```

The complete regression is inherited, not shipped in this bundle;
its six branch-custody exclusions remain as established by the project.
Do not tag/promote before the live v0h adapter and full original gate
reproduce an independent end-to-end witness.

The self-contained synthetic test deliberately exercises 64 distinct
observed neuron IDs; it does not reconstruct the original BV v0h run.

### Reading a normalized v0i event trace

```bash
python -m search.spk_bv_v0i_ingest_ndjson --input normalized-v0i.ndjson \
  --max-units-per-tick 250 --link-budget link-0:60
```

The input must contain exact `Reception.as_dict()` keys. Its exporter is
not supplied because the native BV v0h event API/schema remains unseen.
Only run this on data normalized against that native schema; never
fabricate a mapping from the summary output alone. This CLI rejects
malformed/contradictory records without emitting a partial result.
