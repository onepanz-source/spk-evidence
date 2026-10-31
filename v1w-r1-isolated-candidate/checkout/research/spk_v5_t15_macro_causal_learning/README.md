# T15 macro: prospective A-computed feedback falsification

T15 is a separate **research** three-actor C→environment→A→B→C loop. It is not a rewrite or native addition to T14. C uses original frozen SPK `pe_execution_v1b._compute_local` for decision thresholds. A receives a pre/post temperature sensor pair and a private-world target, encodes absolute-distance features **locally in Python**, and calls the same original PE fragment to emit an improvement/worsening result. B executes a PE relay. The host supplies environment initial conditions, physical law, and raw input temperatures, **not a per-trial action, reward or verdict**. Persistent C P updates are versioned, applied in a SQL transaction only after B feedback, and independently audited. This closed loop is atomic per episode; events are ordered in the ledger but not dispatched by original BV's clocked scheduler.

## Prospectively fixed evaluation

* Ten environments with setpoints 3..12 (C never receives the setpoint), three deterministic training permutations (17,29,43), total 30 cells per condition.
* Training sees even temperatures 0,2,...,14, excluding equilibrium; evaluation sees odd temperatures 1,3,...,15, excluding equilibrium. Within every cell there is zero training/evaluation temperature overlap. **There are 75 distinct world+heldout-temperature pairs, evaluated three times = 225 total observations, not 225 statistically independent physical situations.**
* C P policy is a learnable integer threshold theta (initially 12), expressed as two complementary original PE computations. Negative feedback adjusts theta using a known monotone actuator-sign assumption. A emits whether action improved absolute distance to the target via original PE comparisons; C does not observe the target.
* No learning, missing feedback, altered verdict and wrong-lineage controls. Evaluation always runs with P frozen. Counterfactual reverses actuator signs without changing C's update rule.
* **Prospective research support criterion:** adaptive vs frozen held-out success rate improves by at least **10 percentage points**, each training-order seed improves, held-out physical loss falls, no evaluation writes, all controls have zero credits. This does not assert native SPK learning. Research report is still publishable and PASS as *completed falsification* if support is not found, but must say `NOT_SUPPORTED`.

## Reproducibility and trust limits

Original frozen PE source must match SHA `8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c`. Local testing used the original `_compute_local` source with a temporary *import-only* stand-in for an unavailable fabric module; this shim is **not bundled** and is not allowed on fwork. T15 itself does not execute frozen BV-v0e, original A1d, T14 Ed25519 or original memory-service grants during research training. Their source immutability and T14 report are checked as ancestry, not misrepresented as T15 capabilities.

This task uses a very simple deterministic world, a rule-based A evaluator with Python feature preprocessing, and a hand-designed low-dimensional C learning update. All run in a host-controlled Python process. No independently attested physical A sensor, no learning in frozen SPK BV, no intrinsic source-authored objective/goal, no general-purpose backpropagation, no generalization to new world dynamics, no distributed clock, and no environmental causal discovery have been demonstrated.

The reverse-actuator counterfactual is intended to expose exactly that restricted model dependence. The outcome may be unfavorable; preserve it as evidence rather than suppressing it.

Run on user's full original checkout:

```bash
bash search/spk_v5_t15_macro_prospective_learning_gate.sh ~/workspace/spk-evidence/spk-v5-t15-macro-prospective-learning.json
```
