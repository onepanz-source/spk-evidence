# SPK BV v0l · Native typed provenance dossier (research)

## Scope

An incremental **read-only** v0k capture analyzer. It operates on the actual source-bound capture produced by v0k, rather than re-executing v0h. It does not invent `transmission_id`, `batch_id`, `context_id`, `path_id` or `transport_units` for the v0i ledger. It does not assume one link grant = one physical transmission.

The captured reference described in the October 17 fwork log has 22 entries at `$[3]/feedback/deliveries`, 22 at `$[3]/feedback/link_grants`, 5 at `.../assessments`, and 17 at `$[3]/forward/batches`. These are separate, small-case structural observations; the larger v0h stress witness observed **528 feedback packets and 33 unique receiver votes**. These are not interchangeable sources.

## Research output

- Revalidate v0k capture envelope, canonical fixture SHA256, typed container format, shape report, symlink and resource limits. Keep source pins as evidence of capture origin but not as signed attestation.
- Enumerate four *actual* typed-sequence paths. Compute per-group source-preserving count, sequence hash, row-content multiset digest, repeated rows (without collapsing them), shape signatures and coverage of native scalar paths (up to 3 levels).
- Report optional **explicitly requested** scalar samples (`--sample-values 1`), which might disclose test information. Default is schema and hashes **without values**.
- Reject missing, ambiguous or malformed paths rather than using synthetic fallback records.
- Preserve `native_v0h_verified=false` and expressly exclude source-to-v0i packet bijection, link-grant pairing, large 528-packet witness equivalence, causal credit, hardware cost, compression and learning.

## Install

```
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/spk-bv-v0l-native-typed-dossier-research.tar.gz
bash search/spk_bv_v0l_research_gate.sh
```

## Real native fixture dossier

The following is strictly a **read-only** analysis of the v0k JSON capture, not a native fixture invocation:

```
python -m search.spk_bv_v0l_dossier \
  --capture /tmp/spk-bv-v0k-native-fixture.json \
  --out /tmp/spk-bv-v0l-native-dossier.json \
  --expected-fixture-sha a580e8382ef18c04c479f4f969b2150efe4cb6a14f1f4d835e5a62c8015da8b0
```

Output must not exist (no overwrite). For scalar examples useful to build a strictly evidenced adapter, run again with another output and `--sample-values 2`, carefully reviewing any sensitive trace contents before sharing. Neither result alone proves physical feedback-packet identities.

Then run the existing full regression:

```
bash search/spk_bv_credit_v0a_full_regression.sh
```

## Acceptance for next integration step

1. Inspect the real v0l dossier's delivery and grant scalar-field inventories; determine whether unique physical packet identifiers, receiver, origin, batch, context and observed/birth ticks are actually present.
2. If fields are missing, identify the native source that owns them; expand *research-only* observability instead of deriving fabricated IDs from array position.
3. Design an explicit source-to-v0i mapping with anti-collision, exact row conservation and an independent native v0h replay witness. Only then evaluate cost and capacity effects.

This checkpoint does not affect frozen Architecture v1 or v0h native producer files.
