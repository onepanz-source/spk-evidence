# SPK/v0 — Minimal Spike Operator Semantics

**Status:** Experimental draft
**Version:** 0.0.1
**Purpose:** Define a deterministic, minimal and testable semantic model for the computational search of a compositional spike algebra.

---

## 1. Research question

SPK/v0 investigates the following question:

> Can a small set of elementary event/state operators generate, through composition, a useful family of spike-based computational dynamics?

The initial candidate basis is:

```text
SPK/MERGE
SPK/DELAY
SPK/ACC
SPK/DECAY
SPK/CMP
SPK/EMIT
SPK/RESET
```

This set is provisional.

No operator is assumed to be fundamental.

The purpose of the project is precisely to determine whether some operators are:

- redundant;
- derivable from others;
- unnecessarily specialized;
- replaceable by more elementary operators;
- useful only as higher-level macros.

The long-term objective is to identify a small efficient generating basis:

\[
B^* \subseteq B_0
\]

or to determine that no useful compact basis exists under the chosen semantics.

---

# 2. Non-goals of SPK/v0

SPK/v0 does **not** attempt to:

- model biological neurons accurately;
- reproduce a specific neuromorphic processor;
- define a universal theory of neural computation;
- train a neural network;
- optimize for GPU execution;
- reproduce Loihi, SpiNNaker, Akida or any other ISA;
- prove computational universality;
- define continuous-time physics.

SPK/v0 is deliberately smaller.

Its purpose is to provide a deterministic laboratory in which operator composition can be explored and compared.

---

# 3. Design principles

SPK/v0 follows six rules.

## 3.1 Minimal semantics

Each primitive SHALL perform one clearly defined transformation.

Hidden side effects are forbidden.

---

## 3.2 Determinism

For a given:

```text
program
input
initial state
parameter set
```

execution SHALL always produce the same:

```text
output
final state
```

---

## 3.3 Explicit time

Time is part of the computational object.

It is not merely the order in which instructions execute.

---

## 3.4 Explicit state

Persistent state SHALL be represented explicitly.

Operators SHALL NOT create hidden persistent state unless introduced by a future SPK specification.

---

## 3.5 Simultaneity preservation

Events occurring at the same time SHALL be treated as simultaneous.

Their result SHALL NOT depend on arbitrary iteration order.

---

## 3.6 Falsifiability

Claims such as:

```text
P ≡ Q
```

or:

```text
operator X is redundant
```

must be independently testable by the runtime.

An LLM assertion is not evidence.

---

# 4. Time model

SPK/v0 uses discrete timestamps:

\[
t \in \mathbb N_0
\]

where one unit is called a **tick**.

A tick has no predefined physical duration.

For example:

```text
1 tick = 1 ms
```

may be chosen by an experiment, but is external to the algebra.

Using integer time in v0 avoids floating-point ambiguity when reasoning about temporal equality.

---

# 5. Event

The elementary external object is an event:

\[
e=(t,c)
\]

where:

- \(t\) is the event timestamp;
- \(c\) is the channel identifier.

Formally:

\[
t\in\mathbb N_0
\]

\[
c\in\mathbb N_0
\]

Example:

```text
(12, 3)
```

means:

> one spike occurred at tick 12 on channel 3.

Events have no amplitude in SPK/v0.

An event either exists or does not exist.

---

# 6. Spike train

A spike train \(S\) is a finite multiset of events:

\[
S=\{e_1,e_2,\ldots,e_n\}
\]

Multiple identical events are permitted.

Therefore:

```text
[(10, 0), (10, 0)]
```

is different from:

```text
[(10, 0)]
```

This distinction is important because coincident spikes may contribute multiple times to state accumulation.

For execution, a spike train SHALL be represented canonically in non-decreasing timestamp order.

---

# 7. Event batch

All events sharing the same timestamp form an **event batch**:

\[
B_t=\{e\in S\mid time(e)=t\}
\]

Example:

```text
S = [
    (5, 0),
    (5, 1),
    (5, 1),
    (9, 0)
]
```

produces:

```text
B5 = [(5,0), (5,1), (5,1)]
B9 = [(9,0)]
```

A state program executes once per event batch, not once per individual event.

This prevents arbitrary ordering among simultaneous spikes from affecting the result.

---

# 8. State

SPK/v0 initially provides exactly one persistent scalar state register:

\[
x\in\mathbb R
\]

The initial value is:

\[
x_0
\]

and defaults to:

\[
x_0=0
\]

unless explicitly provided.

The restriction to one scalar state is intentional.

If arbitrary state were permitted from the beginning, a single SPK unit could encode an unrestricted virtual computer and the search for elementary operators would become meaningless.

---

# 9. Transient guard

Execution also contains one transient Boolean register:

\[
g\in\{false,true\}
\]

The guard is **not persistent state**.

At the beginning of every event batch:

\[
g=false
\]

The operator `SPK/CMP` may modify it.

The operators:

```text
SPK/EMIT
SPK/RESET
```

read it.

At the next timestamp the guard is cleared again.

---

# 10. Execution context

During processing of an event batch at time \(t\), the execution context is:

\[
C=(t,B_t,x,g,\Delta t,O)
\]

where:

- \(t\): current timestamp;
- \(B_t\): current event batch;
- \(x\): persistent scalar state;
- \(g\): transient guard;
- \(\Delta t\): elapsed ticks since the previous processed batch;
- \(O\): output spike train.

For the first batch:

\[
\Delta t=t
\]

assuming the machine begins at:

\[
t=0
\]

After the complete state program has executed for timestamp \(t\), that timestamp becomes the reference for the next batch.

---

# 11. Two computational layers

SPK/v0 deliberately distinguishes two kinds of operations.

## 11.1 Event algebra

Transforms spike trains into spike trains:

\[
\mathcal E^n\rightarrow\mathcal E
\]

Initial operators:

```text
SPK/MERGE
SPK/DELAY
```

---

## 11.2 State algebra

Transforms execution state while processing event batches:

\[
(B_t,x,g)\rightarrow(x',g',O)
\]

Initial operators:

```text
SPK/ACC
SPK/DECAY
SPK/CMP
SPK/EMIT
SPK/RESET
```

This separation is provisional but intentional.

One research question is whether these two families eventually form distinct but interacting algebraic structures.

---

# 12. SPK/MERGE

## Signature

\[
MERGE:
\mathcal E^n\rightarrow\mathcal E
\]

with:

\[
n\ge1
\]

## Semantics

For spike trains:

\[
S_1,S_2,\ldots,S_n
\]

`MERGE` produces their multiset union:

\[
MERGE(S_1,\ldots,S_n)
=
S_1\uplus\ldots\uplus S_n
\]

Multiplicity SHALL be preserved.

Example:

```text
A = [(2,0), (5,0)]
B = [(5,0), (7,1)]
```

then:

```text
MERGE(A,B)
=
[(2,0), (5,0), (5,0), (7,1)]
```

## Candidate laws

Commutativity:

\[
MERGE(A,B)=MERGE(B,A)
\]

Associativity:

\[
MERGE(MERGE(A,B),C)
=
MERGE(A,MERGE(B,C))
\]

Identity:

\[
MERGE(A,\varnothing)=A
\]

These laws SHALL be tested explicitly.

---

# 13. SPK/DELAY

## Parameters

```text
delay >= 0
```

with:

\[
delay\in\mathbb N_0
\]

## Signature

\[
DELAY_d:\mathcal E\rightarrow\mathcal E
\]

## Semantics

For every event:

\[
(t,c)
\]

produce:

\[
(t+d,c)
\]

Therefore:

\[
DELAY_d(S)
=
\{(t_i+d,c_i)\}
\]

Example:

```text
S = [(2,0), (5,1)]
DELAY(3,S)
```

produces:

```text
[(5,0), (8,1)]
```

## Candidate laws

Identity:

\[
DELAY_0(S)=S
\]

Composition:

\[
DELAY_a(DELAY_b(S))
=
DELAY_{a+b}(S)
\]

Distribution over merge:

\[
DELAY_d(MERGE(A,B))
=
MERGE(DELAY_d(A),DELAY_d(B))
\]

These are candidate algebraic identities to be verified.

---

# 14. SPK/ACC

`ACC` modifies the persistent scalar state according to the number of matching events in the current batch.

## Parameters

```text
weight: real
channel: optional integer
```

If no channel is specified, all events are accepted.

Define:

\[
count(B_t,c)
\]

as the multiplicity of channel \(c\) within the current batch.

For an unrestricted accumulator:

\[
count(B_t,*)=|B_t|
\]

## Semantics

\[
x'
=
x+w\cdot count(B_t,c)
\]

Example:

```text
x = 2
batch = [(10,0), (10,0), (10,1)]

ACC(weight=0.5, channel=0)
```

gives:

\[
x'=2+0.5\cdot2=3
\]

`ACC` does not modify the guard.

---

# 15. SPK/DECAY

`DECAY` applies exponential temporal decay to the persistent state.

## Parameter

\[
\tau>0
\]

## Semantics

For elapsed time:

\[
\Delta t
\]

the state becomes:

\[
x'
=
x e^{-\Delta t/\tau}
\]

`DECAY` does not depend on the number of events in the current batch.

`DECAY` does not modify the guard.

## Important ordering rule

Program order is semantically significant.

Therefore:

```text
DECAY
ACC
```

and:

```text
ACC
DECAY
```

are generally different.

For example:

\[
DECAY_\tau(ACC_w(x))
\neq
ACC_w(DECAY_\tau(x))
\]

for:

\[
\Delta t>0,\quad w\neq0
\]

This distinction SHALL NOT be silently canonicalized.

---

# 16. SPK/CMP

`CMP` compares the current state against a threshold.

## Parameter

\[
\theta\in\mathbb R
\]

## Semantics

\[
g'
=
\begin{cases}
true & x\ge\theta \\
false & x<\theta
\end{cases}
\]

State \(x\) is unchanged.

Only the `>=` comparison exists in SPK/v0.

Additional comparison predicates SHALL NOT be introduced until evidence shows they are necessary.

---

# 17. SPK/EMIT

`EMIT` converts a true transient guard into an output event.

## Parameter

```text
channel_out >= 0
```

## Semantics

If:

\[
g=true
\]

append:

\[
(t,channel_{out})
\]

to the output spike train.

If:

\[
g=false
\]

no output is produced.

`EMIT` does not change:

\[
x
\]

or:

\[
g
\]

Multiple `EMIT` instructions may therefore emit multiple coincident output spikes.

---

# 18. SPK/RESET

`RESET` conditionally modifies persistent state.

## Parameter

\[
r\in\mathbb R
\]

## Semantics

If:

\[
g=true
\]

then:

\[
x'=r
\]

otherwise:

\[
x'=x
\]

The default reset value is:

\[
r=0
\]

`RESET` does not change the guard.

---

# 19. State program

A state program is an ordered finite sequence:

\[
P=[O_1,O_2,\ldots,O_n]
\]

where each:

\[
O_i
\]

is one of:

```text
ACC
DECAY
CMP
EMIT
RESET
```

Example:

```text
DECAY(tau=10)
ACC(weight=1.0)
CMP(theta=3.0)
EMIT(channel_out=0)
RESET(value=0.0)
```

The operators execute from top to bottom for every event batch.

---

# 20. Stream expression

Before entering a state program, input streams may be transformed using:

```text
MERGE
DELAY
```

Example:

```text
MERGE(
    INPUT(channel=0),
    DELAY(
        3,
        INPUT(channel=1)
    )
)
```

A stream expression is evaluated completely before execution of the state program.

---

# 21. Complete SPK/v0 program

A complete program consists of:

\[
Program=(StreamExpression,StateProgram)
\]

Example:

```text
STREAM:
    MERGE(
        INPUT(0),
        INPUT(1)
    )

STATE:
    DECAY(tau=10)
    ACC(weight=1.0)
    CMP(theta=3.0)
    EMIT(channel_out=0)
    RESET(value=0.0)
```

---

# 22. Execution algorithm

Given:

```text
program P
input spike trains S
initial state x0
```

execution is:

1. evaluate the stream expression;
2. canonicalize the resulting spike train;
3. group events by timestamp;
4. set:
   \[
   x=x_0
   \]
5. set previous timestamp:
   \[
   t_{prev}=0
   \]
6. for each timestamp \(t\):
   - construct \(B_t\);
   - compute:
     \[
     \Delta t=t-t_{prev}
     \]
   - set:
     \[
     g=false
     \]
   - execute every state operator in program order;
   - set:
     \[
     t_{prev}=t
     \]
7. return:
   - output spike train;
   - final persistent state.

Formally:

\[
execute(P,S,x_0)
\rightarrow
(O,x_f)
\]

---

# 23. Deterministic simultaneity rule

The behavior of a program SHALL NOT depend on the ordering of events having identical timestamps.

Therefore:

```text
[(5,0), (5,1)]
```

and:

```text
[(5,1), (5,0)]
```

represent the same input.

Operators receive the entire batch.

This rule is fundamental.

---

# 24. Example: integrate-and-fire-like behavior

Consider:

```text
ACC(weight=1)
CMP(theta=3)
EMIT(channel_out=0)
RESET(value=0)
```

Input:

```text
[(1,0), (2,0), (3,0), (8,0)]
```

Initial state:

```text
x = 0
```

Execution:

```text
t=1: x=1 → no emit
t=2: x=2 → no emit
t=3: x=3 → emit → reset x=0
t=8: x=1 → no emit
```

Output:

```text
[(3,0)]
```

No primitive named `INTEGRATE_AND_FIRE` exists.

The behavior emerges from composition.

---

# 25. Example: leaky integrate-and-fire-like behavior

Consider:

```text
DECAY(tau=10)
ACC(weight=1)
CMP(theta=3)
EMIT(channel_out=0)
RESET(value=0)
```

The behavior traditionally identified as a leaky integrate-and-fire unit is therefore represented as a composition of lower-level SPK operators.

One purpose of this project is to determine whether such compositions recur naturally enough to deserve classification as higher-level macros.

---

# 26. Program length

For initial search experiments, the length of a state program is:

\[
L(P)=n
\]

where \(n\) is the number of state instructions.

Stream-expression complexity SHALL initially be measured separately.

First experiments SHOULD use:

\[
L(P)\le4
\]

followed by:

\[
L(P)\le5
\]

and:

\[
L(P)\le6
\]

only when necessary.

---

# 27. Structural equivalence

Two programs may differ syntactically while expressing the same transformation.

Define:

\[
P\equiv Q
\]

if, for every admissible input and initial state:

\[
execute(P,S,x_0)
=
execute(Q,S,x_0)
\]

including both:

- identical output spike train;
- identical final persistent state.

This is called **strong equivalence**.

---

# 28. Observational equivalence

For some experiments the internal final state may be irrelevant.

Define:

\[
P\equiv_O Q
\]

if for every admissible input:

\[
output(P,S,x_0)
=
output(Q,S,x_0)
\]

even if their final internal states differ.

Strong equivalence implies observational equivalence:

\[
P\equiv Q
\Rightarrow
P\equiv_O Q
\]

The inverse is not guaranteed.

---

# 29. Empirical equivalence

During search it may be impossible to prove equivalence immediately.

For a finite test corpus:

\[
D=\{(S_1,x_1),\ldots,(S_n,x_n)\}
\]

define:

\[
P\equiv_D Q
\]

when both programs produce identical outputs and final states for all samples in \(D\).

This is **not a proof of equivalence**.

It means only:

> no counterexample has yet been found inside test domain \(D\).

All software and documentation SHALL preserve this distinction.

---

# 30. Counterexample

A counterexample for:

\[
P\equiv Q
\]

is an input/state pair:

\[
(S^*,x_0^*)
\]

such that:

\[
execute(P,S^*,x_0^*)
\neq
execute(Q,S^*,x_0^*)
\]

Counterexample search is a first-class operation in SPK.

When an equivalence candidate is proposed, the preferred first action is to attempt to falsify it.

---

# 31. Program signature

For a finite experiment domain:

\[
D
\]

the empirical signature of program \(P\) is:

\[
Sig_D(P)
=
[
execute(P,d_1),
\ldots,
execute(P,d_n)
]
\]

Programs sharing the same signature are candidates for equivalence clustering.

That is:

\[
Sig_D(P)=Sig_D(Q)
\]

implies only:

\[
P\equiv_D Q
\]

not:

\[
P\equiv Q
\]

---

# 32. Rewrite rule

A rewrite rule has the form:

\[
P\Rightarrow Q
\]

and is allowed only when equivalence has been established under the required semantic regime.

Example candidate:

\[
DELAY_a\circ DELAY_b
\Rightarrow
DELAY_{a+b}
\]

Rewrite rules SHALL record their evidence status:

```text
PROVEN
TESTED
CONJECTURED
```

A `CONJECTURED` rule SHALL NOT be used for destructive canonicalization.

---

# 33. Normal form

A future canonicalizer may attempt to compute:

\[
NF(P)
\]

such that equivalent programs map to the same or structurally comparable representation.

SPK/v0 does not assume that a unique normal form exists.

This is a research target, not a specification requirement.

---

# 34. Candidate basis

The initial basis is:

\[
B_0=
\{
MERGE,
DELAY,
ACC,
DECAY,
CMP,
EMIT,
RESET
\}
\]

The project SHALL attempt to determine whether:

\[
B^*\subset B_0
\]

can preserve the target expressive capability.

Possible outcomes include:

```text
some primitives are redundant
```

or:

```text
additional primitives are required
```

or:

```text
no compact useful basis exists
```

All three are valid research outcomes.

---

# 35. Primitive removal test

For each candidate primitive:

\[
o\in B
\]

construct:

\[
B'=B-\{o\}
\]

and test whether target behaviors remain representable.

Primitive removal SHALL consider not only representability but also representation cost.

A primitive is not automatically useless merely because its behavior can be synthesized inefficiently from others.

---

# 36. Representation cost

For a behavior \(F\) and basis \(B\), define:

\[
L_B(F)
\]

as the shortest known program expressing \(F\).

A candidate basis may be evaluated using a cost function such as:

\[
C(B)
=
\alpha |B|
+
\beta \sum_F L_B(F)
+
\gamma RuntimeCost(B)
+
\delta StateCost(B)
\]

The constants are experiment-dependent.

SPK/v0 does not define universal values for them.

---

# 37. Initial target behaviors

The first experiments SHOULD attempt to construct at least:

```text
T1  Integrate-and-fire
T2  Leaky integrate-and-fire
T3  Temporal coincidence detection
T4  Ordered sequence detection
T5  Refractory-like behavior
```

Additional targets MAY later include:

```text
Adaptive threshold
Burst generation
Oscillation
Temporal integration window
Inhibition
Rate transformation
```

Targets are **behaviors**, not primitives.

Their presence in this list SHALL NOT imply that dedicated SPK operators should exist for them.

---

# 38. Search strategy

The initial search SHALL prefer exhaustive enumeration over learned search.

Suggested progression:

```text
program length <= 4
program length <= 5
program length <= 6
```

At every level:

1. generate well-formed programs;
2. execute on the test corpus;
3. compute signatures;
4. cluster equivalent candidates;
5. search for counterexamples;
6. apply proven rewrite rules;
7. retain canonical representatives where possible.

Agents and machine learning SHALL be introduced only after this deterministic pipeline exists.

---

# 39. Well-formedness

SPK/v0 permits syntactically legal but potentially useless programs.

For example:

```text
EMIT
```

without a previous `CMP` emits nothing because:

\[
g=false
\]

at batch entry.

Likewise:

```text
RESET
```

without a true guard performs no state change.

The search system MAY later introduce grammar rules to eliminate obviously sterile programs.

Such pruning rules SHALL be documented separately from semantic rules.

---

# 40. No implicit neural semantics

SPK operators SHALL NOT contain hidden concepts such as:

```text
neuron
synapse
membrane
axon
firing rate
biological excitation
```

unless explicitly introduced by a higher abstraction layer.

For example:

```text
ACC
```

means accumulation.

It does not mean:

```text
synaptic integration
```

Biological interpretations may be mapped onto SPK programs, but they are not part of primitive semantics.

---

# 41. No privileged model

SPK/v0 does not assume that:

```text
LIF
```

or any other established neuron model is fundamental.

If:

```text
ACC
DECAY
CMP
EMIT
RESET
```

happens to reproduce LIF-like behavior, LIF is treated as a macro-level composition.

Conversely, if experiments show that some commonly used dynamic cannot be represented efficiently with the candidate basis, the basis must be reconsidered.

---

# 42. Algebraic questions

SPK/v0 is designed to make the following questions experimentally accessible.

### Closure

Which operator families are closed under composition?

### Associativity

For which compositions does:

\[
(A\circ B)\circ C
=
A\circ(B\circ C)
\]

hold?

### Commutativity

Which operators commute?

\[
A\circ B
=
B\circ A
\]

### Identity

Which identity elements exist?

### Idempotence

For which operators:

\[
A\circ A=A
\]

holds?

### Distributivity

Are there useful relations such as:

\[
D(M(A,B))
=
M(D(A),D(B))
\]

?

### Redundancy

Can one primitive be expressed by compositions of others?

### Normal forms

Can equivalent programs be reduced to canonical representatives?

### Minimal generators

Does a compact generating basis exist?

---

# 43. Timing algebra hypothesis

One research hypothesis is that event transformations may form a structure distinct from state transformations.

Candidate event-side primitives:

\[
MERGE,\ DELAY
\]

operate primarily on:

\[
\mathcal E
\]

and may exhibit algebraic relations related to timed-event systems or semiring-like structures.

This hypothesis SHALL be tested rather than assumed.

---

# 44. State algebra hypothesis

Candidate state-side primitives:

\[
ACC,\ DECAY,\ CMP,\ RESET
\]

operate on:

\[
\mathcal X
\]

while:

```text
EMIT
```

maps state/control conditions back into events.

Conceptually:

\[
\mathcal E
\xrightarrow{ACC}
\mathcal X
\]

and:

\[
\mathcal X
\xrightarrow{EMIT}
\mathcal E
\]

This event/state dual structure is provisional.

---

# 45. Open questions

SPK/v0 intentionally leaves the following unresolved.

### Q1

Is `MERGE` an actual primitive, or merely graph composition syntax?

### Q2

Is `EMIT` computationally fundamental, or only an output boundary operation?

### Q3

Can `RESET` be expressed using other state transformations?

### Q4

Should `DELAY` operate on complete streams, individual channels, or both?

### Q5

Is exponential `DECAY` too semantically rich to count as elementary?

Possible future alternatives include a simpler linear leak.

### Q6

Does `CMP` contain too much logic for a primitive?

### Q7

Should state be restricted to one scalar permanently, or only during algebra discovery?

### Q8

Do event and state operations belong to one algebra or to interacting algebras?

### Q9

Which equivalence relation is most meaningful for physical neuromorphic hardware?

### Q10

Does a hardware-independent minimal basis exist at all?

---

# 46. Evidence levels

Every claimed SPK property SHALL be assigned one of four evidence levels.

```text
SPECIFIED
```

True by semantic definition.

```text
TESTED
```

Observed over a finite test domain.

```text
PROVEN
```

Established symbolically or formally.

```text
CONJECTURED
```

Suggested but neither proven nor sufficiently tested.

These labels SHALL NOT be conflated.

---

# 47. Initial implementation requirements

The first runtime implementation SHALL support:

```text
integer timestamps
integer channels
event multiplicity
batch execution
one scalar persistent state
one transient Boolean guard
deterministic output
all seven SPK/v0 operators
```

The implementation SHALL NOT initially require:

```text
NumPy
PyTorch
GPU support
neural-network frameworks
neuromorphic hardware
```

---

# 48. Required first tests

The minimum test suite SHALL include:

### Event ordering

Different ordering of coincident events produces identical execution.

### Multiplicity

Two identical coincident events remain two events.

### Delay identity

\[
DELAY_0(S)=S
\]

### Delay composition

\[
DELAY_a(DELAY_b(S))
=
DELAY_{a+b}(S)
\]

### Merge commutativity

\[
MERGE(A,B)=MERGE(B,A)
\]

### Merge associativity

\[
MERGE(MERGE(A,B),C)
=
MERGE(A,MERGE(B,C))
\]

### Delay distribution

\[
DELAY_d(MERGE(A,B))
=
MERGE(DELAY_d(A),DELAY_d(B))
\]

### Accumulation multiplicity

Two accepted events contribute twice.

### Guard reset

The transient guard returns to `false` at every new timestamp.

### Conditional emit

`EMIT` produces output only when the guard is true.

### Conditional reset

`RESET` modifies state only when the guard is true.

### Determinism

Repeated execution of the same program and input produces identical results.

---

# 49. First milestone

SPK/v0 reaches its first experimental milestone when the repository contains:

```text
formal SPK/v0 specification
deterministic runtime
unit tests
property-based tests
five target behaviors
program enumerator
empirical signature generator
equivalence clustering
counterexample search
```

and exhaustive exploration is possible for:

\[
L(P)\le4
\]

over a finite parameter domain.

---

# 50. Scientific discipline

The project SHALL distinguish at all times between:

\[
\text{observed}
\]

\[
\text{conjectured}
\]

and:

\[
\text{proved}
\]

A compact pattern found by search is not automatically an algebraic law.

Failure to find a counterexample is not proof.

Repeated emergence of a macro is not evidence that it is fundamental.

A familiar biological interpretation is not evidence that an operator is necessary.

The preferred research strategy is:

\[
\boxed{
define
\rightarrow
execute
\rightarrow
compare
\rightarrow
falsify
\rightarrow
reduce
}
\]

Only after this process should higher-level neural learning be introduced.

---

# 51. Versioning rule

Changes to primitive semantics require a new semantic version.

For example:

```text
SPK/v0.1
SPK/v0.2
```

Results obtained under one semantic version SHALL NOT automatically be considered valid under another.

The semantic specification is part of the experiment.

---

# 52. Current candidate model

The current working hypothesis is:

\[
B_0=
\{
MERGE,
DELAY,
ACC,
DECAY,
CMP,
EMIT,
RESET
\}
\]

with computation structured as:

\[
\boxed{
Stream\ Transformation
\rightarrow
Event\ Batching
\rightarrow
State\ Transformation
\rightarrow
Conditional\ Event\ Emission
}
\]

Whether this structure survives experimentation is intentionally unknown.

---

# 53. Evidence register

This section records the current evidence status of algebraic and semantic
properties investigated by SPK/v0.

The register distinguishes strictly between:

- `SPECIFIED`: true by definition of the SPK/v0 semantics;
- `TESTED`: verified over a finite automatically generated test domain;
- `PROVEN`: established by symbolic or formal reasoning;
- `CONJECTURED`: proposed but not yet sufficiently verified.

## 53.1 Event representation

| Property | Status |
|---|---|
| Event timestamps are non-negative integers | SPECIFIED |
| Event channels are non-negative integers | SPECIFIED |
| Spike trains preserve event multiplicity | TESTED |
| Spike trains have deterministic canonical ordering | TESTED |
| Input ordering does not affect canonical spike train representation | TESTED |
| Simultaneous events are grouped into one event batch | TESTED |

## 53.2 State semantics

| Property | Status |
|---|---|
| State contains one persistent scalar register `x` | SPECIFIED |
| Guard is Boolean | SPECIFIED |
| Guard is reset at the beginning of every event batch | TESTED |
| Persistent scalar state survives batch transitions | TESTED |

## 53.3 SPK/MERGE

Let:

\[
A \oplus B = MERGE(A,B)
\]

The following properties are currently observed.

### Commutativity

\[
A \oplus B = B \oplus A
\]

**Status:** TESTED

### Associativity

\[
(A \oplus B) \oplus C
=
A \oplus (B \oplus C)
\]

**Status:** TESTED

### Identity

Let:

\[
0_{\mathcal E} = \varnothing
\]

Then:

\[
A \oplus 0_{\mathcal E} = A
\]

**Status:** TESTED

Therefore, under the current SPK/v0 semantics, the pair:

\[
(\mathcal E,\oplus)
\]

is a candidate commutative monoid.

This classification is currently:

**Status:** CONJECTURED

until the properties are established directly from the formal definitions
rather than only through finite testing.

## 53.4 SPK/DELAY

Let:

\[
D_t = DELAY_t
\]

### Identity delay

\[
D_0(S)=S
\]

**Status:** TESTED

### Delay composition

\[
D_a \circ D_b
=
D_{a+b}
\]

for:

\[
a,b\in\mathbb N_0
\]

**Status:** TESTED

### Distribution over merge

\[
D_t(A\oplus B)
=
D_t(A)\oplus D_t(B)
\]

**Status:** TESTED

This suggests that every delay operator:

\[
D_t
\]

acts as an endomorphism over the candidate event monoid:

\[
(\mathcal E,\oplus)
\]

This classification is currently:

**Status:** CONJECTURED

## 53.5 Current experimental result

At SPK/v0.0.1, the event-side structure currently observed is:

\[
(\mathcal E,\oplus,D)
\]

with:

\[
\oplus = MERGE
\]

and:

\[
D=\{D_t\mid t\in\mathbb N_0\}
\]

where experimental evidence currently supports:

\[
D_0=I
\]

\[
D_aD_b=D_{a+b}
\]

and:

\[
D_t(A\oplus B)
=
D_t(A)\oplus D_t(B)
\]

No claim of novelty or completeness is made.

The immediate next objective is to introduce the state-side operators and
determine which algebraic properties survive interaction between:

\[
\mathcal E
\]

and:

\[
\mathcal X
\]

## 53.6 SPK/ACC

For a batch \(B_t\), channel selector \(c\), and weight \(w\):

\[
ACC_{w,c}(x)
=
x+w\,count(B_t,c)
\]

The following properties are currently established.

### Multiplicity linearity

For \(n\) matching events:

\[
ACC_{w,c}(x)
=
x+wn
\]

**Status:** TESTED

### Guard preservation

`ACC` does not modify the transient guard.

**Status:** TESTED

## 53.7 SPK/DECAY

For:

\[
L_{\tau,\Delta}(x)
=
xe^{-\Delta/\tau}
\]

with:

\[
\tau>0
\]

the following properties are currently established.

### Zero elapsed-time identity

\[
L_{\tau,0}(x)=x
\]

**Status:** TESTED

### Temporal composition

\[
L_{\tau,a}
\circ
L_{\tau,b}
=
L_{\tau,a+b}
\]

because:

\[
xe^{-b/\tau}e^{-a/\tau}
=
xe^{-(a+b)/\tau}
\]

**Status:** PROVEN

### Guard preservation

`DECAY` does not modify the transient guard.

**Status:** TESTED

## 53.8 ACC/DECAY non-commutativity

Let one or more matching events contribute total increment:

\[
u=wn
\]

Then:

\[
DECAY(ACC(x))
=
(x+u)e^{-\Delta/\tau}
\]

while:

\[
ACC(DECAY(x))
=
xe^{-\Delta/\tau}+u
\]

Their difference is:

\[
u(e^{-\Delta/\tau}-1)
\]

Therefore:

\[
DECAY\circ ACC
\neq
ACC\circ DECAY
\]

in general.

They coincide only for degenerate cases such as:

\[
u=0
\]

or:

\[
\Delta=0
\]

**Status:** PROVEN

This is the first established SPK/v0 example where operator ordering changes
program semantics.

## SPK/v0 experimental canonicalization checkpoint

Status: **TESTED / EMPIRICAL**

This checkpoint records the first closed exhaustive experiment over the
current SPK/v0 state-operator subset.

### Search domain

Operator pool:

- `ACC(weight=0, channel=0)`
- `ACC(weight=1, channel=0)`
- `ACC(weight=2, channel=0)`
- `CMP(threshold=1)`
- `CMP(threshold=2)`
- `EMIT(channel_out=0)`
- `RESET(value=0)`

Program lengths:

\[
0 \le L \le 4
\]

Total syntactic programs:

\[
1 + 7 + 7^2 + 7^3 + 7^4 = 2801
\]

### Corpus refinement

The initial empirical corpus produced behavioral collisions that were
shown to be false equivalences.

A counterexample-guided refinement process was therefore applied.

The refined corpus contains:

\[
92
\]

samples.

Four additional counterexamples discovered by CEGAR separated several
previously merged empirical classes.

Examples included cases such as:

\[
ACC_4;CMP_1
\]

versus:

\[
ACC_3;CMP_1;ACC_1
\]

which are distinguishable for suitable negative initial states.

### Rewrite families currently implemented

The canonicalizer includes exact or semantically justified reductions
covering, among others:

- neutral accumulation:

\[
ACC_0 \Rightarrow I
\]

- adjacent accumulation fusion on the same channel:

\[
ACC_a;ACC_b
\Rightarrow
ACC_{a+b}
\]

- overwritten comparisons:

\[
CMP_a;CMP_b
\Rightarrow
CMP_b
\]

when no intervening operation reads the guard;

- overwritten resets;

- removal of `EMIT` and `RESET` when the guard is known false;

- dead comparison elimination by guard liveness;

- repeated comparison elimination when persistent state has not changed;

- commutation of `EMIT` across compatible state operators;

- removal of shadowed resets;

- limited forward abstract interpretation of state constraints produced
  by `CMP` followed by guarded `RESET`.

In particular, for:

\[
CMP_\theta;RESET_r
\]

with:

\[
r < \theta
\]

the canonicalizer can infer:

\[
x < \theta
\]

after the guarded reset, independently of the branch taken.

### Exhaustive result

For all 2801 syntactic programs in the search domain:

\[
2801
\rightarrow
223
\]

distinct canonical forms were obtained.

The refined empirical corpus also distinguishes exactly:

\[
223
\]

behavioral classes.

Therefore:

\[
\boxed{
2801
\rightarrow
223
\rightarrow
223
}
\]

Measured ratios:

\[
\frac{2801}{223}
\approx
12.561
\]

and:

\[
\frac{223}{223}
=
1.000
\]

No empirical semantic-preservation violations were observed between any
program and its canonical form:

\[
\boxed{
0\text{ observed violations}
}
\]

### Interpretation

This result does **not** prove that the rewrite system is mathematically
complete for SPK/v0.

It establishes the narrower result that, for the explicitly explored
operator pool, parameter set, program depth and refined test corpus:

> every behavioral equivalence currently observed is represented by the
> same canonicalization partition.

Equivalently, there are no remaining unexplained empirical equivalence
collisions in this finite experimental domain.

This is therefore recorded as an **empirically complete normal form on
the explored SPK/v0 domain**, not as a proof of global completeness.

### Evidence status

- exhaustive enumeration of the declared finite domain: **TESTED**
- program-to-canonical semantic preservation on corpus v2: **TESTED**
- canonical forms: `223`
- empirical behavioral classes: `223`
- observed preservation violations: `0`
- global rewrite-system completeness: **NOT PROVEN**
- completeness beyond program length 4: **NOT TESTED**
- completeness after introducing additional operators such as `DECAY`:
  **NOT TESTED**


## SPK/v0 temporal canonicalization checkpoint

Status: **TESTED / EMPIRICAL**

The state-algebra experiment was extended with:

\[
DECAY(\tau=2)
\]

while keeping the maximum program length:

\[
L \le 4
\]

### Search domain

The operator pool contains 8 instantiated operators.

Total syntactic programs:

\[
1 + 8 + 8^2 + 8^3 + 8^4
=
4681
\]

### Numerical semantics

Introducing exponential decay exposed differences between exact real
arithmetic and IEEE-754 execution.

Raw execution showed 97 apparent canonicalization violations, but all
were caused exclusively by floating-point rounding:

- output mismatches: 0
- guard mismatches: 0
- maximum absolute state difference:
  approximately \(1.78\times10^{-15}\)
- maximum observed difference:
  2 ULP

Raw observations therefore remain available for diagnostics, while
empirical signatures use an explicit deterministic numerical
normalization policy.

This numerical normalization is part of the experimental observation
model and is not identified with equality over the mathematical reals.

### Temporal counterexample refinement

A temporal counterexample-guided refinement phase expanded the corpus
from 92 to 98 samples.

Candidate states were generated around analytically relevant threshold
preimages of the form:

\[
x =
\theta e^{n\Delta t/\tau}
\]

This separated false empirical equivalences caused by insufficient
coverage of states above thresholds after one or more decay operations.

### Additional temporal rewrite properties

The canonicalizer now includes temporal/state facts such as:

\[
DECAY_\tau;RESET_0
\equiv
RESET_0;DECAY_\tau
\]

when the guard is unchanged.

It also propagates positive strict upper bounds through exponential
decay.

If:

\[
x<U,\qquad U\ge0
\]

then after:

\[
x' = x e^{-\Delta t/\tau}
\]

the same strict upper bound remains valid:

\[
x'<U.
\]

This permits context-sensitive movement of a comparison already known
to be false across `DECAY`.

Importantly, this is not a general commutation rule:

\[
CMP;DECAY
\not\equiv
DECAY;CMP
\]

without the required state constraint.

### Exhaustive result

For the complete finite search domain:

\[
4681
\]

syntactic programs reduce to:

\[
548
\]

canonical forms.

The refined temporal corpus distinguishes exactly:

\[
548
\]

empirical behavioral classes.

Therefore:

\[
\boxed{
4681
\rightarrow
548
\rightarrow
548
}
\]

with:

\[
\frac{4681}{548}
\approx
8.542
\]

and:

\[
\frac{548}{548}
=
1.000.
\]

Observed semantic-preservation violations:

\[
\boxed{0}
\]

Residual ambiguous classes:

\[
\boxed{0}
\]

### Interpretation

Within the explicitly explored domain:

- all syntactic programs have been exhaustively enumerated;
- canonicalization preserves all tested observations;
- counterexample-guided refinement found no remaining unexplained
  behavioral collisions;
- every resulting canonical form occupies a distinct empirical class.

This establishes an **empirically complete temporal normal form for the
current finite SPK/v0 domain**.

It does not prove completeness for:

- arbitrary program depth;
- arbitrary real-valued parameters;
- additional decay constants;
- multiple event channels with independent accumulators;
- the full SPK event algebra;
- continuous-time semantics.

## Empirical state-algebra closure through depth 5

The SPK/v0 state algebra has been exhaustively enumerated over the
current finite operator instantiation:

- ACC(0), ACC(1), ACC(2)
- DECAY(tau=1), DECAY(tau=2)
- CMP(1), CMP(2)
- EMIT(0)
- RESET(0)

with program length:

    0 <= L <= 5

The syntactic search space contains:

    66430 programs

After canonicalization:

    4633 canonical forms

On the refined depth-5 corpus:

    4633 empirical runtime classes

Therefore:

    syntactic programs       66430
    canonical forms           4633
    empirical classes         4633
    ambiguous classes            0
    residual excess forms        0

This is an empirical closure result over the declared finite domain,
not a proof of global completeness.

### Depth-5 discoveries

Increasing the search depth from 4 to 5 exposed new identities that
were not observable in the shorter domain:

1. threshold / EMIT control-flow identities;
2. threshold / RESET subsumption identities;
3. mixed EMIT / RESET threshold partition identities;
4. a context-sensitive temporal rewrite derived from:
   - a strict state upper bound,
   - accumulated decay rate,
   - discrete integer time.

The depth-5 search also exposed a distinction between:

    algebraic semantics over the reals

and:

    IEEE-754 runtime semantics.

Consecutive DECAY fusion is exact algebraically when parameterized by:

    lambda = 1 / tau

with:

    lambda_eff = sum(lambda_i)

but is not universally IEEE-safe near a CMP threshold because different
floating-point evaluation paths may differ by sub-ULP amounts that CMP
can make observable.

Rewrite validity is therefore tracked separately for algebraic and
runtime semantics.

### Current checkpoint

Depth <= 4:

    7381 -> 973 -> 973

Depth <= 5:

    66430 -> 4633 -> 4633

The state-algebra exploration is considered closed for the current
finite operator domain through depth 5.

Further increases in brute-force depth are deferred in favor of
expanding the algebra along an independent dimension.

## Event algebra

The SPK/v0 event-side grammar is:

    E ::= EMPTY
        | variable
        | MERGE(E, E)
        | DELAY(k, E)

where:

    k ∈ N0

and SpikeTrain semantics preserve event multiplicity.

### Normal form

Every event expression has a normal form represented by a finite
multiset of atoms:

    (variable, accumulated_delay)

The normalization is defined recursively:

    NF(EMPTY)
        = {}

    NF(v)
        = {(v, 0)}

    NF(MERGE(A, B))
        = NF(A) multiset-union NF(B)

    NF(DELAY(k, A))
        = shift(k, NF(A))

where:

    shift(k, {(v, d)})
        = {(v, d + k)}

with multiplicity preserved.

Therefore the normal form directly captures:

    MERGE commutativity
    MERGE associativity
    EMPTY identity
    DELAY(0) identity
    DELAY composition
    DELAY distribution over MERGE

### Semantic preservation

The normal form preserves SpikeTrain semantics by structural induction
over the event-expression grammar.

EMPTY maps to the empty SpikeTrain.

A variable maps to its assigned SpikeTrain.

MERGE corresponds to finite multiset union.

DELAY(k) translates every event timestamp by k.

Therefore:

    eval(E, rho)
        =
    eval(NF(E), rho)

for every expression E and environment rho.

### Completeness

For any finite variable set V choose an injective channel assignment:

    channel : V -> N0

and the environment:

    rho(v) = {(0, channel(v))}

Under this environment, every normal-form atom:

    (v, d)

produces exactly:

    (d, channel(v))

Because the variable-channel mapping is injective and event
multiplicity is preserved, two distinct normal-form multisets produce
distinct SpikeTrains.

Therefore:

    E ≡ F
        iff
    NF(E) = NF(F)

for the current SPK/v0 event algebra.

Thus the quotient event algebra is isomorphic to the finite multisets:

    M_f(V × N0)

with MERGE as multiset addition and DELAY(k) as translation of the
N0 component.

This result is structural and is not limited to the finite
enumeration depth used by the experiment.

### Experimental confirmation

The v1 enumerated domain used:

    variables: A, B, C
    delay constants: 0, 1, 2
    maximum AST nodes: 5

Results:

    syntactic expressions:                  1636
    behavioral classes before normalization: 140
    canonical normal forms:                  140
    behavioral classes after normalization:  140
    semantic preservation violations:          0
    ambiguous canonical classes:               0
    residual excess forms:                     0

The finite experiment therefore agrees with the structural result:

    1636 -> 140 -> 140


## SPK/Core Algebra v0 finite closure

Declared finite domain:

- Core unsigned integer state
- nonnegative ACC weights
- instruction pool:
  - ACC(1,ch0)
  - ACC(1,ch1)
  - CMP(1)
  - CMP(2)
  - EMIT(7)
  - RESET(0)
- syntactic program length <= 4

Method:

- structural canonicalization
- ordered-state canonicalization
- CEGAR refinement
- independent semantic-preservation verification

CEGAR added two separating samples:

- x0=2, events=((0,1),(0,1))
- x0=0, events=((0,1),(0,1))

Final checkpoint:

    1554 syntactic programs
      -> 239 canonical programs
      -> 239 empirical behavioral classes

Refined corpus size: 434 samples.

Final properties:

- canonical/behavior ratio = 1.000000
- ambiguous canonical classes = 0
- residual excess = 0
- semantic preservation violations = 0

Status:

This is a finite closure result for the declared Core v0 domain.
It is not a claim of global completeness for arbitrary SPK/Core
programs, instruction parameters, depths, or numerical domains.

## SPK/Core Temporal Algebra v0 finite closure

Temporal Core basis used in the finite experiment:

- SHIFT_DECAY(1)
- ACC(1,ch0)
- ACC(1,ch1)
- CMP(1)
- CMP(2)
- EMIT(7)
- RESET(0)

Maximum syntactic program length:

    4

Total syntactic programs:

    2800

Method:

- structural canonicalization
- ordered unsigned-state algebra
- temporal rewrite algebra
- CEGAR corpus refinement
- independent source-to-canonical preservation verification

Temporal CEGAR refinements:

    x0=4,  events=((1,0),(1,0),(1,1))
    x0=3,  events=((1,1),)
    x0=14, events=((1,1),)

Final result:

    2800 syntactic programs
      -> 572 canonical programs
      -> 572 empirical behavioral classes

Final properties:

- canonical/behavior ratio = 1.000000
- ambiguous canonical classes = 0
- residual excess = 0
- unresolved behavioral pairs = 0
- semantic preservation violations = 0

Status:

This establishes finite closure for the declared SPK/Core Temporal v0
domain and observation corpus.

It does not establish global completeness for arbitrary program depth,
instruction parameters, state widths, thresholds, channels or temporal
domains.
