# SPK 24o: Extended Semantic Coverage and Observer Noninterference v0

**Status: INTEGRATION PASS (2026-10-16, 216-case finite domain).**

Baseline: `5cff26d` (SPK 24n independent differential oracle accepted).

## 1. Functional objective

Expand the finite proof surface of S3 (Network IR and execution), S4
(observer noninterference and observation correspondence), and S5
(independent two-engine differential, metamorphic properties, reproducible
full-corpus evidence). No new scheduling or owner-custody layer is introduced.

The existing Core, Network, Compiler, Architecture and Simulator implementations
remain unchanged. The 24n operational interpreter remains independent and
unmodified. The 24o corpus generator imports only the 24n primitive dataclasses
and Python standard library. The adapter imports frozen libraries for input
construction and actual execution, never for expected execution.

## 2. Declared bounded corpus

The corpus comprises **216 cases = 6 instruction profiles x 6 finite DAGs x
6 event schedules**, generated deterministically and identified by unique
`profile/graph/events` names. Each network contains three named neurons A/B/C.

Instruction profiles: three relays; threshold with persistent state; decay;
dual emission (routed and terminal channels); overwritten guards; and
fractional-bit accumulation. All use the previously admitted 24n Core fragment
with 8-bit state. Graphs include no edges, one hop, a chain, parallel edges,
fan-out and a delayed reconvergent diamond. Inputs cover silence, time zero,
duplicates at a single timestamp, separated times, interleaving across neurons,
and distinct channels at the same timestamp.

The corpus fingerprint is:

`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`

Only successful executions within fixed limits (`max_batches=128`,
`max_events=4096`) are included. Overflow, unsupported instructions, resource
arbitration, negative or zero-delay edges and indefinite cyclic execution are
**not** silently classified as valid executions.

This is exhaustive over the *declared* Cartesian fixture matrix, not over all
legal SPK programs, networks, configurations or event histories.

## 3. Tests and independent checks

For **every one of 216 cases**, the frozen Network v0 executes with and without
an observer. The full runtime result objects must be equal, not merely output
counts. All emission/terminal-output multiplicities, terminal states, event and
batch counts, and batch/route observations must match the independent 24n
interpreter via the full-field canonical projection.

For every case, reversing the initial-event input order must preserve the
canonical result. This is a metamorphic requirement concerning event input
ordering, not observer ordering. For pure unit relay profiles, translating
external timestamps by a nonnegative constant must translate emission and
terminal timestamps accordingly. Where all external events are on channel 0,
the separate algebraic DAG path-support oracle must obey the same covariance.
The path oracle is **not** extended to unmatched input channels.

Additional explicit oracles check idle executions, parallel routing
multiplicity, exact success/failure execution limits, unsupported instructions,
and failed observation comparisons under tampering.

**S3 scope:** Network IR encoding/decoding is round-tripped on 36 expanded
configurations and its execution compared; the frozen Compiler→manifest→Network
reference from 24m/24n is exercised separately as regression and a bridge test.
24o does not claim that every one of the 216 cases has passed resource
admission through the Compiler, nor that multineuron execution uses the
single-root ApplicationRuntimeHost 24j.

## 4. Evidence and replay

The canonical 24o JSON evidence includes corpus schema and SHA-256, all case
identifiers, per-case canonical output fingerprint, processed counts, emission
and route counts, and an explicit noninterference assertion. Verification
recomputes **every case**, from the local versioned corpus generator using
both frozen Network v0 and the 24n independent oracle. It rejects modifications
to results or corpus metadata even if the outer SHA-256 is recomputed.

Two independent Python processes must produce byte-identical artifacts and
both pass replay. SHA-256 authenticates neither code publishers nor sensor
data origins; comparing results from the same local code version is not proof
of general semantic correctness or crash-safe persistence.

## 5. Gate and promotion

Run on `fwork`:

```bash
bash search/spk_24o_final_gate_v0.sh
```

Six checks:
1. Pure interpreter and metamorphic tests.
2. Frozen Network, observer and independent-oracle extended tests.
3. Two independent process artifacts, byte-level equality and full replay.
4. Previous Compiler/Network/24m/24n regression suite.
5. Entire repository regression.
6. No changes in frozen directories, clean staging and patch whitespace.

Failure in any of these remains a failed gate; do not tag or commit until the
cause is understood. The test counts on `fwork` are the acceptance evidence.

## 6. Roadmap rubric

Previously certified estimated completion:

| Phase | Prior | 24o contribution | Still not demonstrated |
|---|---:|---|---|
| S1 | 100% | none | closed |
| S2 | 100% | none | closed |
| S3 | 80% | broader Network IR/runtime fixtures | unified multineuron host |
| S4 | 60% | 216-case observer noninterference | general coverage over all observers and execution domains |
| S5 | 75% | full-corpus independent differential/replay | remaining instruction and temporal domains |

Baseline project total = `(100+100+80+60+75)/5 = 83%`, equal weight. No
new percentage is *certified* merely by creating these files. After the real
gate, reassess the rubric explicitly without equating test count to proof.

## 7. Noninterference and source hygiene

The package includes only 24o files; it must never overwrite Core, Network,
Compiler, Architecture, k24b, 24d-24n, or the following pre-existing untracked
files: `search/core_temporal_depth5_v1.py`,
`search/core_temporal_quotient_alignment_v0.py`, `spk_24d_collect.py`.

## 8. Core IR normal-form admission correction (accepted)

The original `guard_overwrite` primitive program deliberately contains two
adjacent CMP instructions: CMP(1), CMP(3). The second overwrites the first
without an intervening side effect. `NetworkNodeV0` correctly rejects this
non-normal form because frozen Core IR v0 requires runtime-normalized programs.

Only the 24o input adapter now replaces adjacent overridden comparisons with
the final comparison before constructing the frozen Network IR. The original
216-case corpus, its fingerprint and the independent 24n interpreter remain
unchanged. For each case, the 24o execution compares the frozen result both
against the independent interpretation of the admitted network and **against
the original primitive source**, preventing admission normalization from hiding
a semantic change. An explicit test covers every initial state 0..254 under
an 8-bit single-event scenario; no normalization is allowed to change the
final guard, emission or reset.

This is not a relaxation of frozen Core IR preconditions, and no frozen
component is modified. The correction passed the authoritative `fwork` gate; the original `guard_overwrite` profile remains in the corpus.

## 9. Certified fwork gate - 2026-10-16

Baseline: 5cff26d.

- Independent corpus tests: 23 PASS.
- Frozen Network / observer differential: 27 PASS.
- Complete corpus: 216 finite scenarios.
- Independent-process evidence replay: PASS.
- Previous Compiler/Network/24m/24n regression: 126 PASS.
- Full repository regression: 2777 PASS.
- Frozen-source and patch hygiene: PASS.

Corpus SHA256:
cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5

Evidence SHA256:
51abd66dc40493426dba66c3c5a56ee24761f567b1ca8d009659d07678446174

Roadmap engineering estimates:
S1=100%, S2=100%, S3=80%, S4=75%, S5=85%.
Total=88% (equally weighted), previous 83%, delta +5 pp.

S4 receives 15 additional points for expanded finite noninterference
coverage; S5 receives 10 additional points for extended differential
and replay coverage. Remaining points concern broader execution domains,
observer behaviors and unsupported semantic fragments.

These are bounded engineering acceptance results, not universal proofs.
