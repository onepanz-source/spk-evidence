# SPK/* Back Validation v1v: Frozen Runtime Observation Surface Audit

**Status:** research-only, source-pinned, read-only, not a native online feedback channel.

## Motivation

BV v1u attests a 58-session *incremental shadow laboratory* whose inputs came
from producer-owned native **post-hoc** traces. All 58 sessions have zero
native stream deliveries. Its researcher-owned clock, synthetic ingress,
identity seals and interval coverage do **not** constitute an online native
observation, source authentication, or independent absence witness.

Before engineering a native delivery adapter, v1v checks exactly which API
surface is actually available in the **frozen source checkout on fwork**.
No source is monkeypatched, wrapped with an instrumenting monkeypatch,
rewritten, or otherwise changed. The code never installs a listener, callback,
subscriber, receiver mailbox, or operator update.

## Audit procedure and evidence hierarchy

1. Verify v1u canonical report and the source-bound trust boundary, including
   58 unique `arm/mode/plan` session identities. Fail closed on forged native
   authority, altered reference SHA-256, missing sessions, or a changed sender
   count in the producer-only view.
2. In CLI source-audit mode, read *exactly* the frozen files under the checkout:
   `search/spk_bv_v0e_live_evidence.py`,
   `spk_backvalidation_v0/live_dual_scheduler_v0e.py`,
   `tests/test_spk_bv_live_dual_scheduler_v0e.py`,
   `spk_architecture_v1/pe_execution_v1b.py`.
3. Compare the first three complete file hashes to frozen evidence and the
   fourth to its pinned architecture SHA-256; additionally require the pinned
   AST digest and positional formal parameters of `_compute_local`.
4. Parse, **without executing**, the top-level `execute_live_v0e`, `fixture`,
   `_compute_local`, `_admit`, plus the `LiveBVPlanV0e` class, and record the
   public function formals, async/yield/return syntactic facts and *possible*
   callback-related argument names. These are **search hints**, not callback
   existence or event delivery attestations. E.g. an `on_event` formal without
   evidence of invocation and receiver delivery is insufficient.
5. Reconstruct v1u by invoking its complete previous CLI and requiring the
   existing v1u report to match **byte for byte**, then recheck source and
   predecessor immutability before writing the new report (`open('xb')`).

### Offline mode

`--contract-only` validates the v1u report and emits a conservative contract
without reading native source or replaying the predecessor. Its result has
`frozen_source_bytes_rechecked_in_this_run=false`,
`inherited_native_v1u_recomputation_verified_in_this_run=false`, and
`actual_native_API_surface=null`. The offline preview included with this
release MUST NOT be cited as a native inspection.

## Requirements before authenticating native feedback

The report lists eight mandatory, currently unmet integration prerequisites:
source-owned emission/ingress observation during execution; independently
receiver-accessible control delivery; predecision expectations and receipt;
independent clock, interval coverage and fault awareness; authenticated
source/episode identity; non-interference with frozen forward and BV
scheduling; an actual receiver-declared value criterion; and causal binding of
the recorded decision to the affected event.

The **absence** of a named callback parameter does NOT prove that no hook could
possibly be added or already exists via another mechanism. Conversely, the
presence of a callback-looking parameter does not prove that it is actually
called with a correct event at the correct time, nor that B can read it.
In either case, v1v does not promote the source-inspection result to an
operational channel, certificate of absence, endogenously scored judgment,
causal credit, learning, or an architecture change.

## Compatibility and gate

Five additive files only:
- `spk_bv_research/frozen_observation_surface_v1v.py`
- `search/spk_bv_v1v_frozen_observation_surface.py`
- `search/spk_bv_v1v_research_gate.sh`
- `tests/test_spk_bv_v1v_frozen_observation_surface.py`
- `docs/spk-bv-v1v-frozen-runtime-observation-surface.md`

Run the new v1v gate, then invoke the CLI with `--v1u` and the same previous
`--v1t ... --v0w` arguments used in v1u, plus `--out`. In full mode, the
frozen checkout must have exactly the pinned sources; mismatched or missing
source results in a nonzero exit and no attestation.

For an offline research-only report using the uploaded v1u document:

```bash
python -m search.spk_bv_v1v_frozen_observation_surface \
  --root . \
  --v1u /tmp/spk-bv-v1u-bounded-incremental-shadow-channel.json \
  --contract-only \
  --out /tmp/spk-bv-v1v-offline-contract.json
```

**Next step:** interpret the source-bound API inventory from fwork and select
an integration seam. If no adequate public event interface is verified,
propose an explicitly versioned new *additive* source-owned observer interface
and prove noninterference separately, rather than secretly patching the
frozen scheduler or replaying synthetic ticks as if they were native time.
