# SPK V5-T3i/j/k consolidated research milestone

Research-only experiment, no changes to Core v0, Network v0, Compiler v0, Architecture v1 or frozen BV v0e.

## T3i: decision/credit custody and research registry

The host-owned policy registry chooses one of the **unchanged neural A programs** `current`, `persist`, `silent`, solely from previous and current light thresholds. It commits the choice and context before supplying C's separate CO2 reading to the T3h A1b execution. The unchanged T3h C program computes the verdict with `ACC/CMP/EMIT/RESET`, forwards it over C->B->A, and the unchanged A1b A credit program consumes it. Only an exact, reexecuted C-authored A-consumed witness may alter the registry's per-context bandit weights. A missing marker, C sensor, forward or reverse route or an expired/lost pending packet produces **no update**, not a negative reward. Every decision and update is linked by a SHA-256 audit chain. Forge/replay/out-of-order/weight alteration must fail.

**The registry and policy update are external to A1b. A is not self-modifying.** A1b execution is native to the frozen architecture reference, but the selector and delayed cross-episode credit registry are research-owned and not native BV transactions. The sensor CO2 threshold at C is supplied by the host; source/sensor identity is not authenticated. Delayed settlement is a modeled registry delay, not a measurement of native network jitter.

## T3j: engineered regime shifts and negative controls

The deterministic generator places 1,200 **non-independent engineered** sequential episodes in 3 regime blocks: C's target follows current light, then C is mostly quiet, then C follows persisted light. There is 4% measurement noise. Four predefined PRNG seeds, with and without source/control disruptions, produce 9,600 shifting episodes. Compare a contextual recency-weighted 3-arm learner (epsilon=.12, alpha=.20) with fixed `current`, `persist`, `silent`, random arms, and a separate placebo bandit updated from unrelated pseudo-random coin flips. Fixed-arm audit runs through frozen A1b too. Six further 1,200-episode negative experiments with stationary-current, uninformative-coin and 7-event rapid-switch environments reveal limitations. Total 16,800 generated episodes. The regime itself and C oracle are engineered by the same harness and do NOT constitute external reinforcement truth.

## T3k: public original UCI diagnostic and falsification

On the *prefix* of 1,200 chronological consecutive pairs in each original UCI CSV (3,600 max), C observes host-thresholded CO2; A chooses without access to it or to the photographic label. Photo occupancy labels are consulted only **after** each A1b output, strictly for post-hoc scoring, and never for learning. This data has already been examined extensively (T3a–T3f), so it is **not blind** or prospective. Optimization toward CO2 agreement can conflict with photographic occupancy. Source hashes must match the original UCI inputs. The public result is diagnostic, not an estimate of future generalization. A fresh independently held and authenticated goal/sensor reference would be required for stronger claims.

## Expected outputs and validity

A positive aggregate engineered-shift difference vs best fixed and placebo may be reported only as `ENGINEERED_SHIFT_RESEARCH_FEEDBACK_BENEFIT_NOT_NATIVE`. Failure on stationary/no-signal/rapid switching is retained. Never promote result to autonomous neuronal learning, end-to-end native BV, signed C-origin, physically accurate transit resource budgeting, full goal alignment or new-blind holdout.

Gate: `bash search/spk_v5_t3ijk_closed_loop_gate.sh ~/Scaricati/occupancy /tmp/spk-v5-t3ijk-closed-loop-research.json`. The gate is create-only and validates the canonical report byte for byte.
