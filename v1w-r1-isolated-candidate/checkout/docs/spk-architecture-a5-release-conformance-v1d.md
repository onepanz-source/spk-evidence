# SPK Architecture v1 · A5d Bounded Release Conformance

**Status: RELEASE CANDIDATE. An independent-clone gate is mandatory before tagging.**

## Release scope

This final Architecture v1 milestone does not modify Core, Network, Compiler,
Simulator v0 or previous Architecture v1 implementations. It verifies that
19 certified predecessor milestones (A1a–A5c, 115 tracked files) and six A5d
files form a committed, reproducible 121-file source set on branch
`spk-architecture-v1`, descending from annotated baseline tag
`spk-simulator-bounded-reference-v0` (a76ebaae49373a4c6b66f94465d78dbf1cf19f80).

The proposed final annotated tag is `spk-architecture-bounded-reference-v1`.
The gate never creates or moves this tag automatically.

## Authoritative two-stage gate

1. With A5c committed and A5d unpacked, run
   `python -m search.spk_arch_a5d_release_evidence_v1d --preflight`.
   Verify only the six A5d paths are new, then commit them as a release candidate.
2. Run `bash search/spk_arch_a5d_final_gate_v1d.sh` from the **clean committed**
   release candidate. The gate creates two independent local Git clones (not
   shared worktrees); neither contains uncommitted project files.
3. In the first clone run the A5d release tests, real independent Compiler
   witness tests, protected A5a/A5b/A5c/A4d regressions and the **entire**
   repository test suite.
4. In both clones generate identical canonical release evidence. Verify each
   receipt from the opposite clone, replaying newly computed witnesses against
   the real frozen Compiler, A3d execution and A4d custody.
5. Validate exact source hashes, parent tag/ancestry, clean checkouts,
   existence of historical integration certificates, and absence of a release
   tag. Only a fully green gate makes this exact commit tag-eligible.

## Fresh release witnesses

Stratified selection: six program profiles × six graph families, with
36 selected source cases across all six input families, each under three PE
placements. For each of the 108 source/placement pairs, A5d freshly computes
one independent vertical Compiler/host/custody witness, one PE-renaming and
resource metamorphic witness, and one bounded adverse authority/fault witness.
This is a **new stratified replay**, not full regeneration of all 19 old phase
certifications. Historical SHA-256 values are recorded and source-audited as
metadata, never represented as new phase evidence.

## Freeze discipline and limitations

- Original v0 components and the 19 previous Architecture cycles remain unchanged.
- Tag only the exact clean commit that passed the isolated-clone gate.
- Persist full stdout and the canonical JSON release receipt outside Git if
  independent audit material is needed. Digest alone does not archive the file.
- Frozen reference semantics are bounded to the finite software corpus,
  deterministic global scheduling, controller trust and logical PE/memory/link
  models. This is not evidence of physical hardware, NoC fidelity, asynchronous
  fault recovery, hostile-process isolation, live checkpoint continuation or
  automatic learning.
- Release admission does not make an architecture physically complete.
