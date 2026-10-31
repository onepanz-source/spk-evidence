# SPK Architecture A5a: vertical conformance and committed evidence inventory v1a

**Status: INTEGRATION PASS (2026-10-16, stratified bounded logical domain).**

## Objectives

A5a is the first architectural conformance gate **across** A1–A4, not another
PE or mode feature. It creates a Git-pinned inventory of all 16 predecessor
cycles, requires the v0 simulator annotated tag to point at the previously
frozen commit, and checks every one of the 97 predecessor files is tracked,
committed, unmodified, and referenced by a corresponding certified document.
The 16 recorded gate evidence SHA-256s are historical *reported outcomes*, not
new evidence reruns. A5a does not silently turn historical log strings into
cryptographic attestation by an independent authority.

For direct independent conformance, A5a selects one input family per pair of
six source program profiles and six network graph families. Every input family
is represented, for 36 distinct cases x 3 PE placements = 108 witnesses.
The source corpus itself is pinned to its frozen 216-case SHA-256. Each witness:

1. Runs the real frozen Compiler/host witness through A3d link evaluation.
2. Separately runs full A4b authority, A4c changed-program verification and
   approval, A4d P/S/E/O capture, full replay recovery, stale-state rejection,
   and explicitly cold activation on the changed candidate.
3. Invokes the A3d engine directly, outside its A4a wrapper, for source and
   candidate; compares entire canonical results to the A4d receipts.
4. Compares A3d causal link output and manifest to the distinct A4d witness,
   checks no lost/duplicated remote events, no in-flight/outbox remainder,
   and distinct source/candidate manifests.

The attested evidence binds the **actual Git HEAD** and the SHA-256 of each
previously committed source/documentation/gate/test file, in addition to
108 cross-layer semantic witness rows. Independent processes regenerate it.

## Boundary and limitations

The cross-layer sample is stratified but **not exhaustive** of the full
216 x 3 corpus. Existing A1–A4 acceptance gates and the full repository
regression cover their own finite domains. The historical SHA-256 receipts
must not be described as physically signed or as independently rerun here.

Git commits and hashes are local provenance, not protection against a hostile
machine owner. A5a assumes a trusted software reference, source-controlled
predecessors and deterministic execution. No physical NoC, actual memory RAM
transactions, crash-atomic durable state, hot migration, automatic learning,
receiver ingress protocol or distributed clock is certified.

## Gate

`bash search/spk_arch_a5a_final_gate_v1a.sh`

Six sections: pure inventory, actual full vertical semantic witnesses,
independent-process replay, selected protected regressions, full repository
regression and freeze/staging hygiene. The gate does not commit or tag.

## Certified A5a gate

- Independent inventory tests: 7 PASS.
- Real frozen Compiler/host integration: 6 PASS.
- Prior certified phases: 16.
- Tracked predecessor files: 97.
- Stratified source cases: 36.
- Vertical cross-layer witnesses: 108.
- Previous protected regressions: 60 PASS.
- Full repository regression: 3370 PASS.
- Independent-process canonical replay: PASS.
- Frozen source and Git hygiene: PASS.

Evidence SHA256:
123040eeb3ce4d8025c141c79acd0ff7c58dde33379eeadcb840989982dcc0fa

Acceptance covers Git-pinned predecessor inventory
and stratified cross-layer architectural witnesses.

Historical gate digests are recorded outcomes, not
independently regenerated signatures. Full hardware
conformance and exhaustive cross-product replay
are not claimed.
