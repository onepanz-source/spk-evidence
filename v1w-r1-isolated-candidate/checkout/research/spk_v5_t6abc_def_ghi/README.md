# SPK V5 T6ABC/DEF/GHI: executable PE-fragment closed-loop adaptation (research only)

**A single cumulative checkpoint**, not three separate release gates.

## Scope

1. **T6ABC**: C makes an actual `_compute_local` PE choice (`EMIT 11/12`). B recomputes the relay (`EMIT 31/32`); A obtains its measured integer output (`ACC -> raw 5/11`) via the exact *unmodified* frozen PE implementation. A compares with its own local target. The judgment returns A → B → C, each with a new PE computation.
2. **T6DEF**: C has a strictly bounded experimental, per-context selection table. A negative feedback with intact decision custody changes the next selected *instruction program*. C does not modify the frozen computation function. Matched 48-episode training/control runs use the identical cues and initial policy; only the update switch differs.
3. **T6GHI**: 48 matched interventions force the opposite **experimental C output channel**, recomputing the resulting B and A PE steps. Missing and late feedback, tampering, replay, conflicting feedback, concurrent stale policy versions, A data forgery and feedback-induced destabilization are all exercised.

### Acceptance (expected for this two-context toy example)

- 48 matched cues in each run; 48 forward and reverse paths each.
- Without updating C: **0/48** A goals satisfied.
- With updating C: **46/48** A goals satisfied, after exactly **2** valid local updates.
- C really produces a different next emission after receiving negative A feedback.
- 48 model-internal counterfactual pairs; a dropped C signal produces `A.raw=0`.
- Old policy-version feedback cannot undo the latest update. A privileged host can STILL mint a coherent but false A receipt and force a wrong update.
- Report byte-identical on two executions; source custodial pins and frozen source SHA unchanged.

### Explicit epistemic boundary

This uses the original frozen `spk_architecture_v1.pe_execution_v1b._compute_local` **as a callable instruction engine only**, with tiny host-authored Node-like descriptions. It does NOT execute `execute_on_pes_v1b`, the frozen BV-v0e scheduler, an authenticated sensor, or any native learning contract. It does not test generalization, statistical significance or a large neuromorphic network. A and B relay actions are host-driven PE-fragment calls. The reported internal counterfactual effect is identifiable only because the simulated graph is known and controllable.

The test purposely keeps a successful host-forgery counterexample. `promotion_allowed=false`, `native_BV_credit=0`, `native_learning=false` are mandatory and immutable.

### Usage

Extract this additive archive into an existing fully installed SPK BV v5 checkout. It never contains or overwrites frozen components.

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T6ABC_DEF_GHI_Functional_Closed_Loop_Cumulative_20261022.tar.gz
bash search/spk_v5_t6abc_def_ghi_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t6abc-def-ghi-functional-loop.json
```

Outputs are immutable-by-default; do not overwrite existing reports. Running the gate performs tests plus two independent executable audits and enforces a byte-exact comparison.
