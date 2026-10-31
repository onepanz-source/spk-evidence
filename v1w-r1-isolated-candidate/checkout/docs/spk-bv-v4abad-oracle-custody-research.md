# SPK Back Validation v4ab–v4ad — oracle provenance and label poisoning

**Research-only, no native or derived algorithm adoption.** This checkpoint
depends on the exact signed v3tuv native source and v4y–v4aa task-objective
observation. Frozen Architecture v1, Core, Compiler and native v0e are intact.

## Research question

Can positive actor-local feedback, apparently valid program improvement and
two agreeing task-label providers jointly justify learning? **Not yet.**
It is possible for two signers to attest exactly the same *false label*.
Cryptographic source integrity is distinct from semantic correctness.

The report uses two roles (`task_specifier`, `independent_reviewer`) with
canonical, domain-separated HMAC-SHA256 **test-fixture** attestations over:
scope, parent digest, source key, epoch, sequence, nonce, creation/expiry and
declared task labels. The verifier accepts the keyring as an external argument,
but the *reproducible fixture keys are deliberately published in the bundle*.
They are **not secret, not suitable for deployment, and do not authenticate
real people or external organizations**. The anti-replay ledger only lives
within one bounded evaluation, and is explicitly not durable.

## 12 typed scenarios for each of 18 native source cases

| Variant | Meaning | Research outcome |
| --- | --- | --- |
| `valid_quorum` | Two distinct matching test-role MACs, correct task canary | Test witness accepted, no production trust |
| `missing_reviewer` | Only one role | Reject quorum |
| `wrong_reviewer_mac` | Reused wrong-role MAC | Reject attestation |
| `tampered_after_sign` | Labels changed after MAC generation | Reject attestation |
| `expired` | Freshness boundary crossed | Reject expiry |
| `wrong_scope` | Authenticated for unrelated task | Reject scope |
| `replay` | Same nonce after a first accepted witness | Reject replay |
| `stale_sequence` | Source sequence below accepted high watermark | Reject stale sequence |
| `dually_signed_poison` | Both roles MAC inverted labels | Reject semantic canary conflict |
| `absent_canary` | No prior agreed task canary | Reject absent reference |
| `wrong_predecessor` | Parent digest does not match signed source | Reject lineage |
| `single_key_roots` | Both roles mapped to the same test key | Reject role root separation |

The semantic canary is **the already precommitted v4y–v4aa experimental task**
(channel 0 → one terminal output; channel 1 → none). It catches a change
relative to that precommitment; it is **not independently verified real-world
truth**. In particular, if the initial labels are wrong, this mechanism can
preserve a wrong task perfectly. Similarly, authenticating signers alone
cannot make their labels true.

## Measured scope

- 18 original signed native reexecutions checked against the pinned native
  SHA witness and unchanged `live_dual_scheduler_v0e`.
- 216 provenance cases, 18 acceptable *test-only* attestations, 18 full-MAC
  co-signed label-poisoning cases rejected.
- Independent deterministic witness rebuilding plus adversarial unit tests.
- No physical device, durable replay ledger, production key provision,
  external source identity validation, generalization, actual learning or
  adoption. No source-dependent spike weights.

## Next falsifiable step

Specify and test an *external* verifying authority/key-provisioning and
genuinely independent task truth. Until then, a test-role quorum is only
cryptographic mechanism coverage and may not authorize algorithm promotion.
