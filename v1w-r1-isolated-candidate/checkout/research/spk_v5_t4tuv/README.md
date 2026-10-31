# SPK V5 T4TUV - Host authority counterexample (research only)

**Aim:** test whether the process-separated T4QRS A-owned research ledger is
sufficient evidence that neuron C authored the semantic feedback. It is not.

Three cumulative gates:

- **T4T:** Reconstruct all 24 adapter-origin packets from immutable archived
  T4GHI/T4NOP results, with **zero** new BV-v0e executions. Re-enroll commitments
  using the existing **host-authorized** T4QRS precommit protocol. Run the
  original, unmodified B relay, A receiver and QRS auditor. The resulting
  T4QRS report has the same exact SHA-256 as the authentic 180-source-run
  T4QRS output, even though this new run has performed **zero source calls**.
  This falsifies the inference that its A ledger or QRS report authenticates
  neuron C. **The original 360 scheduler invocations remain real and valid.**
- **T4U:** A strict native-receipt check has *no affirmative branch* until an
  actual runtime-execution-owned origin verifier exists. Adding invented fields,
  strings saying `signed`, SHA hashes or host tokens is never sufficient.
- **T4V:** Recheck source SHA custody, detect the precise `execute_live_v0e`
  and posthoc adapter callsites via AST, run two independent offline rounds,
  compare deterministic sealed outputs and enforce strict nonpromotion.

Nothing in this package modifies frozen Core, Network, Compiler,
Architecture v1, or BV-v0e scheduler. This is a **constructive adversarial
experiment**, not an emulation of native C-authored messages. It uses archived
source evidence only, and neither sensor authentication nor independent goal
truth nor online learning exists here.

Install into `~/workspace/spk-backvalidation-v0` with:

```sh
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4TUV_Host_Authority_Counterexample_Milestone_20261022.tar.gz
bash search/spk_v5_t4tuv_host_authority_counterexample_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t4tuv-host-authority-counterexample.json
```

The goal of the **next implementation branch** is an experimental, nonfrozen
runtime in which C's execution step originates a signed/owned semantic event,
B forwards it with causal ancestry intact, and A verifies the runtime-granted
emission authority **before** committing receiver-owned state. Neither the
static program identity nor the host's commissioning key suffices as proof.
