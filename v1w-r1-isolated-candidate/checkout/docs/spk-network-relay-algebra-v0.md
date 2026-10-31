# SPK Network Relay Algebra v0

## 1. Scope

This document formalizes the homogeneous relay-DAG fragment of
SPK Network v0.

It does not claim completeness for arbitrary SPK/Core networks.

The fragment assumes:

- a finite directed acyclic graph;
- positive integer edge delays;
- homogeneous relay nodes;
- initial raw state zero;
- routed inputs on channel 0;
- relay output on channel 7;
- terminal-output observation;
- event multiplicity preserved by the network transport;
- batching by `(timestamp,node)`.

The relay program is:

    ACC(1,0)
    CMP(1)
    EMIT(7)
    RESET(0)

Every non-empty channel-0 batch therefore produces exactly one output
event at the same timestamp and returns the persistent raw state to
zero.


## 2. Local relay semantics

Let a relay receive at timestamp `t` a batch containing `m >= 1`
events on channel 0.

Its state evolution is:

    raw = 0
    raw := m
    guard := true
    emit one event at t
    raw := 0

Therefore event multiplicity inside one timestamp is erased:

    m >= 1  ->  one output event

Hence the relay implements temporal support:

    multiset of timestamps
        ->
    set of timestamps


## 3. Delay sets

Let:

    P_f(N_0)

denote the finite subsets of the non-negative integers.

Define parallel composition:

    A ∪ B

and serial composition:

    A ⊕ B =
        { a + b | a in A, b in B }

The neutral elements are:

    parallel zero:
        ∅

    serial identity:
        {0}


## 4. Algebraic laws

For finite delay sets A, B, C:

### N-UNION-01 — associativity

    (A ∪ B) ∪ C
        =
    A ∪ (B ∪ C)

### N-UNION-02 — commutativity

    A ∪ B
        =
    B ∪ A

### N-UNION-03 — idempotence

    A ∪ A
        =
    A

### N-UNION-04 — identity

    A ∪ ∅
        =
    A


### N-SERIAL-01 — associativity

    (A ⊕ B) ⊕ C
        =
    A ⊕ (B ⊕ C)

### N-SERIAL-02 — identity

    A ⊕ {0}
        =
    {0} ⊕ A
        =
    A

### N-SERIAL-03 — empty annihilator

    A ⊕ ∅
        =
    ∅ ⊕ A
        =
    ∅


### N-DIST-01 — left distributivity

    A ⊕ (B ∪ C)
        =
    (A ⊕ B) ∪ (A ⊕ C)

### N-DIST-02 — right distributivity

    (A ∪ B) ⊕ C
        =
    (A ⊕ C) ∪ (B ⊕ C)


Therefore the relay delay domain forms an idempotent semiring:

    (
        P_f(N_0),
        ∪,
        ⊕,
        ∅,
        {0}
    )


## 5. Node recurrence

For every network node `v`, define `T_v` as the finite set of output
timestamps produced by the relay.

For the external source node `a`:

    T_a = support(input timestamps)

For every other node:

    T_v =
        union over incoming edges (u,v,d)
        of

            T_u + d

where:

    T_u + d =
        { t + d | t in T_u }

Because the node is a relay, coincident arrivals are batched and
therefore duplicates disappear automatically.


## 6. Path-delay theorem

Let `Paths(a,v)` be the directed paths from source `a` to node `v`.

For a path `p`, define:

    delay(p) =
        sum of edge delays along p

Then for every reachable node `v`:

    T_v =
        {
            t + delay(p)
            |
            t in support(input),
            p in Paths(a,v)
        }

with ordinary set semantics.


## 7. Proof

The proof is by induction over any topological ordering of the DAG.

### Base case

For source node `a`, every non-empty external batch at timestamp `t`
produces exactly one relay output at timestamp `t`.

Therefore:

    T_a = support(input)

which corresponds to the zero-length path having delay 0.


### Inductive step

Assume the theorem holds for every predecessor `u` of node `v`.

Every edge:

    u --d--> v

translates every event timestamp produced by `u` by `d`.

Hence that edge contributes:

    T_u + d

to `v`.

The network batches all arrivals sharing `(timestamp,v)`.

The relay emits one event for every distinct timestamp appearing in
those arrivals, independent of multiplicity.

Therefore:

    T_v =
        union over (u,v,d)
        (T_u + d)

Substituting the induction hypothesis for every `T_u` gives exactly all
source-to-v paths, with each path delay equal to the sum of its edge
delays.

Thus:

    T_v =
        {
            t + delay(p)
            |
            t in support(input),
            p in Paths(a,v)
        }

The theorem follows for every node of the finite DAG.


## 8. Network normal form

For terminal-output observation, define:

    NF(N) =
        {
            terminal_node
                ->
            finite set of source-to-terminal path delays
        }

Two networks in the declared relay-DAG fragment are observationally
equivalent when they have the same normal form:

    NF(N1) = NF(N2)

provided terminal node identity remains observable.


## 9. Finite experimental evidence

### Three-node experiment

Network slots:

    a->b
    a->c
    b->c

Edge choices:

    absent
    delay 1
    delay 2

Results:

    syntactic networks: 27
    behavioral classes: 16
    collapsed excess: 11

Serial relay delay composition was supported for all tested pairs:

    (1,1)
    (1,2)
    (2,1)
    (2,2)

A counting sink demonstrated that parallel-edge idempotence is not a
structural property of arbitrary SPK networks.


### Four-node exhaustive DAG experiment

Nodes:

    a,b,c,d

Possible forward edges:

    a->b
    a->c
    a->d
    b->c
    b->d
    c->d

Each edge had three choices:

    absent
    delay 1
    delay 2

Therefore:

    3^6 = 729

syntactic networks were tested.

Results:

    syntactic networks: 729
    delay-set normal forms: 159
    runtime behavioral classes: 159

    runtime/predictor mismatches: 0
    normal-form ambiguities: 0

Hence, on the complete declared four-node finite domain:

    syntactic network
        ->
    delay-set normal form
        ->
    behavioral class

produced exact one-to-one agreement between normal forms and observed
behavioral classes.


## 10. Important boundary

The idempotence:

    A ∪ A = A

does not come from network transport.

Network transport preserves event multiplicity.

Idempotence is induced by the relay node semantics:

    non-empty batch
        ->
    one emitted event

A different sink can distinguish multiplicity.

For example, a sink containing only:

    ACC(1,0)

distinguishes one parallel edge from two parallel edges.

Therefore relay delay-set algebra is an emergent algebra of the
declared node fragment, not a universal structural algebra of SPK
networks.


## 11. Relation to the event algebra

The base SPK event algebra preserves multiplicity:

    MERGE(E,E) != E

and is naturally represented by finite multisets.

The relay projection maps timestamp multiplicity to temporal support:

    finite multiset
        ->
    finite set

After this quotient:

    D ∪ D = D

becomes valid.

Thus composition through a specific SPK primitive can induce an
algebra whose identities are stronger than those of the underlying
event transport.


## 12. Status

For the declared homogeneous relay-DAG fragment:

- a general path-delay normal form has been derived;
- its correctness follows by induction on DAG topology;
- the resulting delay domain is an idempotent semiring;
- exhaustive four-node finite testing agrees exactly with the normal
  form.

This does not establish an algebra for:

- arbitrary Core programs;
- heterogeneous node types;
- zero-delay edges;
- cyclic networks;
- arbitrary initial state;
- observation of internal emissions;
- multiplicity-sensitive sinks.

Those are separate extensions of the semantic domain.
