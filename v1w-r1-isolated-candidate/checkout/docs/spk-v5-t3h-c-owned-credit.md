# SPK V5-T3h: C-computed, reverse-routed credit (research only)

This **derived Architecture A1b circuit** executes all three neuron programs using frozen `execute_on_pes_v1b` and a research-local `CaseV0`. It does **not** patch BV v0e, Core, Compiler, the frozen architecture, or their ownership contracts.

## Meaning and epistemic limits

- A sees two *distinct ~60-second light measurements* at abstract ticks 10 and 11. A's research arm is `current`, `persist` or `silent`. A sends an explicit decision marker at tick 12 whether or not it emitted a forward spike.
- B forwards actual A output and its marker to C with declared positive one-tick edge delays; no idealized local copy substitutes for the B relay.
- C sees **its own separate binary observation** derived from a CO2 measurement at physical instant t, independent of A's arm (channel 4 when CO2>=600, channel 5 when CO2<600). This is not the photographer-derived occupancy label. **The host adapter still thresholds CO2 and injects the input; there is no independently attested C sensor or cryptographic native issuer.**
- At tick 15, an explicit closure input to C permits C to **calculate** its positive/negative judgment with A1b instructions. Internal accumulator values are: 112 for neither A spike nor CO2-high, 113 for CO2-high only, 114 for A-spike only, 115 for both. A conditional descending `CMP` and `RESET` cascade emits channel 11 for local agreement, 12 for disagreement. The closure emits ch9. Without a C sensor or A decision marker the accumulator never reaches 112: only closure is emitted.
- Reward signal 11/12 travels C→B, B forwards 13/14 to A, and A records **actual consumption as a terminal 13/14 emission**. No rewiring inside frozen Architecture A1b is needed. No retraining, state/policy update, or native BV feedback occurs.
- Missing C observation results in **abstention**, not a negative judgment. The reverse path missing results in C's authored verdict but no accepted credit at A. If A emits a normal spike but source A→B→C transport is broken, **fail closed**: no reward is accepted even if C coincidentally computes a sign consistent with silence. If A chose silence, an absent *unused* forward path cannot be counted as lost evidence, while the explicit marker remains mandatory.
- Each episode uses fresh A/B/C state, preventing cross-episode contamination. A1b global ideal arbitration is **not physical real-time, bound memory/PE admission, or a native signed actor message**. The timeline of abstract ticks is *not* actual ~60s processing latency.
- Input timestamps are checked to be genuinely successive 59/60/61 seconds. Measurement hash binds a claim to its exact source input. Anti-replay here is **deterministic verification by source reexecution**, not independent durable transport custody.

## Limitations and decisions

This milestone demonstrates *C-side neuronal computation of reward* and *reverse neuronal propagation to A* in a three-neuron derived circuit, rather than an host-constructed reward described as if C authored it. However, the C target is an intentionally chosen CO2 binary proxy, **not independently verified occupancy truth**. CO2 and light may share spurious environmental correlations; any high agreement is not a performance or task-utility guarantee.

The 144-case finite matrix is engineered source QA, **not a new UCI result or independent blind dataset**. No weights, local policy, or program are ever modified. Native BV v0e and all frozen contracts remain untouched. Future work requires real provenance-bound separate C sensor authority, PE/resource admission for this route, replay protection, and a one-arm learner validated on newly collected holdout data.
