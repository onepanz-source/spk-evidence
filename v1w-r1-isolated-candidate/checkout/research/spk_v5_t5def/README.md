# SPK V5 T5DEF | PE-scope semantic issuer, research only

This additive experiment splits **compute-and-issue** from the scheduler:

- `pe_semantic_issuer_v0.compute_and_issue` calls the **frozen** `_compute_local` once and authors a `PEEmission` object from that exact output, before the copied scheduler gets it.
- `live_pe_issuer_fork_v0` is a copied **T5ABC** scheduler fork. It receives the PE-scope descriptor, transports the same semantic payload through the existing BV arbitration and preserves frozen scheduler outputs.
- Gate checks byte-exact T5ABC **original result and experimental port** SHA per each of 180 source cases. Original frozen PE and BV files must not change. Two independent runs compare byte-for-byte.
- A mandatory host-rebinding counterexample bypasses C PE compute using cached returns for case 0. The receiver and full scheduler report remain identical. **Thus PE scope is not an independently authenticated neuronal origin.**

## Strict non-promotion

No trusted execution environment, PE-owned cryptographic key, attested sensor, independent reward/goal, neuronal C-authored receipt, native learning or authenticated BV is claimed. Python code and import bindings are host-controlled.

## Install and gate (fwork)

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T5DEF_PE_Scope_Issuer_Research_Milestone_20261022.tar.gz
bash search/spk_v5_t5def_pe_scope_issuer_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t5def-pe-scope-issuer.json
```

The package contains only new `research/spk_v5_t5def/` and `search/` paths. The historical T5ABC PASS report is SHA-pinned within this package, not regenerated or overwritten.
