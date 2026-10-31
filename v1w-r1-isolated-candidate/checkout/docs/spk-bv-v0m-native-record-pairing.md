# SPK/* Back Validation v0m: source-bound native delivery/link-grant pairing (research)

## What the actual 2026-10-17 v0l dossier establishes

The independent dossier collected on `fwork` records **22** native `feedback/deliveries`, **22** `feedback/link_grants`, **5** `feedback/assessments` and **17** forward batches; native fixture SHA-256 `a580e8382ef18c04c479f4f969b2150efe4cb6a14f1f4d835e5a62c8015da8b0`.

All 22 deliveries and grants expose the native fields `packet_id`, `assessment_id`, `sender`, and `receiver`. Delivery has `tick`, `independent_receiver`, `evidence_ids`. Grant has `tick`, `delivered_at`, `wait`, `source_pe`, `target_pe`, `cross_pe`. Assessment has `id`, `batch_id`, `observer`, `tick` and `terminal_emission_id`; forward batches have `batch_id` and `tick`.

The *two shown* native examples associate grant `bv1` (dispatch tick 9, delivered_at 10) with delivery `bv1` (tick 10), and `bv2` similarly. These examples do not establish all 22 pairs. **The v0m CLI will verify the actual full capture**, not use the two samples for any identity lookup.

## Scope and required invariants

1. Only consume the user-recorded v0k JSON capture. No import/execution of the native v0h fixture; no changes to frozen Architecture v1 or v0h files.
2. Verify the entire v0k envelope, typed representation and fixture SHA via v0l's `load_capture`; compare all source-bound v0l group hashes, schema, field coverage, producer pins, selected test and scalar samples if present.
3. Require exactly one delivery and one grant for each native `packet_id`, with identical `assessment_id`, `sender`, `receiver`. Never pair by list ordinal. Reject unmatched, duplicate or conflicting IDs atomically, with no output file created.
4. Require the referenced assessment ID to exist uniquely and its `batch_id` to exist among uniquely named forward batches. These are integrity tests within the one captured fixture, not independently witnessed execution.
5. Verify integer tick relationships: `grant.tick <= grant.delivered_at == delivery.tick` and `assessment.tick <= delivery.tick`. Enforce nonnegative reported wait; check `cross_pe == (source_pe != target_pe)`.
6. Preserve the actual reported wait and observed PE flags. **Do not assert** that `wait` equals elapsed queuing latency, or that each grant is one hardware transmission. The joined hash is order-independent; the native fixture hash remains order-sensitive and source-bound.
7. Never construct `epoch`, `context_id`, `path_id`, `link_id`, `transport_units` or an independent causal vote. Accordingly **no v0i conversion** is attempted at this stage.

## Install / native verification on fwork

```
cd ~/workspace/spk-backvalidation-v0

tar -tzf ~/Scaricati/spk-bv-v0m-native-record-pairing-research.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0m-native-record-pairing-research.tar.gz

bash search/spk_bv_v0m_research_gate.sh

python -m search.spk_bv_v0m_pairing \
  --capture /tmp/spk-bv-v0k-native-fixture.json \
  --dossier /tmp/spk-bv-v0l-native-dossier.json \
  --out /tmp/spk-bv-v0m-native-pairing.json \
  --expected-fixture-sha a580e8382ef18c04c479f4f969b2150efe4cb6a14f1f4d835e5a62c8015da8b0

bash search/spk_bv_credit_v0a_full_regression.sh
```

Output paths must not already exist (never overwrite). The CLI returns `2` and emits no report on failures. Its report contains count metrics, source hashes, per-tick group counts and a deterministic joined hash, **not unredacted packet identifiers**. Use the new pairing file to review the results, not the full native fixture which can contain sensitive trace data.

## What remains excluded

- Independent source-to-observer v0h causal replay, production of 528-packet stress trace and cross-scenario equivalence.
- Native-to-v0i exact `Reception` translation: the fields required by the v0i ledger are not all present at delivery/grant level. Do not create synthetic epoch or contextual identities.
- Causal usefulness, learning, scheduling equivalence, compression, energy, hardware performance, cost advantage or a chip selection.

## Acceptance for the next checkpoint

If 22 paired native IDs pass, extend read-only research *observability* toward the 528-feedback stress case by recording actual native packet identities, contextual origins/batches and dispatch/delivery lineage there. Independently verify its source witness and compare its normalized, fully evidenced ledger only when the necessary fields are present. No changes to frozen Architecture v1.
