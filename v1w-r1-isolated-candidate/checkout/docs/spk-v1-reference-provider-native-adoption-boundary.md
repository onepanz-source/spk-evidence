# SPK V5 T10ABC/DEF/GHI: synchronous reference P admission provider

**Status**: research-only V1 provider, NOT a native SPK Memory Contract implementation. Frozen Core/Network/PE/BV and Architecture v1 MUST NOT be modified.

## Objective

Earlier T9STU added a durable SQL fence requiring a reference grant and completed C semantic event. The authority/decision was still implicit in the scheduler inserting `p_grant`. T10 introduces a **separate provider admission decision** invoked by the P store *during the actual `SEM_B_C` tick*, plus an additional persistent provider receipt written in the same SQLite transaction as the change to P.

This is genuine logical separation and a fail-closed provider veto in the **host-controlled research runtime**; the provider and store still share one host, process, SQLite connection and fault domain. It is not a cryptographic or privilege boundary. Do not label its grants SPK-native.

## T10ABC: provider at the P-write boundary

- New `ProviderFencedTickEngine` subclasses the T9 reference engine without changing prior source. On every `UPDATE p`, a T10 SQL trigger calls `spk_ref_v2_provider_authorize` synchronously.
- The registered provider checks exact owner C, domain P, execute mode, PE-C-RESEARCH, cue, P version and bounded transition; the grant is coupled to the decision episode's `SEM_B_C` tick, `SEM_A_B` relay, A event and the original frozen PE A computation.
- The existing three T9 fences remain active. New code adds two triggers and verifies their canonical definitions at initial creation and after database reopen.
- A second T10 SQL trigger commits a durable, unique `reference_provider_receipt` record with source event ID and digest. Its absence aborts the transaction.

## T10DEF: outcome parity and actual grant counts

96 episodes, same synthetic tasks and four phases as T9. Preserve the T9 exact output result counts and scheduling costs:

| Admission | Successes | Waves | Stale vetoes | Provider grants/commits |
| --- | ---: | ---: | ---: | ---: |
| Fixed control, 3 in flight | 48 | 32 | 0 | 0 |
| Free 3 in flight | 84 | 32 | 4 | 8 |
| Context affinity | 88 | 48 | 0 | 8 |
| Serial | 88 | 96 | 0 | 8 |

A second context-affinity run reopens the entire SQLite engine between every wave; output digests and provider receipts must remain equal. Provider counts, grants, and P versions are independently auditable. These “waves” are NOT physical latency or energy.

## T10GHI: failure cases and promotion guard

1. Disable the provider after four forward/relay ticks and before `SEM_B_C`. The fifth tick must reject, rolling back the whole event transaction, including tentative event state and `p_grant` insertion. P remains unchanged.
2. Reopen and restore the provider, then process the queued C event once. The provider grants once, records the committed receipt, and preserves it across restart/replay.
3. Two same-version negative judgments admit one grant; second verdict remains visible but receives no P authority. Late feedback (tick 19) remains an observation only.
4. Direct P UPDATE/INSERT/DELETE, altered triggers and tampered reference receipts fail the reference audit.
5. Native SPK `Memory Contract` is **not connected**. A typed target is projected but `native_authorize` deliberately denies. `native_SPK_P_grants=0`, `native_SPK_P_writes=0`, `native_learning=false`, `promotion_allowed=false` MUST hold.
6. A privileged host can modify both trigger/provider code and the SQLite database, forge A goals/source events, then reseal. The evidence does not establish independently authenticated sources, native transport or hardware learning.

## Adoption requirements beyond this reference

A future versioned native provider must be *part of an adopted SPK runtime*, bound to its real memory domain P and to authority not derivable by freely editing user-supplied evidence. Validate target IDs, isolation between PE owners, resource budgets, versioned custody, revocation/expiry, persistence and crash semantics, and adversarial provenance before making any native-learning claim. Real native grant/commit counters must come from this implementation, not from a renamed reference grant.

## Reproduction

Add-only archive extraction: `tar --skip-old-files -xzf <archive>` at the repository root. Run `bash search/spk_v5_t10abc_def_ghi_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t10abc-def-ghi-cumulative.json`.

The gate verifies 19 cumulative manifests and 12 original source pins, runs the genuine BV-v0e admission preflight on `fwork`, runs all 19 cumulative suites, then performs two byte-identical full reports. Local partial staging has a PE fabric test shim for unavailable admissions: **the full native preflight and 12-source custody have not been executed here**.
