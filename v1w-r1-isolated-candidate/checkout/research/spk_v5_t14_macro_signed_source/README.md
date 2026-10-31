# SPK V5 · T14 Macro Signed A Source Custody Boundary

## Scope

One additive research-only milestone, **not** an implementation of native BV learning:

1. Canonical A event provenance includes A event ID/hash, original PE-derived A output digest, C choice, host-authored goal, cue, episode, and P version.
2. Detached Ed25519 signature verification using OpenSSL, with a public-key fingerprint pinned on creation and checked after reopen.
3. Source receipt acquisition between A computation and C feedback receipt; same-tick P source linkage persisted atomically with reference grant.
4. Missing/invalid signature denies the reference provider **before** running the original A1d access chain. The B->C event stays queued and P is untouched; a later valid receipt may recover it.
5. T13 **genuine original A1d** memory access remains a prerequisite to each signed reference P update on fwork. No original code changed.
6. Negative probes and crash-reopen provenance preservation.
7. Full inherited regression, source pins, and two byte-identical strict reports.

## Security claim boundaries

**The test signer is not A.** The release gate generates an ephemeral laboratory Ed25519 key within an isolated temporary directory. It only tests signature verification and key pinning. Neither real-world observations nor A's identity are independently authenticated. The runtime host still authors the goals and can alter the program or data. The private key is not included in the archive, and it is not supplied to `SignedSourceGatedV1`.

Signing a goal produced by the host is **not** proof that the goal is correct. Even the signed scenario is a laboratory fixture, not native learning.

A privileged host can replace both runtime and the pinned trust root, and can rewrite/reseal the SQLite database. Real provenance will require a signer independently controlled by the producing A process, secure key enrollment, verified goal authority, and immutable or separately anchored recipient logs.

## Key outcomes

- Lab signer with existing original A1d executor on fwork: 96 episodes, 88 successful; eight reference P grants each accompanied by signed lab receipt and original execution-access witnesses.
- Unsigned negative verdict: transaction abort, 0 P grants, queued C receipt retained; after signature + reopen exactly one reference grant.
- Program-disabled baseline remains 48/96 as proven by T13 history, but the unsigned **active-learning** scenario fails closed and is NOT represented as a 48/96 completion. It halts at the first negative attempt until the receipt arrives.
- No authentic A sensor source; zero original SPK BV learning and zero original native P learning grants.

Requires OpenSSL CLI with Ed25519 support and the complete authentic frozen SPK source checkout on fwork. No extra Python dependencies beyond those in previous checkpoints.
