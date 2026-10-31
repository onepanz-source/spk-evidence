# SPK Back Validation v4ak–v4am — valid-fork and rollback witnesses

**RESEARCH ONLY. NO TRUSTED EXTERNAL AUTHORITY DEPLOYED.** The native v0e,
Architecture v1, Core and Compiler remain frozen. No candidate adoption,
weight update or learning occurs.

## Central falsifiable hypothesis

A SQLite record can pass its own integrity checks and still represent an
unauthorized *alternate history*. If an independent authority had already
retained the genuine history's digest, that fork would be detectable.

The experiment creates two *different*, locally valid SQLite journals with
properly signed public-fixture reviews and a common predecessor. Both pass
normal reopening/chain/replay checks. They have different heads. Witness A
matches A and rejects B. Because the lab HMAC key is openly embedded in the
research code, B can sign a new capsule; this, too, passes when there is **no
independently retained capsule digest**. It fails when verifier input carries
the previously retained SHA-256 digest of capsule A. A replayed prior valid
SQLite database also fails against the later recorded head.

This is a constructive counterexample to the false inference
`self-consistent log -> authoritative log`.

## Mechanism and signed lineage

1. Read the exact byte-pinned v4ah–v4aj report SHA-256
   `8fd397a7b3b1cf693f1c5e3be3e78021f504609a0b2695b2bbe67e07d65f8674`
   and its source-bound SQLite witness (72 entries, 144 unique nonces).
2. Reopen the existing SQLite escrow and verify every journal record, signed
   review, hash-chain predecessor, replay index, source clock and head.
3. Produce a canonical, HMAC-SHA256 lab witness capsule containing the pinned
   report digest, SQLite parent, head, record/nonce totals, issuer role,
   sequence and prior witness reference. The signer key is supplied to the
   module; the **test key is public, not a real identity credential**.
4. Save the capsule in a new exclusive/private file and independently pin the
   capsule's own byte digest. The corresponding JSON audit is also create-only.
   A verifier can be run later with that previously retained digest and the
   current database without trusting SQLite's own stored `head` value.
5. Construct valid alternate branches and valid rollback histories; verify
   the precise cases in which an external pin rejects them.

For the exact reference fixture, the capsule's SHA-256 is:

`1654e88d8c7dd8d88aac656f58ce0838e10f25d4f1b4b956a1af876a3ad593a0`

The reference capsule in `docs/` is a *reproducibility fixture*, **not** an
actual independent authority. In a future system, the trusted head or digest
must be published with authenticated custody controlled separately from the
actor controlling the SQLite data and code. Its rotation, recovery,
reconciliation and publication ordering remain open design questions.

## Gate and negative evidence

- 29 new adversarial tests: source SHA pinning, create-only files, role/serial,
  canonical domain-separated witness bytes, wrong-key and wrong-MAC vetoes,
  valid divergent forks, valid prior-history rollback, same-key re-signing,
  distinct retained capsule digest, stale head after a legitimate append,
  tampered SQLite, symlink and unsafe-output rejection.
- 170 inherited tests through v4ah–v4aj: **199 tests passed**, plus frozen
  native v0e forward/BV smoke, reproducible pinned witness and audit bytes.
- No additional broad native training or task inference is claimed here. The
  18 original executions, 72 counterfactual probes and 198 escrow review
  attempts belong to the pinned predecessor and are regression-checked in
  the inherited gate; the new counterexample executes a narrow native probe.
- Both experimental branches are valid SQLite histories. The external digest
  distinguishes the source branch; it does not establish real-world task
  meaning or the correctness of its labels.

## Critical exclusions

1. All new storage and the example witness run on **one host**, and the lab
   HMAC key is published in fixture code. No adversarial separation of
   ownership exists. Anyone able to replace the database *and* the outside
   digest can substitute a coherent history; anyone reading the test key can
   forge the role MAC. This package only shows what a genuinely independent
   future custodian would be required to enforce.
2. The signer is a test role, not a verified person, organization, TPM or HSM.
   HMAC does not establish identity without an authentic protected key.
3. The capsule and JSON audit are separate create-only files, not a shared
   atomic transaction. If the report write fails after the capsule is saved,
   the capsule may remain. No remote monotonic counter, Byzantine quorum,
   secure clock, key provisioning or rotation has been implemented.
4. Both endpoint and emission observations derive from the same native run;
   agreement cannot determine external task truth. Neither this checkpoint
   nor its predecessors justify self-modifying a production neuron's program.

**Next gate:** an externally owned anchor with a provisioned trust root,
plus independently verified task evidence/holdout. Neither may be faked
by placing another fixture key in the same codebase.
