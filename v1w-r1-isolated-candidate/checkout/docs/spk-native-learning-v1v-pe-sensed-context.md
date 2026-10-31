# SPK Native Learning Runtime v1v · Bounded PE-sensed context port

## Scope

This macro-intervention removes the host **context string** argument from the new v1v entrypoint. An observation batch containing original channel occurrences is evaluated by two separate invocations of the **frozen original** `spk_architecture_v1.pe_execution_v1b._compute_local` (a PE instruction fragment `ACC/CMP/EMIT/RESET`). A single recognized PE signature binds to an internal `ctxN` assigned by observation order. The resulting identity indexes the existing v1u durable P bank, and the existing v1t same-scheduler A→B→C learning handles the episode.

It does **not** reimplement the frozen BV-v0e, replace its source, authenticate sensory channels, infer the host-defined goal, or learn arbitrary signatures. The classification happens at the **pre-episode admission port**, not on the reverse BV transport. Old direct v1u callers can bypass this optional port, a limitation stated in the release report.

## One macro-gate; no sub-milestones

- Original-source SHA-256 chain (PE, BV-v0e, causal memory) and all v1r/v1s/v1t/v1u manifests; exact v1u report SHA `7032bd...`.
- Original PE provenance check: the loaded `_compute_local` is the original object also used by the versioned scheduler. No test-bypass in the production report or release gate.
- Two **disjoint PE computations**: paired channels `40 + 42 → 71`, `41 + 43 → 72`. Neither one nor both emissions are accepted. An optional uninformative channel `99` leaves the class unchanged; exact duplicate occurrences, illegal channels and noncanonical batches fail closed.
- Separate durable SQLite `sensed_bindings` and `sensed_epoch` ledgers: observation, PE evidence, internal context binding, PE source SHA and chained record digest. Context P and PE evidence must agree on every replay. A dangling last selector can recover after an interrupted admission.
- Five epochs (two contexts, two with previously unseen noise) recompute versions `2,1,2,1,3`, with 325 tick records and zero new ticks when rerun. The genuine frozen PE reads P after context selection.
- Reverse first-observation order: internal `ctx0` and `ctx1` swap names, but PE-signature-to-final-P association does not.
- Seven simulated tick interruption boundaries, cooperative two-process serialization, intentionally corrupted sensor/selector/P ledgers, absent/ambiguous/repeated cues and direct older-API bypass detected by v1v audit.
- Inherited v1/v1r/v1s/v1t/v1u and T14–T17 tests plus two byte-equal full-checkout conformance reports.

## Meaning of PASS

`V1V_PE_SENSED_CONTEXT_P_RECALL_PASS` says **PE-generated signatures select previously learned P without host-provided context labels**, and the P is indeed read by C in the versioned BV-native learning scheduler. The source is still host-written, the PE feature fragment and candidate cues are predefined, and the goal is still set by the host. No broad context inference, host-resistance, authenticated sensor or frozen v0e learning claims are licensed.

The checkpoint tests the *classifier's deterministic cue mapping and durable causal binding*. This is an integration milestone, not an independent scientific evaluation of unsupervised context formation or generalization. A privileged host can alter and reseal both the database and its provenance. The lock is cooperative POSIX `flock` only, and genesis replay cannot safely repeat irreversible external actions.

## Usage

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_Native_Learning_V1V_PE_Sensed_Context_Macro_20261023.tar.gz
bash search/spk_native_learning_v1v_sensed_context_macro_gate.sh \
  ~/workspace/spk-evidence/spk-native-learning-v1v-pe-sensed-context.json
```

Archive is **incremental** and must be installed after v1u. It contains only new v1v files. Report output is immutable. All original frozen sources and v1u records are kept unchanged.
