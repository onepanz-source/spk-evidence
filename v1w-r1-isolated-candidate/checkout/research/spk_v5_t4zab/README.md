# SPK V5 T4ZAB · Live PE C-step boundary & exact frozen source handoff

T4Z = verify all pinned research and frozen sources, anchored to SHA-pinned T4WXY/T4GHI.
T4A = intercept live `_compute_local` returns for node C (in a fresh child process),
       without changing its return value, and verify original source output digests
       for 180 cases; repeat in independent producer processes for byte-exact parity.
T4B = supply an allowlisted read-only copy of `pe_execution_v1b.py` and
       `live_dual_scheduler_v0e.py`, pinned by their original SHA-256 digests.

This is **not** a native neuron emitter, a PE-owned receipt, a native BV semantic
credit, or learning. A Python host wrapper observes the C computation, and can
forge this instrumentation. The semantic sign still comes from the result of
an original frozen BV invocation. Next step is a separate *derived experimental
fork* written against the actual frozen source copies, with in-function emission,
causal attribution, attack tests, and native-boundary honesty; never edit
frozen source or misrepresent Python hooks as C authority.

Runner: `bash search/spk_v5_t4zab_live_C_seam_gate.sh ~/workspace/spk-evidence/spk-v5-t4zab-live-C-seam.json`

Outputs: deterministic JSON report plus `spk-v5-t4zab-frozen-seam-sources.tar.gz` in
same directory as report. Upload both to guide next derived research fork.
