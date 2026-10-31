# SPK/* BV v0o: native paired-run discovery and declared comparison

## Why v0o is **not** yet a controlled A/B effect

BV v0n verified 22 native grant/delivery records, 66 native reported wait, 22 outstanding-record tick area, and peaks of 2/4 under distinct aggregation assumptions. It did **not** capture a feedback-disabled execution of the same workload. Consequently, subtraction of v0n measurements from any unrelated run would be false attribution.

BV v0o targets the existing `runs` pytest fixture of `tests/test_spk_bv_live_dual_scheduler_v0e.py::test_feedback_causes_forward_source_link_wait`, which exercises the live dual scheduler, but whose `runs` fixture structure is still unverified in the real worktree. **The contents of that fixture have not been reviewed in the user's repository.** We capture it without executing its test body and inspect it. Native pytest fixture setup and module import are executed locally: only run in a trusted repository.

- Capture requires source-byte hashes (test module and direct scheduler module, not a closure over every dependency) before and after fixture execution, and rejects output inside the repository or overwrite.
- Capture uses v0k's lossless typed codec, preserves list/tuple and dict identity, and refuses unsupported native types instead of fabricating a serializable representation.
- The independent-process gate compares captured payload SHA256 with `PYTHONHASHSEED=13` and `811`. Differing hashes => FAIL, not a forced common witness.
- Native inventory lists nested paths and container shapes to identify actual run keys and input manifests without assigning inferred ON/OFF labels.
- An **optional** config selects two explicit native run paths and one or more workload value paths within each; each selected witness must compare equal, otherwise FAIL.
- An optional declared comparison can extract exact scalar integer or sequence-count metrics, reporting raw values and deltas, with no timing or energy reinterpretation.

Even a PASS of the *declared pair comparison* does **not** prove full input parity, treatment-only manipulation, matching output semantics, or causal feedback overhead unless native input manifests and treatment control are independently audited. Such a comparison is exploratory.

## Local installation / gate

```bash
cd ~/workspace/spk-backvalidation-v0
tar -tzf ~/Scaricati/spk-bv-v0o-live-runs-comparison-research.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0o-live-runs-comparison-research.tar.gz
bash search/spk_bv_v0o_research_gate.sh
bash search/spk_bv_v0o_native_gate.sh /tmp/spk-bv-v0o-native
bash search/spk_bv_credit_v0a_full_regression.sh
```

The native gate emits three new files: `/tmp/spk-bv-v0o-native-13.json`, `-811.json`, `-inventory.json`. Files must **not already exist**. Share the **inventory** and compact gate output rather than full native capture; the latter includes all fixture data.

## Optional config after examining the actual inventory

This example is *synthetic* and **must not be used** on the native v0e capture until the true paths are verified:

```json
{
  "baseline": ["disabled"],
  "enabled": ["enabled"],
  "workload_witnesses": [{"name":"input-object", "baseline_path":["inputs"], "enabled_path":["inputs"]}],
  "metrics": {
    "forward_end_tick": {
      "baseline":{"path":["last_tick"],"op":"int"},
      "enabled":{"path":["last_tick"],"op":"int"}
    },
    "feedback_grants": {
      "baseline":{"path":["feedback_grants"],"op":"count"},
      "enabled":{"path":["feedback_grants"],"op":"count"}
    }
  }
}
```

Comparison:

```bash
python -m search.spk_bv_v0o_analyze \
 --capture /tmp/spk-bv-v0o-native-13.json \
 --expected-fixture-sha <CAPTURED_SHA256> \
 --compare-config /tmp/spk-bv-v0o-verified-selector.json \
 --out /tmp/spk-bv-v0o-paired-observation.json
```

No generator invents treatment, workload or measurement semantics. Frozen Architecture v1, Compiler, Core and Network are unchanged. No causal credit, model updating, compression, or hardware profile recommendation.
