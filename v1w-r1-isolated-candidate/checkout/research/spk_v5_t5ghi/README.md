# SPK V5 T5GHI | Receiver-owned challenge + PE-bound freshness (research)

**No native C authentication or BV/learning promotion.** This increment follows T5DEF PASS, whose exact report SHA-256 is pinned to `e5e966c7692a839cee0cc5575f031bfde2c7d02e5b3ca29ed41f3d97f0674e55`.

T5GHI is additive. The SHA-pinned original BV-v0e scheduler, frozen PE v1b, T5ABC and T5DEF forks, and their original reports are left untouched. A *copied* T5DEF fork calls a separate PE-scope challenge-aware wrapper synchronously with each `_compute_local` call. The PE wrapper attaches `challenge_digest` to the C assessment. The fork forwards the field via the **existing causal BV path C → B → A**. Removing this field must reproduce **exactly** the original 180 T5DEF experimental-port hashes and frozen-source outputs.

A separate Python process models receiver A. For each case A generates an unpredictable one-use 256-bit challenge with `secrets.token_hex(32)`; it verifies the echoed challenge commitment, message continuity, and single-use consumption. No raw nonce or nonce-dependent digest is placed in the deterministic final report. A rejects duplicate/replayed, altered, and wrongly attributed messages. Unused challenges are explicitly expired. Two independent run reports must be byte-identical while actual private challenges differ.

**Mandatory negative witness:** the privileged Python host intercepts old C PE outputs from the same case, suppresses new C computation, attaches a *new valid challenge digest*, and still causes A to accept the fabricated fresh message. This is possible because the challenge is disclosed to the host, which can impersonate the copied PE wrapper. SHA-256 challenge binding is **not** a signature, cryptographic C identity, verified sensing, trust anchor, or attestation. The A process is OS-process-separated but not isolated from a privileged host. All 72 A receives remain research-only; the prior 24 guard candidates are not promoted to native credit.

## Run on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T5GHI_Receiver_Owned_Freshness_Milestone_20261022.tar.gz
bash search/spk_v5_t5ghi_receiver_freshness_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t5ghi-receiver-freshness.json
```

The gate runs inherited regressions, exact custody SHA comparisons, independent 180-case fork runs, separate A processes, adversarial tests and deterministic report sealing. Failures stop without writing the destination report. User evidence is required for the original full checkout, which is not reproduced by local synthetic tests.
