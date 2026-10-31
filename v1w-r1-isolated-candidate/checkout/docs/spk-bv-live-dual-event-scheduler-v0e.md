# SPK Back Validation v0e: live dual-event shared-credit scheduler (research)

**Status:** RESEARCH CANDIDATE; independent `fwork` gate not yet executed. No release, promotion, learning or hardware claim.

**Parent**: frozen `spk-architecture-bounded-reference-v1`, commit `5af99cd1f4d603bf0c8e1557a6561c107765fdb5`; BV v0/v0a/v0b/v0c/v0d are inherited. No frozen files are edited. All source additions are in the research worktree `spk-backvalidation-v0`.

## 1. Research question

Can actual neuron executions and causally derived BV packets contend **during** the same logical execution for an explicitly finite fabric link, PE-service slots, memory service and cross-PE in-flight capacity, such that BV arbitration can causally **change forward link timing**?

Unlike v0d, this experiment does not run A3d to completion and then insert BV into the leftover timetable. A new separate bounded logical scheduler executes actual A1b local semantics (`_compute_local`) and emits forward events and BV packets in a *single execution*. Existing A3d remains unchanged. This is NOT native BV inside A3d, nor proof of its complete observational equivalence.

## 2. Semantics

Each tick:

1. Deliver previously granted forward and BV cross-PE events, respecting positive delays.
2. Process eligible neuron batches in `(ready_tick, node_id)` order, with priority over BV in the **PE-computation stage**. Reserve their conservative A3c memory envelopes atomically within current PE/domain/fabric budgets. Evaluate the real frozen A1b instructions. Record each emitted routing occurrence and its input occurrence parents.
3. On an eligible terminal emission by the declared observer, create a contextual assessment from actually observed inputs. Queue reverse packets grouped by observer and actual immediate causal source. This is *observed influence*, **not** proven causal credit.
4. Arbitrate queued forward link transmissions and reverse BV packets **online**. Both consume finite fabric and directional link slots and share in-flight capacity. BV packets additionally require one sender PE service grant and two logical memory service permits (O: sender, E: receiver). Neither class is silently dropped on congestion.
5. Repeat until both event classes, outboxes and in-flight queues are drained, or refuse completion on a bound/horizon violation.

Two policy choices are admitted: `forward-first` and `feedback-first` at the **link-arbitration stage**. In both, forward neuron *computation* retains precedence for PE/memory service at each tick. This is not a generally fair or optimal arbiter. No BV event edits a neural state or program. A reverse hop follows an actual input occurrence's `(source, target)` relation, rather than a presumed static edge. Parent chains were created by the live batches. Fan-in is recorded as a set of occurrence parents, not fictitious fractional contributions. A receiver contributes at most one independent vote per assessment, even if several paths carry it.

## 3. Bounded experimental domain

- A1a/A1b frozen three-node `A, B, C` fabric; the pilot uses `spread` and the causal chain `A→B→C` with delay 1. Duplicate edges may be admitted when the positive-delay and capacity preconditions hold.
- Frozen programs `OLD` and `NEW` from BV v0b, and `RELAY` at B/C; `C` observes terminal channel 7. Inputs at ticks 1 and 3 for the primary demonstration.
- New bounded data: live route occurrence IDs, receipt times, parent occurrence IDs, terminal assessments, BV packet IDs, per-tick joint grant ledger, in-flight counts and contention counters.
- An all-or-nothing conservative per-batch memory reservation. Unlike A3d, this prototype does **not** accumulate grants for a batch over multiple ticks. Such cases can be delayed until exhaustion and rejected. Controller-issued A2b authority is **not** reproduced. These are deliberate scope restrictions, not equivalence claims.
- Finite logical horizon, peak in-flight limit, sender outbox cap, batch/event/occurrence/BV-packet limits, reverse hop cap and positive latencies. No rollback guaranteed on refusal.
- Local forward routing is supported; same-PE BV feedback is explicitly rejected in this prototype.
- No N-node engine, physical parallel clocks, physical memory traffic, real NoC, concurrent program mutation, context-derived semantic fitness, global causal credit, statistical generalization, learned policy, or A4c promotion.

## 4. Falsifiable pilot and observed local reference

| Case | Forward link grants | BV link grants | Terminal ticks |
|---|---:|---:|---|
| BV disabled, frozen A3d reference fixture | 4 | 0 | 3, 5 |
| New live runtime, forward-first | 4 | 4 | 3, 5 |
| New live runtime, feedback-first | 4 | 4 | 3, 7 |

Under a one-slot-per-tick shared fabric link and in-flight budget, the feedback-first policy grants a reverse message at tick 3 instead of A's second forward emission. A→B must wait until tick 5 and the second terminal result arrives at tick 7. **That is a live interference observation**, not a posthoc cost overlay. BV-off matches A3d for *the admitted fixtures* in both terminal outputs and actual link grant times (8 parametrized fixture checks). This does not prove equality over all A3d configurations.

All BV grants are charged one abstract service unit and two abstract memory units. The per-tick ledger is checked against PE/domain/fabric service and memory caps, directional/fabric link slots, and shared cross-PE in-flight capacity. A receipt is not counted as multiple independent votes when duplicate paths converge.

## 5. Integrity, gates and next research dependency

Execute `bash search/spk_bv_v0e_research_gate.sh` in the research worktree with the existing `.venv` activated. It covers new live scheduling tests, inherited BV and frozen selected tests, source/ancestry protection, and an independent-process canonical JSON capture/replay. Then `bash search/spk_bv_credit_v0a_full_regression.sh` for the branch-compatible full functional suite; six historical Git release-custody tests remain intentionally deselected, not counted as passes.

Evidence is bound to a complete deterministic payload with SHA-256. A payload with rehashed but forged timings is still refused by fresh source-backed replay. This does not create an external trust anchor, a formal safety proof, or tamper-proof hardware.

**Next decision:** do not attempt program learning yet. First generalize event identity/custody and dual-class admission from three fixed nodes to variable `N`, then compare alternative arbitration/fairness policies under recurrent graphs, fan-in, congestion and sparse-time horizons. The BV contextual assessor remains explicitly separate from independent task-quality measurement.
