# SPK V5 T7ABC + T7DEF + T7GHI: genuine BV-v0e epoch execution + research P-state

Research-only and additive. **The original frozen `execute_live_v0e`, `_compute_local`, three-neuron admission, service/resource arbitration and two-hop BV are used in each epoch on `fwork`.** No copy of frozen BV or PE is included; source integrity and 12 pinned dependencies are checked.

## T7ABC: no copied scheduler

C issues **11 or 12** according to a research-owned P state. The preexisting BV-v0e scheduler computes actual `C -> B -> A` PE outputs, A writes outcome emission **21** (objective met) or **22** (not met), and A's terminal **7** causes genuine *structural* BV packet transport `A -> B -> C` with resource grants.

**Crucial boundary:** `A -> B -> C` BV packets do **not** carry 21/22. The host adapter associates the separate A semantic emission with the structural delivery. This is not an authenticated native BV assessment or a semantic message carried by native BV.

## T7DEF: transactional versioned state, not native P

The host-side research adapter stores C choice/versions in SQLite WAL (FULL synchronous), serializes whole epochs, and only commits a wrong-choice correction when both the separate A verdict and native BV structural route were observed and accepted. The next host-authored C *instruction tuple* reads the updated choice. The frozen SPK Memory Contract and PE-owned P domain are never changed.

The original BV-v0e scheduler only admits A/B/C; the previous 4-node A+D test **cannot** be described as executed in BV-v0e. This checkpoint verifies a single A within its actual domain.

## T7GHI: controls, restart, missing path, threat model

96 episodes across 4 host-authored goal regimes compare fixed vs adaptive C with identical goals; 24 stationary episodes further test adaptation; loss of C->B routing prevents both A verdict and BV credit; a pending episode survives restart and commits once. A deliberately forged host evidence record is still accepted by the state adapter if verification is bypassed. SQLite hash chaining detects accidental damage, not adversarial full rewrite.

## fwork one-command gate

```sh
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T7ABC_DEF_GHI_Frozen_BV_Epoch_Adapter_Cumulative_20261022.tar.gz
bash search/spk_v5_t7abc_def_ghi_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t7abc-def-ghi-bv-epoch-bridge.json
```

## Truthfulness boundaries

- No independently authenticated C identity, A sensors, A goal authority, physical causality, or hardware security.
- No native BV semantic verdict, BV credit, SPK P-memory update, native learning or frozen contract change.
- The *same original BV code* ran here in a local harness with **substitute admission dependencies**, but full original admission/profile can only be established by the complete `fwork` gate. Never present those local results as a full original-architecture gate.
- The verified counterfactual is **internal to a synthetic three-neuron case** and to a series of research-managed epochs.
