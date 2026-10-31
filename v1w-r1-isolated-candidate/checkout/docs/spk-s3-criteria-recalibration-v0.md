# SPK Simulator/Compiler: S3 acceptance recalibration after 24k

**Status: CRITERIA REVIEW, NOT A NEW CERTIFIED PERCENTAGE.**
Baseline: `fe292dc`, 24k finite offline provider/launcher gate PASS on `fwork`
(2592 total tests, demo completed version 0 → 1). The 24l gate passed on fwork on 2026-10-16 (2638 regression tests).

## Normative baseline and completion logic

`docs/spk-execution-contract-v0.md` §8 identifies:

- **S1** Interface contracts and temporal assumptions (100% closed).
- **S2** Versioned network, strict Compiler v0 validation, deterministic
  serialization and source reconstruction (100% closed).
- **S3** **Compiler-to-runtime integration and reference network execution**.
- **S4** **Non-interfering execution observations**.
- **S5** **Differential/negative testing and reproducible execution artifacts**.

Do not treat the number of modules or pytest cases as phase completion. The
24d–24k sequence implements a valid *finite, one-root, output-free reference*
consumer, but the 24k demo starts from an SPK fixture which returns an
already-sealed `OwnedSharedEventCycleStateV0`. It does **not** demonstrate a
complete versioned declarative network source passed through Compiler v0 into
the same host and then into a representative multi-node emitting network.

## Evidence matrix

| Required capability | Existing evidence | Still necessary for broad acceptance |
| --- | --- | --- |
| S3 compiler-to-runtime | Frozen compiler manifest/conformance and source reconstruction suites; existing `run_network_v0` integration | Explicit tested path from versioned source to selected runtime/host with observable equivalent semantics |
| S3 reference execution | 24k complete root EVENT/P/S/Core/STATE_COMMIT (`EXIT 0`), 24k limited (`EXIT 3`) | Broader representative network execution including nontrivial routing/emission; compare to frozen `run_network_v0` where applicable |
| S4 noninterfering observations | Observer hooks documented (`on_batch`, `on_route`); 24d–24g read-only replay/audit | Matched observer-on/off executions with full result equivalence, not only digest of a summary |
| S5 differential and negative | Thousands of tests, existing historic differential suites; 24l introduces public-result fingerprint comparison | Persisted reproducible artifacts tied to canonical input/manifest and substantive differential executions across implementations |

## Percentage decision

S1=100%, S2=100%, S3=60%, S4=0%, S5=0%, total **52%** using
`(100+100+60+0+0)/5`. This is the *last formally certified roadmap estimate*.
The evidence demonstrates progress since that checkpoint, but a defensible
replacement percentage requires subdividing S3 by actual acceptance criteria
and proving coverage, especially Compiler→host and representative routed
execution. **Do not promote S3 solely because 24l passes.**

This is not saying S4 or S5 have seen no engineering work. They have partial
artifacts but are not accepted as phases under the original contract.

## Required next broad, nonfragmented cycle

After the complete 24l gate: implement and certify one integrated path from
canonical declarative network source through frozen Compiler into reference
execution; include nontrivial routing and emit cases where existing APIs can
support them. In the same gate, compare observer enabled/disabled results and
produce reproducible execution artifacts. This will create a meaningful
acceptance basis for updating S3/S4/S5 together.

Exclude learning, back-validation, physical hardware, distributed execution,
Core/Network/Compiler mutations and fabricated global single-writer claims.

## 24l acceptance update

24l closes the local reference source-pin, overlapping-process
exclusion and public-result reproducibility gate.

It does not close the original S3 Compiler-to-Runtime integration
or representative routed network execution criteria.

Certified roadmap estimates remain:
S1=100%, S2=100%, S3=60%, S4=0%, S5=0%.
Total=52%, equally weighted.
