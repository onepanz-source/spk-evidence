# SPK V5 / T4DEF · One-BV-source structural experiment (research only)

## Motivation and evidence

T4ABC located the host selection in `spk_v5_research/island_source_bv_bridge_v5t3o.py`: the original `evidence()` extracts A1b C sign, calls two frozen BV-v0e passes (`terminal_channel` 30 and 31), then correlates the chosen observer result a posteriori.

## Scope grouped in this checkpoint

- **T4D · source-locus custody:** pinned T4ABC dossier + five original research modules + three frozen legacy modules; AST checks original post-hoc two-pass logic.
- **T4E · single frozen BV invocation per case:** research case with both C `EMIT(11)` and `EMIT(12)` mirrored to a single terminal `EMIT(30)`; BV-v0e is invoked once with terminal 30. The separately executed original T3h A1b program supplies the semantic sign **outside this BV invocation**. Original frozen scheduler and computation modules are not touched.
- **T4F · differential falsification:** reproduce 180 original truth-table conditions, compare structural eligibility count against the T3OPQ baseline (42 eligible, 138 rejected), check 36 positive and 36 negative original T3h signs, repeat in a fresh Python process and compare reports byte by byte, and forbid promotion.

The shared terminal means **BV-v0e receives no positive/negative sign distinction**. Even if this checkpoint passes, it proves only that one *structural* source invocation can be used for both signs, using an independently computed T3h semantic result. It DOES NOT prove a single execution with receiver-authored semantic credit. It does not prove a neuron learning mechanism, independent authenticated C sensor, source-to-receiver identity attestation, physical cost, blind goals, or transfer across devices.

## Commands on Fedora / fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4DEF_Single_BV_Source_Research_Milestone_20261022.tar.gz
bash search/spk_v5_t4def_single_source_gate.sh /tmp/spk-v5-t4def-single-source.json
```

The default source dossier is `/tmp/spk-v5-t4abc-causal-origin.json`, from the preceding gate. Alternatively pass its existing path as the **second** argument. The first argument is a **new, nonexistent** output path; the script does not overwrite previous reports.

## Invariants

- Source pins fail closed on mismatch.
- An `assessments` entry without a real C terminal and source ancestry is rejected.
- BV-v0e service/memory/grant accounting is checked with the original T3OPQ requirements.
- Missing marker, missing C sensor, missing forward or reverse channel cannot cause a positive update.
- The T3h sign is identified as being produced by a different A1b invocation, not authenticated by the BV-v0e receipt.
- Research output contains `native_semantic_BV_proven=false`, `native_learning_proven=false`, `promotion_allowed=false`.
- `F_research_structural_eligible` is only structural lineage + separate T3h gate; not task-utility credit.

## Local verification scope

30 standalone Python unit and adversarial tests pass against the uploaded original five-source bundle. They use synthetic BV fixtures and do NOT substitute for running the real `execute_live_v0e` on fwork. Only the above gate on the user's actual repository runs the real frozen scheduler. The baseline parity assertion is a falsifiable research hypothesis; a mismatch must be investigated, not papered over.
