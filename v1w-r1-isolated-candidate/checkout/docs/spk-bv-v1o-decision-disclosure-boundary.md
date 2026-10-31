# BV v1o | Decision disclosure and authority boundary

**Status:** source-bound, T4 shadow decision-visibility experiment. No native decision channel, receiver judgment, learning, or certified algebra rewrite.

## What the already-verified v1n establishes

- The actual A→B edge is present. The native original forward trace has 2 sender emissions and 2 received occurrences; the variant copy has 0 and 0.
- V1n T0–T3 partitions eight worlds (two bound to actual posthoc counts, six explicitly hypothetical). The two hypothetical worlds `SHADOW_INTERNAL_CAUSE_A` and `SHADOW_INTERNAL_CAUSE_B` are indistinguishable through T3.
- B cannot obtain A's decision identity from native logs. Even two-port evidence, an advance expectation and interval coverage do not establish the **internal cause**.

## Additional hypothesis studied in v1o (not installed)

Consider a proposed `shadow.decision-record/v1o`, tied to `A→B:7→0`, the expected event identity, episode and a sender decision identifier. In the lab, allow A's asserted operator-selection action to be transmitted to B, along with a claimed predecision acknowledgment, sender provenance, covered interval and proof of receipt before verdict.

The bounded model demonstrates ten outcomes, including missing decision, unauthenticated content, absent independent receipt, no predecision expectation, coverage gap, mismatched endpoint/episode/event, stale record and the closed-lab hypothetical success case.

**The success case only states that two different *declared actions* become distinguishable if a trustworthy channel is assumed by the closed lab.** It does not establish a signed message, authentic native sender, observable causal contribution or reliable recipient criterion. A selected operator and a missing spike may co-occur without the former causing the latter. An SHA-256 of an uploaded JSON merely identifies the bytes.

The field `declared_lab_producer=True` is an explicit **assumption**, not a security primitive. It cannot authorize native trust and every row contains `native_authority=false`. In actual SPK neither B nor C receives these proposed records; C remains an indirect descendant, not a direct recipient of A.

## Source custody and reproducibility

The CLI `search/spk_bv_v1o_decision_disclosure.py` takes `--v1n` and all the same predecessors as v1n. It checks paths (no aliases, no files inside source tree, no symlinks), recreates v1n using its own native-bound CLI, and requires **byte-for-byte equivalence** before generating a canonical JSON report. It does not mutate any original node or frozen producer.

`bash search/spk_bv_v1o_research_gate.sh` runs isolated-import tests, compiles the two modules, and then invokes the v1n.1 inherited research/freeze gate. The final native-bound CLI must be run separately on fwork. Never confuse local source-audit output with a native replay attestation.

## Remaining gates to native Back Validation

1. Define and implement an actual receiver-readable, source-authenticated, timed decision or expectation event in a future research architecture, with verified receipt and failure semantics. This needs an explicit architectural decision and cannot be slipped into frozen Core/Network/Compiler/Architecture.
2. Establish an independently verified absence observation if missing spikes are to be evaluated.
3. Demonstrate receiver-defined value criteria, causal binding between **decision** and outcome, and controlled prospective evaluation. Separate observation, evaluation, credit assignment and actual update/rollback.

All values of native absence witnesses, native decision records, native scored judgments and native updates in v1o remain zero.
