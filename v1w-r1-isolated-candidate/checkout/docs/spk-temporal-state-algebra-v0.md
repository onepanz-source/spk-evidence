# SPK Temporal State Algebra v0

## 1. Scope

This document formalizes the temporal-state results obtained for
SPK/Core and SPK Network v0.

The principal fragment considered here consists of Core programs of
the form:

    ShiftDecay(k1)
    ShiftDecay(k2)
    ...
    ShiftDecay(kn)
    Q

where Q contains no ShiftDecay.

State is unsigned fixed-width integer state.

Network experiments additionally use:

- positive edge delays;
- discrete logical ticks;
- finite feed-forward networks;
- terminal-output observation.


## 2. Shift action

For non-negative integer state x define:

    sigma_k^d(x) = x >> (k*d)

where:

    k >= 0
    d >= 0

For unsigned integer right shift:

    (x >> a) >> b
        =
    x >> (a+b)

Therefore:

    sigma_k^a(
        sigma_k^b(x)
    )
        =
    sigma_k^(a+b)(x)

Thus elapsed time acts on Core state as a monoid action of:

    (N_0,+,0)


## 3. Fusion of prefix ShiftDecay instructions

Consider prefix instructions:

    ShiftDecay(k1)
    ...
    ShiftDecay(kn)

All instructions in one event batch observe the same elapsed delta.

Let:

    K = k1 + ... + kn

Then:

    (((x >> k1*delta)
        >> k2*delta)
        ...)
        >> kn*delta

equals exactly:

    x >> (K*delta)

Hence:

    ShiftDecay(k1);
    ...
    ShiftDecay(kn)

is temporally equivalent to:

    ShiftDecay(K)

for the shared batch delta.


## 4. Lazy temporal representation

The event-driven Core runtime stores:

    raw
    last_timestamp

When a new event batch arrives at time t, it computes:

    delta =
        t - last_timestamp

and a prefix decay block transforms state to:

    raw_event =
        raw >> (K*delta)

before Q executes.


## 5. Relative-age representation

Absolute time is unnecessary for the prefix-decay fragment.

The same transition can be represented by:

    (raw, age)

where:

    age =
        t_current - t_last_event

and:

    raw_event =
        raw >> (K*age)

For finite unsigned state, age can be saturated.

If:

    K > 0

then every state is annihilated once:

    K*age >= state_bits

Therefore an exact conservative saturation bound is:

    ceil(state_bits / K)


## 6. Effective-state representation

Relative age itself is also unnecessary for the prefix-decay fragment.

Define:

    effective_raw =
        raw >> (K*age)

Instead of retaining raw and age separately, evolve effective_raw as
logical time advances.

At an event batch, Q operates directly on effective_raw.

After one silent logical tick:

    effective_raw :=
        effective_raw >> K

Thus temporal evolution becomes an action on state rather than an
explicit state variable.


## 7. Prefix temporal absorption theorem

Let:

    P =
        ShiftDecay(k1);
        ...
        ShiftDecay(kn);
        Q

where Q contains no ShiftDecay, and let:

    K = sum(ki)

Then the lazy representation:

    (raw, age)

and the eager representation:

    effective_raw =
        raw >> (K*age)

produce identical execution of Q for every event batch.

Reason:

1. every prefix ShiftDecay observes the same batch delta;
2. the prefix shifts fuse to total rate K;
3. right-shift composition is exact:

       (x >> a) >> b
           =
       x >> (a+b)

4. therefore the eager state at event time equals the state produced
   by the lazy prefix decay;
5. Q consequently receives identical state and identical batch input.

Hence, within the declared fragment:

    (raw, age)
        ->
    effective_raw

is an exact temporal-state quotient.


## 8. Network projection

For a network of prefix-decay nodes, define:

    q(
        raw,
        age,
        pending
    )
        =
    (
        effective_raw,
        pending
    )

The finite R/D network experiment checked the commuting condition:

    q(delta_T(s,x))
        =
    delta_E(q(s),x)

together with:

    lambda_T(s,x)
        =
    lambda_E(q(s),x)

for every reachable temporal state and every declared input symbol.


## 9. Exact finite evidence

Declared R/D network space:

    108 typed networks

Temporal reachable states:

    14,428

Input symbols per state:

    2

Projection transition checks:

    28,856

Results:

    transition/output mismatches: 0
    projected/reachable state-space mismatches: 0
    canonical temporal/effective mismatches: 0

State-space reduction:

    temporal operational states:
        14,428

    effective operational states:
        2,374

    minimal semantic states:
        718

Therefore:

    14,428
        ->
    2,374
        ->
    718


## 10. Semantic age

Relative age can be semantically observable.

A finite witness was found with identical raw and pending state but
different relative ages:

    age 3
    age 1

A future input distinguished the states.

Therefore age cannot simply be discarded from the lazy
representation.

However, after projection to effective_raw, explicit age is no longer
required.

Thus:

    age is operationally relevant

does not imply:

    age must be represented explicitly


## 11. Absorption boundary

The simple effective-state quotient is not valid for arbitrary
placement of ShiftDecay.

Finite Core probes tested:

Supported:

    ShiftDecay(1); Q
    ShiftDecay(2); Q
    ShiftDecay(1); ShiftDecay(2); Q

Refuted:

    ACC; ShiftDecay; ...
    ACC; CMP; ShiftDecay; ...
    ACC; CMP; EMIT; ShiftDecay; ...
    ACC; CMP; EMIT; RESET; ShiftDecay

Across:

    32,256

concrete cases, the expected prefix/non-prefix classification had:

    classification errors: 0


## 12. Why non-prefix absorption fails

For an interleaving such as:

    ACC(w);
    ShiftDecay(k)

the lazy computation contains:

    (x + input) >> (k*delta)

whereas moving elapsed decay entirely into pre-event state produces a
different expression based on:

    (x >> (k*delta)) + input

In general:

    (x+y) >> m
        !=
    (x >> m) + y

Therefore the temporal action does not commute with arbitrary state
updates.

The same issue applies whenever ShiftDecay occurs after a batch
instruction whose current-batch effect would then become subject to
the elapsed-time decay.


## 13. Temporal algebra interpretation

For the prefix-decay fragment, elapsed time is best viewed not as
stored data but as an action:

    N_0 x State
        ->
    State

with:

    d . x =
        x >> (K*d)

and:

    0 . x = x

    (a+b) . x =
        a . (b . x)

Thus time forms an action of the additive monoid of non-negative
integers on Core state.


## 14. State hierarchy

The experiments establish the following hierarchy:

    absolute timestamp
        ->
    relative age
        ->
    bounded relative age
        ->
    effective state
        ->
    minimal semantic state

For the declared prefix-decay network fragment:

    absolute timestamp
        is unnecessary;

    explicit relative age
        is unnecessary after effective-state projection;

    effective state
        is sufficient operationally;

    behavioral minimization can quotient effective state further.


## 15. Epistemic status

Algebraically established for unsigned integer prefix shifts:

- right-shift temporal composition;
- fusion of prefix ShiftDecay rates;
- monoid action of elapsed time;
- correctness of effective-state representation for a prefix
  ShiftDecay block followed by a non-temporal suffix.

Experimentally and exhaustively established on the declared finite
R/D network domain:

- exact temporal/effective transition projection;
- equality of observable outputs;
- equality of reachable projected state spaces;
- equality of canonical minimal transducers.

Finite counterexamples establish that the same simple absorption
cannot be extended indiscriminately across non-prefix state
operations.

No universal claim is made for arbitrary interleaved temporal Core
programs or arbitrary SPK networks.
