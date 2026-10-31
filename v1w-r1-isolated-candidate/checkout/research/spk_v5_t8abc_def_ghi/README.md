# SPK V5 T8ABC+DEF+GHI Cumulative Candidate Runtime Contract

One additive gate, no changes to frozen SPK source. This checkpoint:

- T8ABC: constructs an explicit semantic-v1 **candidate packet** using A 21/22 + original structural BV A→B→C, with exact source/decision/version binding. This packet exists only in the research adapter.
- T8DEF: makes separate P-v1 candidate admission decision; no native grant can be produced in this implementation. Only research host-managed P can change.
- T8GHI: compares 96 baseline / 96 adaptive episodes, plus 24 dropped-route episodes, recovery and forged-source witness. 48 vs 88 parity with validated T7 report; deterministic two-process report comparison.

See `docs/spk-bv-semantic-and-p-admission-v1-candidate.md` for the contract delta and future native acceptance gates.

## Run on fwork

```
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T8ABC_DEF_GHI_Candidate_Runtime_Contracts_Cumulative_20261022.tar.gz
bash search/spk_v5_t8abc_def_ghi_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t8abc-def-ghi-cumulative.json
```

Native semantic BV, native P state, native learning, sensor authenticity and host-resistance all remain **UNPROVEN**. Privileged-host coherent forgery remains an explicit expected counterexample.
