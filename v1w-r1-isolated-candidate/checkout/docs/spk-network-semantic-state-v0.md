# SPK Network Semantic State v0

## 1. Scope

This document defines semantic state and contextual equivalence for the
finite mixed-node SPK Network v0 fragment studied experimentally.

The declared fragment contains:

- three nodes: a, b, c;
- source node a fixed as relay R;
- nodes b and c independently chosen from R and T2;
- feed-forward edge slots:
    a->b
    a->c
    b->c
- each edge absent or carrying delay 1 or 2;
- binary external input per logical tick;
- terminal-output observation;
- no ShiftDecay;
- zero initial raw state.

The node programs are:

R:

    ACC(1,0)
    CMP(1)
    EMIT(7)
    RESET(0)

T2:

    ACC(1,0)
    CMP(2)
    EMIT(7)
    RESET(0)


## 2. Operational state

For this fragment, the operational state of a network is:

    S_op =
        (
            persistent Core raw values,
            pending routed events
        )

`last_timestamp` is excluded from the semantic machine because the
declared fragment contains no ShiftDecay or other instruction capable
of observing elapsed time.

Pending routed events are part of operational state because positive
edge delays allow emitted events to remain in flight across logical
ticks.


## 3. Input alphabet

The external input alphabet is:

    Sigma = {0,1}

where:

    0 = no external event at the current tick
    1 = one non-empty external batch at source node a

Because source node a is relay R, multiplicity inside one external
batch is immediately quotiented to presence/absence.

Therefore binary input is complete for the declared external
interface.


## 4. Exact transducer semantics

Every network N in the declared fragment induces a deterministic
finite Mealy machine:

    M_N =
        (
            S,
            Sigma,
            delta,
            lambda,
            s0
        )

where:

    S      = reachable operational states
    Sigma  = {0,1}
    delta  = state transition function
    lambda = terminal-output function
    s0     = initial network state

The operational state space is finite for this fragment.


## 5. Contextual state equivalence

Two reachable operational states s1 and s2 are semantically
equivalent iff every possible future input word produces the same
observable terminal-output sequence:

    s1 ~ s2

iff

    for every w in Sigma*:

        Obs(s1,w) = Obs(s2,w)

This is future-behavior equivalence.

The semantic state represented by an operational state s is therefore
its equivalence class:

    [s]~

Operational state identity is not required.

In particular:

    raw(s1) != raw(s2)

does not imply:

    [s1]~ != [s2]~


## 6. Network contextual equivalence

Two networks N1 and N2 are contextually equivalent at the declared
interface iff their initial states have identical future behavior:

    N1 ~ctx N2

iff

    for every w in Sigma*:

        Obs(N1,w) = Obs(N2,w)


## 7. State minimization

The reachable Mealy machine is minimized by partition refinement.

Two states remain in the same partition block iff, for every input
symbol:

1. their immediate observable outputs are equal; and
2. their successor states belong to the same partition block.

The stable partition is exactly the quotient:

    S / ~

and therefore represents the minimal semantic state space of the
network.


## 8. Canonical transducer normal form

After minimization, semantic states are assigned canonical identifiers
by breadth-first traversal from the initial semantic state, following
input symbols in fixed order:

    0, 1

The resulting transition/output table is the canonical transducer
normal form:

    NF_T(N)

For the declared deterministic finite fragment:

    NF_T(N1) = NF_T(N2)

iff

    N1 ~ctx N2


## 9. Finite exact experiment

The declared topology/type space contains:

    4 node-type assignments for b,c

times:

    3^3 = 27 edge configurations

for a total of:

    108 typed networks.


### Reachable operational states

Across all network instances:

    total reachable operational states: 1010

Per-network reachable state counts ranged from:

    minimum: 1
    maximum: 40


### Minimal semantic states

After exact Mealy minimization:

    total minimal semantic states: 643

Therefore:

    operational states quotiented away: 367

Networks whose state space was reduced:

    64 / 108

Largest observed reduction:

    40 operational states
        ->
    14 semantic states

for:

    b=T2
    c=T2
    ab=2
    ac=-
    bc=2


## 10. Network equivalence classes

Canonical minimized transducers produced:

    52 exact contextual classes

from:

    108 physical network descriptions

Therefore:

    collapsed network excess: 56

Non-singleton contextual classes:

    21


## 11. Independent runtime bridge

The independently implemented exact finite-state machine was compared
against the primary SPK network runtime.

Bridge horizon:

    6

Runtime comparisons:

    13,716

Observed mismatches:

    0

This validates the exact-machine encoding over the declared finite
bridge corpus.


## 12. Independent equivalence cross-check

Every pair of the 108 network instances was compared using both:

1. canonical minimized-transducer equality;
2. direct product-state contextual equivalence.

Pairs checked:

    5,778

Equivalence disagreements:

    0

Therefore two independent equivalence procedures produced exactly the
same partition.


## 13. Latent implementation state

The exact product-state experiment identified networks that are
contextually equivalent despite reaching different implementation raw
states.

Example:

Network L:

    b=R
    c=T2
    ab=-
    ac=2
    bc=-

Network R:

    b=T2
    c=R
    ab=1
    ac=-
    bc=1

After input prefix:

    10

reachable raw states include:

    L:
        a=0
        b=0
        c=0

    R:
        a=0
        b=1
        c=0

Despite this raw-state difference, exhaustive reachable product-state
exploration proves identical observable output for every future binary
input word.

Thus:

    implementation state
        !=
    semantic state


## 14. Relation to relay delay-set algebra

The homogeneous relay-DAG fragment admits a simpler representation:

    finite set of path delays

because relay R destroys multiplicity and returns persistent raw state
to zero.

Introducing T2 breaks that static delay-set representation because T2
can retain information between batches.

The appropriate semantic object therefore changes from:

    static delay set

to:

    finite-state transducer

The relay delay-set algebra is thus a special stateless quotient of the
more general stateful network semantics.


## 15. Semantic-state principle

For SPK Network v0:

    physical configuration is an implementation representation;

    semantic state is the minimal residual information required to
    determine all possible future observable behavior.

Equivalently:

    semantic state =
        equivalence class of operational states
        under future observation.


## 16. Epistemic status

Established exactly for the declared finite R/T2 network fragment:

- finite operational-state construction;
- complete reachable-state exploration;
- exact deterministic Mealy minimization;
- exact product-state equivalence;
- canonical transducer representation;
- agreement between product equivalence and canonical equality.

Empirically cross-validated against the primary runtime on 13,716
finite executions.

Not established for:

- arbitrary Core programs;
- ShiftDecay;
- arbitrary thresholds;
- arbitrary weights;
- arbitrary topology size;
- cyclic networks;
- zero-delay edges;
- non-binary external interfaces;
- arbitrary channel mappings;
- arbitrary initial states;
- infinite-state Core configurations.

No universal completeness claim is made.
