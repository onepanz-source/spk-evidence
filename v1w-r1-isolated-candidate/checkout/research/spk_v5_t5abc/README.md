# SPK V5 T5ABC · PE-output-bound BV semantic transit (research fork)

**Scope:** additive copy of frozen `spk_backvalidation_v0/live_dual_scheduler_v0e.py` retaining the original imports and resource-arbitration implementation. The copied code differs only at the sites exposed in `FORK_DIFF.patch`; its original schema/keys remain byte-identical when the additional `experimental_semantic_port` key is discarded. `spk_architecture_v1/pe_execution_v1b.py` is **not** modified.

- In a **real single BV-v0e fork scheduler execution**, the PE's original `_compute_local` produces output channel 11 (sign +1) or 12 (sign -1) within the C batch.
- If and only if C also emits fixed terminal channel 30 in that same batch, the **fork scheduler** attaches a semantic payload, bound to its C batch/tick/causal parents, to the corresponding assessment.
- The original live reverse feedback scheduler carries this payload C→B→A with existing link grants, resource admission, timing and packet IDs. The B continuation inherits the payload from the **received packet**, not the final results JSON.
- Receiver A can read the sign from that in-flight packet; the auditor checks against immutable archived output hashes for all 180 source cases. The 72 potential sign receivers are **not** 72 authorized credits; only 24 cases pass the old application guard, still research-only.
- Test the synthetic route against the frozen reference using two independent scheduler implementations. The full 180-case fork replay is performed **twice** by the gate on the user's original checkout. No original BV-v0e scheduler calls are needed in T5ABC; archived T4GHI/T4ZABC source hashes are the locked oracle for original-result parity.

## Non-promotion, intentionally preserved

This does **not** prove native neuronal authorship, authenticity, trusted sensor, independent reward, true actor credit, or learning. The host controls the fork and therefore can construct/modify execution and counterfeit C payloads. The identifier `C-batch-*` is deterministic internal metadata, **not a cryptographic authenticator**. Receiver A in this test is also a simulated node within the copied Python scheduler, not a separate independently secured PE. This is stronger causal integration than the host's after-the-fact adapter, but does not cross the trust boundary exposed by T4TUV.

## Execute

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T5ABC_In_Scheduler_Semantic_Transit_Research_Milestone_20261022.tar.gz
bash search/spk_v5_t5abc_semantic_transit_gate.sh \
 ~/workspace/spk-evidence/spk-v5-t5abc-semantic-transit.json
```

The gate refuses existing output paths and compares two independent 180-case fork processes byte-for-byte. It validates source SHA pins; it does not rewrite frozen files. Do not treat its successful return as native Back Validation or neural learning.
