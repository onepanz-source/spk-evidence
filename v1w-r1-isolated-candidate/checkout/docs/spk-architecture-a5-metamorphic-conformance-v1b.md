# SPK Architecture A5b: cross-system metamorphic conformance v1b

**Status: INTEGRATION PASS (2026-10-16, bounded ordering-preserving domain).**

## Scope

A5b is the second A5 conformance milestone, built exclusively as six new
files. It does not alter Core, Network, Compiler, Simulator, or earlier
Architecture sources. Its predecessor A5a must be committed and its historical
evidence SHA-256 recorded. A5a's sixteen-phase source custody is checked again.

The complete frozen 216-case corpus, on three PE placements, produces 648
independent cross-system metamorphic witnesses. These test genuinely transformed
execution contexts, not just the replay of unmodified input.

1. **PE identity alpha-renaming**: PE0/PE1/PE2 are replaced with disjoint,
   order-preserving Q0/Q1/Q2. Node ownership, parallel routes, PE grants,
   P/S/E/O quotas, outboxes, memory and all output PE labels change together.
   The *complete causal output* must match after reverse normalization. The
   mode-controller context digest must change and refuse reuse of old authority.
2. **Expansion of nonbinding capacities**: run PE service, P/S/E/O memory,
   link throughput, sender FIFO and in-flight capacities at 256 and 1024 units.
   These are nonbinding for the bounded corpus. The entire neuronal result,
   causal transfer transcript and absence of link congestion must agree.
   This does NOT assert invariance under expansion of genuinely binding limits.
3. **All-local link irrelevance**: in 216 `single` placements change cross-PE
   latency, remote inflight capacity and remote link throughput radically.
   Since no link is remote, the actual neuron result must be identical and
   remote grants remain zero.
4. **Congested transport accounting**: each A3d limited-link execution must
   deliver precisely its *actual* emitted remote occurrences and retain no
   in-flight or outbox entries after CLOSED; processed events equal original
   inputs plus actual transfers. Event counts across differently timed
   executions are not erroneously required to match.

As independent witnesses to the frozen semantic source, 36 stratified
program/topology examples on each placement (108 executions) run the real
frozen Compiler/host ideal reference against a newly executed A3d zero-extra-
latency, unbounded-service profile. The Compiler witness certifies only the
ideal semantics, never the intentionally delayed/congested executions.

Evidence is source-pinned to the Git HEAD and a recorded A5a historical SHA,
and independently regenerated in two Python processes. A recomputed digest
on a forged payload must still be refused by full canonical replay.

## Explicit limits

PE relabeling preserves PE traversal order: invariance under an arbitrary
scheduler tie-break order is NOT claimed. The 256/1024 resource plans are
nonbinding only on this finite three-neuron corpus. Congestion can alter
neuron state and even emission counts; quota monotonicity of neuronal outputs
is deliberately NOT asserted. The model retains one global logical arbiter.
It has no physical NoC, real RAM transaction timing, distributed clocks,
trusted hardware enclave, or durable recovery journal.

## Final gate

`bash search/spk_arch_a5b_final_gate_v1b.sh`

Six stages: all-case independent metamorphic laws, real frozen Compiler ideal
cross-witnesses, two-process independent evidence replay, protected A5a/A3d
regressions, full suite, frozen Git and new-file hygiene. Does not commit or tag.

## Certified A5b gate

- Independent metamorphic tests: 9 PASS.
- Frozen Compiler/host integration: 5 PASS.
- Metamorphic witnesses: 648.
- Nonbinding capacity expansion witnesses: 648.
- Single-PE remote-link inert witnesses: 216.
- Actual cross-PE occurrences: 771.
- Committed predecessor phases: 17.
- Protected regressions: 42 PASS.
- Complete repository regression: 3384 PASS.
- Independent-process canonical replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
0d1967732deb7429a11d15955d8cf1b1f23a1feafade61e1c28dc96eb26be07b

Acceptance covers PE alpha-renaming, nonbinding
resource expansion, all-local remote-link
irrelevance and causal event conservation.

No arbitrary scheduler-order invariance, binding
capacity monotonicity or physical hardware
conformance is certified.
