# SPK V5 T5JKL: Receiver independence and provenance cross-plane audit

**Research only. Do not promote native BV, authentication or learning.** This additive milestone follows the verified T5GHI SHA `f4296cdc55313967fcaab3f34810867128b2550ad85978e4a3f9196eb8028a86`.

## Why this checkpoint matters

T5GHI proves fresh *receipt* of C-derived signs in a Python A receiver process. It does **not** prove an **independent A judgment** on C's choice. A repeatable, non-circular A judgment requires independent observations / goals and provenance not derived from C's own emitted sign. The existing host-controlled software provides no independently authenticated A sensing. Neither a renamed field, a random nonce, a digest, a claimed A identity nor a separately running Python process changes that fact.

This gate cross-checks 180 SHA-pinned cases against the **original T4GHI** source observations. The experimental BV-feedback receipt plane and source `forward.emissions` plane are intentionally distinct. Both must be reported, never silently equated:

- **108** cases have no C sign received by A.
- **24** have fresh receipt with no source failure, so they are only *research guard candidates*, never native credits.
- **24** have fresh receipt with `no_forward`, preserving a coherent T4GHI C→B→A forward emission candidate despite this failure flag.
- **24** have fresh receipt with `no_reverse`, but T4GHI reported no coherent C→B→A *forward.emissions* sign candidate. This is not automatic proof of corruption. It demonstrates distinct evidence planes that must be reconciled before stronger claims.

No receiver-generated independent goals, independently authenticated observations, native credits or learning occur in this gate. The 24 `guard_only` cases do **not** mean independently accepted results. Research classifications use SHA-pinned source failure metadata that remains visible and potentially forgeable by a privileged host.

## Provenance contract

`independence_contract_v0.py` treats a C/B-delivered sign as a **receipt**, not an A judgment. Structurally A-labeled observations can be modeled and tested, but neither they nor self-declared attestations can be promoted to authenticated judgments in this host-controlled runtime. An actual independent judgment needs an external provenance trust anchor and A-local observations/goals; future work can bind an A assessment to C emission causality and return it through B to C with appropriate custody.

## Run

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T5JKL_Receiver_Independence_Provenance_Audit_Milestone_20261022.tar.gz
bash search/spk_v5_t5jkl_receiver_independence_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t5jkl-receiver-independence.json
```

The gate performs two **offline** report audits in independent processes, each checking the 12 pinned original source files. Unlike previous milestones, **no new scheduler or PE executions** are performed because the point is to audit what was actually proved by T5GHI. Two reports must be byte-identical, the complete inherited regressions pass, and no target output is overwritten.
