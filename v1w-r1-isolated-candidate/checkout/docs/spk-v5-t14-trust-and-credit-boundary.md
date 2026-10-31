# SPK V5 T14 · Source custody, semantic claims and authority separation

### Meaning of the signed receipt

`T14 A-EXTERNAL` is a protocol issuer name. It is NOT a demonstrated independently owned sensor identity. The release harness signs host-derived A judgments with a **laboratory key created in a temporary directory**. The signature proves that the same lab private key produced the bytes accepted by the verifier; it proves nothing about the truth of the host-authored goal or the causal correctness of A's verdict.

The signature covers: schema, issuer, episode, cue, choice, host goal, P version, A PE event ID, A PE event digest, A result digest, verdict and nonce equal to A event digest. The verifier reconstructs those fields from its immutable-to-it runtime event and rejects mismatches.

### Authorization order

1. Frozen PE `_compute_local` computes A's outputs in a reference `PE_A` event.
2. An **outside-runtime** signer may submit an Ed25519 receipt covering those exact bytes.
3. C receives `SEM_B_C`; version/deadline and new-runtime P resource quotas are checked.
4. The source guard cryptographically verifies the receipt BEFORE invoking T13's ORIGINAL A1d memory chain.
5. T13 then executes original A1d admission, execution, projection, authorization and memory service, bound by choice and goal.
6. All of the above are prerequisites for the single new-runtime P transaction. A SQL trigger persists the signed grant linkage or raises an abort. Failure leaves the C event queued for recovery.

No original SPK BV P-learning grant exists in this chain. Original execution access is not an original policy update authorization.

### Explicit holes

- Host can still create an arbitrary goal and a plausible A trace.
- Host can invoke a test signer because it owns the **laboratory** key; key isolation in the protocol has not created independent physical trust.
- Source signatures are on per-episode local tick events, not global physical time.
- Host can rewrite program, change trust root and re-sign SQLite; cryptography alone does not stop a privileged host.
- Only positive laboratory evidence and negative denials have been established, not held-out generalization, native causal credit or genuine sensor provenance.

### Criteria for future release

An independently controlled A signer, non-host-authored/attested goals, authenticated message ingress, externally anchored ledger, truly runtime-owned P learning permission, clock/resource model and blinded held-out evaluation must be demonstrated before any native claim.
