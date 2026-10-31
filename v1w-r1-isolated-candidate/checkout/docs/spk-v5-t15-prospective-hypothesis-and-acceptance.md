# SPK V5 T15: a falsifiable causal-feedback learning experiment

## Claim under test

Can a C agent with versioned P reduce held-out error solely from evaluative output computed by downstream A after environmental consequences, without host-provided per-trial reward labels?

## Interventions / controls

World: integer state temperature 0..15, target (private to A and plant) in 3..12. C emits one of two signed actuations using original SPK PE threshold primitives. A evaluates two *observed* states using local distance encoding and original SPK PE CMP/EMIT. B uses original PE to relay the verdict. During training only, negative verified A verdict may update C's threshold. The improvement objective is an A-computed function of sensor and its own target, not an input verdict or correct action supplied by the experiment harness.

The same train and test temperatures apply to adaptive and control cells; their split is fixed before training. Held-out tests use only odd temperatures, never shown to C for the same environment, and freeze P. Physical loss is evaluated independently from the state-transition rule. Control conditions: frozen P, no feedback, altered feedback rejected, wrong-lineage feedback rejected. Falsifying counterfactual: flip actuator sign, violating C's assumed model.

## Predeclared acceptance gates

A research improvement is *supported on this restricted family only* if the held-out absolute success-rate difference is >= 0.10, each predeclared seed improves, aggregate physical loss decreases, no control updates P, and P never changes in evaluation. This is not a statistical claim about physical-world generality. 10 targets x (8 odd temperatures minus equilibrium when odd) = 75 unique cases, repeated under three training orders for 225 observations. Tests additionally check deterministic replay, the entire A PE truth table, C PE decision truth table, source/decision/credit lineage, SQLite rollback and tamper discovery.

Scientific negative output (`NOT_SUPPORTED`) remains a completed research test, not a software failure. Source, integrity, determinism or unintended P changes are *software failures* and abort the gate.

## Unresolved gaps

A computation is original SPK `_compute_local` after Python-owned sensor preprocessing. The host controls the environment model and A's program, and can falsify and reseal all internal storage. The world/feedback actors are within one process; there is no original BV propagation and no original A1d/memory grant in the trial. No native SPK learning, no signer independence, no physical time, no unanticipated physics, no general reinforcement-learning guarantee. Passing this experiment is evidence for the restricted causal update mechanism only, and a reason to design a new versioned SPK runtime with this type of receiver-owned evaluation.
