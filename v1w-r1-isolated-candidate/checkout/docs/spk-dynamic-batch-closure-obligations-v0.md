# SPK S3.7d/3b2b2k/13 · Dynamic Batch Closure Obligations v0

**Status:** candidate, pending full gate on fwork. No Core, Network, or Compiler changes.

## Problem

`Dynamic Destination Inventory v0` reports what has been registered and where its occurrences reside. That does **not** exclude a future, not-yet-registered emission with the same destination `EVENT_TIME` when backpressure delays its `SERVICE_TIME` execution.

## Sound necessary conditions (not sufficient evidence)

For a candidate destination batch at neuronal time `t`, on *every* incoming network edge with source `s` and logical delay `d`:

- A verified source-emission frontier **settled through** `t-d` would exclude any *new* emission on that edge that could arrive at `t`. If `t-d < 0`, the obligation is vacuous because event times are nonnegative.
- A separate verified external-ingress frontier **settled through** `t` is required for the target node, **even when it has no incoming graph edges**. `SERVICE_TIME` and `EVENT_TIME` cannot be substituted.
- Every **currently registered** route for `(target, EVENT_TIME)` must be in `EVENT`. `STAGED`, `OUTPUT` and `CONSUMED` do not qualify for a new batch admission. Existing consumed identities remain historical, not freshly resident.
- Every physical occurrence is checked against the Core-derived registry by re-running `derive_dynamic_destination_inventory_v0`, retaining parallel-edge multiplicity and source/target provenance.

`analyze_dynamic_batch_closure_v0` returns a deterministic per-batch list of those obligations, missing frontier claims and blocked route identities.

### Trust boundary

`EventTimeClaimV0` is a **user-supplied, unauthenticated claim**. It is not derived from a live, single-owner scheduler or from an admitted external event ledger. Consequently, `declared_preconditions_met=True` means only that *the claims were arithmetically sufficient*. It is **not** a closure proof. All returned batches have `status='OPEN_UNPROVEN'`, `supports_consume_admission=False`; the analysis-level flag is also always false. No `BATCH_CONSUME` is created, admitted or confirmed. The function neither advances a clock nor mutates storage or neuron state.

No tick limit, silence period, or absence of pending currently known route identities is treated as proof of closure.

## Scope and next acceptance gate

This component determines *which proofs the authoritative scheduler must provide*. It does not provide those proofs. The next stage needs **single-owner authenticated monotone progress evidence** for source emissions, closure of external ingress event-time horizons, and accounting for all physical external events. Only then may a dynamic batch be *closed* and associated with newly created `BATCH_CONSUME` requests. Open-source/unknown future inputs must conservatively keep the batch open.

## Verification

```bash
python -m pytest -q tests/test_dynamic_batch_closure_obligations_v0.py
python -m pytest -q
```
