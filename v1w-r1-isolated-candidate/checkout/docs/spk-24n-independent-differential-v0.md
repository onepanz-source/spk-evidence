# SPK 24n - Independent Core/Network Differential Oracle v0

**Status: INTEGRATION PASS (2026-10-16, bounded domain).**

Baseline: `fd0fd32` (`SPK 24m compiler network observer evidence v0`).

## 1. Purpose and independence

S3/S4/S5 have a compiler-to-execution proof in 24m, but its direct-source
execution and manifest-reconstructed execution share `run_network_v0`.
Their equality cannot detect a common execution bug.

24n adds a **separate operational interpreter** in
`search/spk_24n_independent_oracle_v0.py`. This module imports **no** frozen
Core, Network, Compiler, Simulator or 24m code. Its executable semantics are
implemented with its own priority queue, per-neuron raw states, instruction
interpreter, channel-count batching and routing. In particular it does **not**
call `run_network_v0`, `run_core_v0`, or any frozen Core interpreter.

`search/spk_24n_differential_evidence_v0.py` is an adapter: it extracts primitive
configuration/program/network data from the admitted SPK objects and compares
the independent interpreter's results to supplied frozen-runtime results.
The shared Compiler manifest decoder validates **inputs**, not the expected
execution. The adapter may call the 24m envelope/replay validator as a separate
precondition, but **the oracle is never computed by 24m**.

A second independent mathematical check uses the relay path-delay recurrence
on finite DAGs. This calculation does not execute instructions or manipulate
an event queue, and tests 729 DAGs on four neurons.

## 2. Declared semantic domain

- Finite networks with unique node identifiers and nonnegative event times.
- Positive integer edge delays; cycles allowed only within execution budgets.
- Parallel edges retain their multiplicity; inputs of equal `(time,node)` are
  combined into one batch, with channels sorted while preserving occurrences.
- Core state: unsigned integer width 1..32 bits, fractional width below state
  width, initial raw state in range, last timestamp initially 0.
- Instructions: `CoreAcc`, `CoreCmp`, `CoreEmit`, `CoreReset`, `ShiftDecay`.
  `CMP` overwrites a fresh per-batch guard; `RESET` is guard-dependent.
  `ShiftDecay` uses the delta from the same neuron's previous batch.
- Each emission is routed on every matching edge; no matching edge makes it
  a terminal output. Produced events keep the originating batch timestamp.
- Executions must terminate below explicitly stated `max_batches` and
  `max_events`; unsuccessful overflows and unsupported instructions are
  **outside** the accepted success domain and cause a visible error.
- No proof is claimed for learning, back-validation, concurrent execution,
  dynamic buffer contention, architectural service scheduling or persistence.

The oracle is intentionally a **bounded subset**, not a new complete SPK
reference specification. Expanding its instruction or temporal domain requires
new tests and a new versioned contract.

## 3. Comparison and evidence

Compared fields:

1. full emission multiset, including timestamp, node, channel and duplicates;
2. full terminal-output multiset;
3. each neuron's `(id, raw, last_timestamp)`;
4. number of processed event occurrences and `(timestamp,node)` batches;
5. batch observations including channels, final raw, guard, output channels;
6. route observations including source, target, channels and causal delay.

Within one timestamp, order is not semantic; event and route multisets are
canonicalized without discarding multiplicity. The **entire field structure**
is still checked. Differences raise `DifferentialMismatchV0`, identifying the
first divergent class rather than printing only `PASS`.

The differential artifact holds the full 24m receipt, independent-oracle
projection and digest. Verification revalidates the 24m receipt and **reruns**
the independent interpreter; it rejects changes even when the outer checksum
is recalculated. SHA-256 alone is not a signature or trusted provenance.

The 24m artifact covers a representative compiled network, two relays,
positive delays 2/3 and a parallel edge. Further differential tests execute
729 four-node DAGs against frozen Network v0; local independent tests also
compare those DAGs to an unrelated algebraic path-support oracle. Stateful
threshold, decay, non-emitting nodes, multiplicities, empty input and finite
budget boundaries are included separately.

## 4. Verification plan

One command on the authoritative fwork checkout:

```bash
bash search/spk_24n_final_gate_v0.sh
```

Gate:

1. Independent interpreter and algebraic checks (no SPK imports).
2. Actual frozen Network v0 vs independent Core/event interpreter.
3. Two independent Python processes produce identical evidence, both replayed.
4. Previous Compiler/Network/Observer/24m regression tests.
5. Full repository test suite.
6. Whitespace, freeze boundary, Git staged-change check.

Status is only promoted after the real fwork gate. The installed package here
has partial frozen dependencies and cannot execute the complete gate.

## 5. Roadmap acceptance distinctions

| Phase | 24n evidence | Limit |
|---|---|---|
| S3 | Compiler manifest supplied to an independent operational execution model | finite admitted subset |
| S4 | Independent batch/route observation comparison | tested cases only; no proof for all observers |
| S5 | Independent-engine differential, 729 DAGs, negative mutation, reproducible artifacts | no universal equivalence; bounded domain |

**Previous certified roadmap estimates** remain S1=100%, S2=100%, S3=60%,
S4=0%, S5=0%; total 52%, equally weighted. These are not updated merely by
writing this implementation. Once the final gate is accepted, reassess the
original S3/S4/S5 acceptance obligations, keeping domain restrictions explicit.

## 6. Noninterference

No tracked changes are permitted in `spk_core`, `spk_network`, `spk_compiler`,
`spk_architecture`, or older simulator components. The pre-existing untracked
`search/core_temporal_depth5_v1.py`,
`search/core_temporal_quotient_alignment_v0.py`, and `spk_24d_collect.py`
remain excluded from any commit.

## 7. Accepted integration gate

Baseline: fd0fd32.

- Independent unit tests: 23 PASS.
- Frozen Network differential tests: 25 PASS.
- Algebraic relay DAG corpus: 729 configurations.
- Independent-process evidence/replay: PASS.
- Previous Compiler/Network regressions: 88 PASS.
- Complete repository regression: 2727 PASS.
- Whitespace/frozen-source boundary: PASS.

Manifest SHA256:
41eb6f71784670312e945944502d43adaa52dcfed886a1be494703214385ccdc

Oracle SHA256:
ee2f4bab0fa15de875861688473adc5eb47dc77416a517cffe0efd4b2aa8e86c

The verification is limited to the declared bounded domain.
It does not establish universal semantic equivalence.

## 8. Roadmap reassessment

Engineering completion rubric:

S3 = 80/100:
- Compiler-to-Network integration: 40/40.
- Routed multineuron reference execution: 40/40.
- Unified broader application-host integration: 0/20.

S4 = 60/100:
- Observer ON/OFF full-result equality on reference: 40/40.
- Independent observation correspondence: 20/20.
- Expanded noninterference corpus: 0/40.

S5 = 75/100:
- Independent bounded differential: 35/35.
- Negative and mutation tests: 20/20.
- Reproducible verified artifacts: 20/20.
- Extended semantic-domain coverage: 0/25.

S1 = 100%, S2 = 100%.

Total = (100+100+80+60+75)/5 = 83%.
Previous baseline = 52%; change = +31 percentage points.

Percentages are engineering estimates, not formal proofs.
No universal equivalence, distributed authority, learning
or architectural contention is claimed.
