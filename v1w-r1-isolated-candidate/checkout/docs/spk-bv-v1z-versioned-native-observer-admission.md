# SPK BV v1z: Versioned Native Observer Admission Contract

**Research contract, NOT promotion**.  This additive release preserves the
frozen scheduler, Architecture, Core, Network, Compiler and all BV predecessor
artifacts.  It does not install a v2 native scheduler.  No true neuron B can
receive evidence yet. The target is a *separately named and pinned v2a executor*
whose source explicitly emits observations during its own execution.

## Evidence inherited from v1y.1

On fwork the external `sys.settrace` probe captured the frozen `execute_live_v0e`
code object with each of four cases (original/variant × BV OFF/ON), preserving
return bytes (`snapshot`-compatible typed fixture encoding). Python line hits
49 and 50, and the BV-only hits 150/206, are **syntax-level execution evidence**.
They are not spike events, not independent clocks or absence witnesses, not
producer-owned control packets. v1z validates the actual canonical v1y JSON
against the original canonical v1x report, including each result SHA-256, scopes,
negative authority constraints, return counts and trace restorations.

## Required next development: strictly versioned v2a executor

Never edit `spk_backvalidation_v0/live_dual_scheduler_v0e.py` or the frozen
`spk_architecture_v1/pe_execution_v1b.py`.  Create a new, explicitly versioned
experimental executor (e.g. `spk_backvalidation_v2/observed_scheduler_v2a.py`)
whose producer **owns** the observer callsite and its event semantics.  The
minimal suggested interface is `execute_live_v2a(..., observation_port=None)`;
its positional/keyword contract must be reviewed independently.  It must never
retrospectively replay v1y line counts and label them native events.

For promotion: verify event provenance and episode/decision binding, observe
online before executor return, independent authenticated recipient delivery,
predecision commitments, interval clock/closure with fault awareness, bounded
backpressure with fail-closed semantics, native observer OFF/ON result-byte parity
under the actual v2a implementation, a recipient-local value criterion, and
causal decision-to-event proof.  The v1z report marks all ten obligations
**unmet**, even if the reference examples succeed. A producer callback is still
not proof that B received or understood its message.

## Reference examples (non-native)

`ReferenceProposalPort` is a strictly bounded in-process test of the proposed
phase protocol: predecision expectation -> decision -> optional emission(s) ->
optional ingress(es) -> interval close. It rejects cross-decision records,
nonmonotonic ticks, malformed source/recipient, missing decisions, missing
closure, and overflow. Callback exceptions are contained, without modifying
forward result. Neither a close record nor a zero-emission example proves
absence, and no packet can be promoted to native authority.

The reference executor uses `seed=0/1/2` and proves its own typed return bytes
are invariant with the port disabled/enabled. It is not the native SPK scheduler.

## Run on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
bash search/spk_bv_v1z_research_gate.sh
python -m search.spk_bv_v1z_native_observer_admission \
  --v1y /tmp/spk-bv-v1y-native-external-probe.json \
  --v1x /tmp/spk-bv-v1x-reference-observation-port.json \
  --out /tmp/spk-bv-v1z-native-observer-admission.json
```

Input and output must be outside the repo, non-symlink and distinct; output
must not already exist. v1z validates previously attested evidence but does
not repeat v1y, and its report explicitly marks the v2a experiment `BLOCKED`.
