# SPK 24m - Compiler / Network / Observer / Evidence integrated reference v0

**Status: INTEGRATION PASS (2026-10-16, finite reference scope).**
**Baseline:** `0f4a020` (24l accepted). This patch adds four new files.

## Scope and preserved contracts

The v0 integrated **network** path is:

`versioned network IR -> frozen compile_network_ir_v0 -> canonical compilation manifest -> frozen loads_compilation_manifest_v0 -> frozen run_network_v0 -> on_batch/on_route -> canonical evidence -> independent replay`.

The source is versioned declarative Network IR, not a prepared single-root
`OwnedSharedEventCycleStateV0`. The code **does not** route emitting or
multi-node network execution through 24j's single-root, output-free runtime
host. The frozen Network runtime remains the authoritative reference for
multi-node emission and routing. No API or semantics are modified in Core,
Network, Compiler, architecture, k24b, 24d–24l.

## Concrete witness

The local fixture contains two neurons A and B, each with:
`ACC(channel=0, weight=1) -> CMP(threshold=1) -> EMIT(channel=7) -> RESET(0)`.
A receives one initial event at timestamp 2. Three directed A(7)->B(0)
edges have delays 3, 2 and 2. Expected results, independently asserted:

- exactly four processed events, three processed batches;
- A emission at t=2 and B emissions at t=4, t=5;
- two B terminal outputs at t=4, t=5;
- three routing observations, including duplicate edges at t=4;
- three batch observations, including input multiplicity `(0,0)` at B/t=4;
- full equality of frozen runtime results with observer absent or present;
- equality of source-network and manifest-reconstructed execution.

The compiler additionally validates architecture, per-PE placement and static
resource admission. The fixture explicitly has two processing elements.

## Replay JSON boundary correction (accepted)

The first real `fwork` gate exposed 9 positive-case failures (30 tests passed),
all at `verify_and_replay_v0()`'s equality between the Python execution
payload and the parsed JSON receipt. `dataclasses.asdict()` preserves nested
tuples, whereas JSON arrays decode to Python lists. Native and wire objects
thus differed even when the serialized content was identical.

The adapter now normalizes both the observed runtime result and the direct
source result through canonical JSON encoding/strict decoding before checking
the result oracle or sealing/replaying an artifact. This changes neither the
frozen runtime nor the receipt schema; replay still requires full equality of
the JSON-domain result and observations and still rejects altered/rehashed
receipts. Two additional regression tests cover nested tuple conversion and
native-vs-wire payload equivalence. The correction is accepted by the complete fwork integration gate.

## Canonical evidence and replay

`search/spk_24m_compiler_network_evidence_v0.py` emits canonical UTF-8 JSON:

- schema/version `spk-compiler-network-evidence/v0`, `0`;
- exact canonical compilation manifest JSON and SHA256 over its bytes;
- finite run limits (`max_batches`, `max_events`);
- **full** network execution result (emissions, terminal outputs, neuron
  states, counters), not merely a successful/failed status;
- `on_batch` and `on_route` observations, with event multiplicity preserved;
- outer domain-separated SHA256 over the canonical payload.

The verifier checks schema, duplicate JSON keys, canonical encoding, both
checksums, manifest consistency and **reexecutes the frozen network** from the
embedded manifest. It compares the full result and observation arrays to the
supplied artifact. Rehashing a fabricated state, emission, route, delay or
batch without a corresponding execution must fail replay.

There is **no claimed cryptographic authentication**: a malicious editor can
replace both source and outcome with another internally consistent scenario
and recompute every hash. Evidence is deterministic/replayable for a trusted
consumer and current software dependencies; it is not a signed receipt or
software-independent formal proof.

## Differential scope, S3-S5 acceptance

| Original criterion | What this gate proves | Unproven |
| --- | --- | --- |
| S3 compiler-to-runtime | Declarative IR compiled, serialized, reconstructed and executed | Adoption by 24j host for routed emission deliberately excluded |
| S3 reference network | Two emitting nodes, positive delays, parallel routes, explicit output oracle | Larger topologies, all resource-exhaustion interleavings |
| S4 non-interference | Complete frozen result equals observer-on/off for source fixture; existing learning-observer regression | Arbitrary observers with side effects; universal equivalence |
| S5 differential | Source-direct vs manifest-reconstructed run; fixed independent hand-authored output oracle | Two independent execution engines are **not** compared |
| S5 reproducibility | Canonical full result and observation artifact, subprocess seed variation, checked replay | Authenticated input lineage, persistent/external trace store |

**No phase percent is automatically promoted** on creation or on a green
suite. A subsequent review must count accepted subcriteria relative to the
original roadmap and declare remaining scope, rather than tallying tests.

## Run one gate

```bash
bash search/spk_24m_final_gate_v0.sh
```

The gate runs focused tests, related frozen regressions, two separate Python
processes with different hash seeds, replay of the evidence, an independent
expected-output check, then the full repository suite. It writes evidence
only into a private temporary directory, does not commit or tag anything.

## Known limits / exclusions

No new service scheduler, learning, back-validation, physical I/O, MQTT,
distributed authority, durable recovery, new Core operations or network
semantics. Observer callbacks are data-capture hooks, not a safety sandbox;
side-effecting observer code is outside this claim. A failed finite execution
does not publish a successful evidence artifact.

**Checkpoint after real gate:** record targeted and full-suite pass counts,
manifest and evidence hash, frozen-module diff check, and S3/S4/S5 estimate
with explicitly scoped acceptance. Until then baseline S1=100%, S2=100%,
S3=60%, S4=0%, S5=0%, equal-weight total 52%.

## Certified integration gate - 2026-10-16

Baseline: 0f4a020.

- 24m tests: 41/41 PASS.
- Compiler/Network integration: 81/81 PASS.
- Complete repository: 2679/2679 PASS.
- Independent process replay: PASS.
- Observer ON/OFF equivalence: PASS for reference fixture.
- Frozen-source boundary: PASS.
- Evidence SHA256:
  ed72f5b137a0350b63970aaaf18eb1c66cc6ee9287f8c7f17d760fb1a68a9412

Acceptance is limited to the finite reference execution.

S3: Compiler-to-Network reference integration demonstrated.
S4: Non-interfering observation demonstrated for the finite fixture.
S5: Canonical evidence and negative replay tests demonstrated;
independent second-engine differential equivalence remains open.
