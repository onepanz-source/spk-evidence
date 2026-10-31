# SPK V5 T4NOP | Receiver Semantic Boundary (research only)

## Scope

Three coordinated research gates, with no mutation of Core, Network, Compiler,
Architecture v1 or the frozen BV-v0e scheduler:

* **N**, source/report SHA pins, including the T4JKLM control-flag hotfix report.
* **O**, a fresh **single-source** `execute_live_v0e` call for each of 180 recipes,
  compared byte-exactly against T4JKLM, T4GHI and T4DEF source digests;
  inspect the *receiver delivery surface*, not just source-side emissions.
* **P**, prove absence of an explicit semantic sign binding and trusted native
  attestation in the observed receiver payload; adversarially reject fabricated
  sign/authenticator/parent fields. **No semantic credit granted**.

The existing `forward.emissions` channels C=11/12, B/A=13/14 and the
`feedback.deliveries` transport records are DIFFERENT evidence types.
The latter expose `packet_id`, `assessment_id`, `evidence_ids`, sender,
receiver, tick and `independent_receiver`; in the measured profile they do
**not** encode authenticated `semantic_sign`, `C_emission_id`,
`causal_parent_id`, `source_identity` and `authenticator`. No posthoc bridge
may manufacture C-authored custody by joining these records.

Opposite signs can have the same *field-and-route schema*. That is not proof
that the complete records, packet IDs or runtime state are byte-indistinguishable.
An opaque field might correlate with the sign; correlation does not establish
receiver-readable semantic contract or authenticated origin.

## What comes after this gate

The next meaningful milestone would be a **separate experimental receiver-owned
semantic transaction port**: C must author sign and a causal event identity;
B must preserve those identities in transit; A must consume a verified
origin-bound receipt in the same causal execution. An independent trusted
verifier/source of authority is required; a host-constructed signature, SHA
or replay comparison is insufficient. Keep this new port separated from
frozen BV-v0e until it has its own negative and differential release gates.

This artifact does not add such a port or native credit, and never trains or
changes a neuronal policy. There is no independent authenticated sensor,
independent goal truth, or native RL evidence.

## Use on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4NOP_Receiver_Boundary_Milestone_20261022.tar.gz
bash search/spk_v5_t4nop_receiver_boundary_gate.sh /tmp/spk-v5-t4nop-receiver-boundary.json
```

The gate refuses to overwrite a report. It checks all dependent manifests and
source SHA pins and reruns the source 180 times in one isolated Python process.
To reduce accidental evidence loss, transfer the resulting JSON to the
persistent `~/workspace/spk-evidence` directory after the gate has passed.
