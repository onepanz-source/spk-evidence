# SPK 24x: Bounded Simulator Conformance Release Candidate v0

**Status: INTEGRATION PASS (2026-10-16, bounded reference release candidate; no tag).**

## 1. Purpose and baseline

This is a **bounded reference-profile freeze readiness audit**, not a universal
simulator certification. Its accepted predecessor must be the committed
24w structural-metamorphic checkpoint, with exact commit subject:
`checkpoint: SPK structural metamorphic conformance v0`.

The audit makes no changes to Core v0, Network v0, Compiler v0, Architecture,
Simulator, or previous 24m–24w adapters. It adds no runtime evaluator,
scheduler, persistence layer or observer implementation.

## 2. Existing conformance arguments

The three cross-layer acceptance families are mandatory, with original fwork
SHA-256 evidence pinned by the audit:

| Family | Bounded acceptance | Accepted evidence digest |
| --- | --- | --- |
| 24u | 216 three-neuron compiled programs; 408 versioned-host runs | `e2ce01b440d019c0b33316c67858102310d889c92d71faa04a5e873540119099` |
| 24v | 1,512 rejected pre-executor admissions; observer callback/diagnostic injection | `a5f23f7cf402bbc8289cb04d56ec0d66784bb4b713799da94b69c85ee0b4da3e` |
| 24w | 648 compiled graph-isomorphism transformations across 216 sources | `1e620306cad44da0f3b1d289a68fab751dc759e1ae243c97ff352354f2ca9e98` |

The plan also pins the unmodified 24o corpus
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`
and the 24w transformation plan
`91dda6289f29b38a12a7672c36169003c3eddc27ff3d4b8abfd923d9f0565d0f`.

Accepted failure results from 24q/r/s/t remain part of the regression gate:
separate-budget agreement, dual-budget observational differences, causal
isolation, and versioned diagnostic equivalence. Ambiguous ties are NOT
promoted into a normative error-priority rule.

## 3. Freeze and provenance contract

The audit requires the accepted 24w baseline as HEAD before commit or its
**direct child** after commit. This child must have subject
`checkpoint: SPK bounded simulator release candidate v0` and add exactly
the four 24x files, with no other changes. Both states attest the same 24w
commit, so the pre-commit record remains verifiable after the 24x commit.
No later unrelated commit is accepted.

The audit rejects an uncommitted 24w baseline, dirty tracked files, staged
files, unexpected untracked files, missing accepted sources, missing annotated
freeze tags, or changes to `spk_core` / `spk_network` since
`spk-core-network-v0` and `spk_compiler` since `spk-compiler-v0`.

Only the three deliberately unrelated experimental untracked files and the
four new 24x candidate files may be present as untracked sources. The audit
does not stage, move, delete, or commit any of these files. It computes a
canonical JSON record with full baseline commit ID, annotated freeze tag target
commit IDs, tracked acceptance-source file digests, evidence-family pins,
corpus and metamorphic-plan identities, and explicit exclusions.

Independent Python processes must produce byte-identical records; validation
requires canonical encoding, unique keys, valid checksum and complete
recomputation against the live checkout. SHA-256 is *not* a digital signature,
external attestation, or durable log.

## 4. Explicitly outside the release profile

The candidate **does not certify**:

- arbitrary graphs or cyclic-network equivalence;
- arbitrary observer sandboxing, recovery or callback side-effect isolation;
- durable exactly-once execution, rollback or authenticated receipts;
- PE contention invariance or distributed scheduling/authority;
- learning, general liveness or back-validation semantics;
- universal equivalence of SPK algebra/Core/Compiler implementations.

The profile is a tested software reference for future simulated architecture,
not a completed neuromorphic processor, device mapping, or production runtime.

## 5. Single acceptance gate

1. Independent release-policy and negative attestation tests.
2. Frozen Compiler → manifest → host → observer → oracle conformance:
   24u, 24v, and 24w test modules.
3. Two independent-process release records, byte equality, canonical replay;
   regenerate 24u, 24v and 24w evidence against the real frozen chain and
   compare each new SHA-256 with the previously certified digest.
4. Budget/diagnostic/observer regression: 24q, 24r, 24s, 24t, 24v.
5. Complete repository regression.
6. Freeze-tag checks, tracked/staging/untracked hygiene and candidate file
   whitespace validation.

Command: `bash search/spk_24x_final_gate_v0.sh`.

On PASS, **do not automatically tag**. First review the bounded-domain
acceptance evidence and commit the four 24x files with the required subject. A separate manual,
annotated release tag can be considered only once its name and precise frozen
scope are approved. This avoids conflating a release *candidate* with release
closure.

## 6. Engineering roadmap at candidate creation

Last accepted checkpoint 24v: S1=100%, S2=100%, S3=90%, S4=85%, S5=90%.
Following successful 24w, propose S5=95% because of proven compiled
structural metamorphism, with other phases unchanged:
S1=100%, S2=100%, S3=90%, S4=85%, S5=95%; equally weighted 94%.

These are qualitative engineering acceptance scores. A gate PASS for 24x
consolidates provenance and scope; **it does not alone promote other phases**
or prove any of the exclusions in section 4.

## 7. Accepted release-candidate gate

Baseline:
54cba1ea95a72997c466a865965b0e98185b28db

- Original release-policy tests: 12 PASS.
- Frozen cross-layer integration: 29 PASS.
- Budget/diagnostic regressions: 63 PASS.
- Original complete regression: 2989 PASS.
- Rebuilt evidence families 24u/24v/24w: PASS.
- Frozen tags, provenance and patch hygiene: PASS.

Canonical precommit attestation SHA256:
7fe3e8b08561ccc30509083641d344d70823a427f6fa38cd83157abf436f51e7

Postcommit replay is required before any release tag.

This is a bounded software reference-profile acceptance,
not universal simulator or neuromorphic architecture completion.
