# SPK Compiler v0 Freeze: C4 Release Gate

Status: release candidate until clean-worktree release gate and annotated tag.
Baseline: `spk-core-network-v0`.
Compiler source: HEAD after the C3 conformance checkpoint.

## Freeze boundary

C4 freezes the v0 compiler code currently tracked under `spk_compiler/`,
`spk_architecture/profile_v0.py`, C1/C2/C3 normative documents and their tests.
The complete list is generated from Git and embedded in
`docs/spk-compiler-v0-freeze-manifest.json`. Every file receives a SHA-256
content digest. The inventory itself is canonical JSON with a payload SHA-256.

The `spk_core/` and `spk_network/` code trees must have no tracked differences
relative to the frozen `spk-core-network-v0` tag, whose commit identifier is
recorded in the manifest. The baseline tag must not move.

This is **not** a signed release, a source-authenticity proof, or a functional
verification for every possible workload. The existing C1/C2/C3 and complete
regression suites must pass in a clean, detached Git worktree.

## No architectural scope creep

C4 must NOT alter the behavior of Core v0, Network v0, Compilation Pipeline v0,
Resource/PE Admission v0, Compilation Manifest v0, or Simulator v0. It does not
claim dynamic buffer admission, backpressure, deadlock freedom, physical
hardware execution, or native machine-code generation.

The release manifest is distinct from C2's **compilation manifest**:
C2 describes one compiled network; C4 identifies the frozen compiler release.

## Procedure

1. Commit C3. Confirm compiler sources are otherwise clean and baseline tag is available.
2. Extract the C4 package in the repository root.
3. Generate the freeze inventory using
   `python search/compiler_v0_freeze_manifest.py --write`.
4. Run `bash search/compiler_v0_freeze_gate.sh --preflight`.
5. Stage only the C4 release files; review Git diff and commit C4.
6. Run `bash search/compiler_v0_freeze_gate.sh --release`.
   This requires tracked files to be clean; unrelated untracked research files
   may remain. It creates a temporary, detached worktree using HEAD and runs
   release validation and tests there, then removes the worktree.
7. Only after the release gate succeeds, create the annotated Git tag
   `spk-compiler-v0` and inspect it.

If any phase fails, do not create the tag or claim a freeze.
