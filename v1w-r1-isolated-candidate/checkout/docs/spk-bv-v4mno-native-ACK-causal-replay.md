# SPK Back Validation — v4m–v4o separate native ACK causal replay

Scope: **RESEARCH ONLY**. The frozen Architecture v1, SPK Core/Network,
Compiler and original `execute_live_v0e` are **not changed**. Three new
versioned research modules/scripts run an independent bounded execution branch.

## Exact question

The v4j–v4l shadow arbiter identified hypothetical PE donors but left their
forward/BV work as *unresolved causal debt*. Can a native-style logical
executor carry out concrete PE, O/E memory, link and in-flight ACK transport
services **and actually recompute downstream native events**, rather than
overlay a changed timeline onto the frozen original?

## v4m — executable reference and non-intervention parity

- An independent bounded research executor reruns native neuron computation,
  forward spikes, reverse BV packets and their shared logical-clock services.
- With **zero** injected ACK requests it must reproduce exact original native
  forward, feedback and resource payloads on all **18 signed native sources**.
- Its implementation and the native source are SHA-pinned. Source native
  snapshot hashes must match the signed v3tuv predecessor.

## v4n — exogenous synthetic ACK transport with causal recomputation

- A fixed synthetic request is derived from each signed v4jkl W4
  deadline-only/protect-forward reservation tick. This **is not** a fresh
  actor request computed from the changed replay.
- At each ready tick, the oldest request can use an actual simulated service:
  sender `PE0`, recipient `PE1`, one sender PE slot, two units of memory in
  domains O and E (one unit for each endpoint PE), one directional/fabric
  link credit, one bounded in-flight occurrence and a later ACK arrival.
- This experimental scheduling policy prioritizes synthetic ACK ahead of
  native forward and BV. It is intentionally **not** the frozen policy. Native
  work not served in the same tick remains pending and is **recomputed** from
  real inputs, neuron state and link/memory admission on subsequent ticks.
- Native forward emission, terminal timing, BV packet ancestry, delivery and
  resource timelines are generated afresh; no original event is silently
  marked as completed. The evidence is causal **conditional on exogenous
  request times**.

## v4o — signed matrix and negative proofs

The precomputed research gate is:

| Metric | Source-bound observation |
| --- | ---: |
| Exact original native non-intervention replays | 18 |
| Signed derived scenarios rerun | 72 |
| Exogenous ACK requests | 399 |
| Executed simulated ACK link grants and arrivals | 399 |
| Previous *hypothetical* v4jkl donors (not matched 1:1) | 291 |
| Scenarios with changed native forward trace | 59 |
| Scenarios with changed native BV trace | 48 |
| Scenarios with changed terminal emission timing | 59 |
| Scenarios with extended native completion horizon | 60 |
| Scenarios with changed final neuron raw-state value | 0 |

Controls: source SHA and canonical predecessor, original native hashes, all
72 source-context identities and signed shadow ledger recalculation, exact
zero-injection native parity, PE/O/E/link/in-flight conservation, ordered ACK
delivery, duplicate/forged PE and identity rejection, forced insufficient
memory and horizon rejection, source/code SHA drift refusal, create-only
output and deterministic replay. Test failures **never** count as completion.

## Essential limits (do not promote the results)

1. The signed source actor row remains **exogenous**. After injecting one ACK,
   the real actor's future intent, remaining FIFO credits, receiver processing,
   judgment and next ACK decision are **not recomputed**. Therefore 399/399
   synthetic ACK deliveries says nothing about realized actor throughput.
2. No trained judgment is consumed by a neuron, so **no learning** has been
   implemented. A transport arrival is **not** an applied actor ACK credit.
3. Synthetic requests run first on the new research scheduler. They do not
   establish a guarantee for the *unchanged* native scheduler or any admitted
   W4 deadline.
4. The 291 original v4jkl shadow donors are stale counterfactual identities.
   New causal execution chooses work to defer dynamically. **Do not report
   those donors as individually repaid** without identity-sensitive replay
   and correct after-ACK actor provenance.
5. The simulator remains bounded (three-neuron research fixture and abstract
   resources); no physical energy/latency, N-node, distributed ownership or
   persistent hardware claims.

The next genuine advance is an actor-generated, versioned native ACK request
source *inside* the reexecuted logical clock, with origin/receiver custody,
FIFO credit application, link settlement and a complete source-to-destination
causal ACK transaction. Only after that can a liveness/learning claim be
considered; this archive deliberately does not adopt it.

## Installation on fwork and gates

1. Verify project status and list archive members before extraction. The
   archive is additive and contains only new `docs/`, `search/`,
   `spk_bv_research/` and `tests/` files.
2. From `~/workspace/spk-backvalidation-v0`, extract with `tar --keep-old-files`
   so an existing local file is never overwritten.
3. Ensure the signed predecessor reports are available and run:

   ```bash
   bash search/spk_bv_v4mno_native_ACK_causal_gate.sh \
     ~/Scaricati/spk-bv-v3tuv-grant-rank.json \
     /tmp/spk-bv-v4jkl-shadow-arbiter.json \
     /tmp/spk-bv-v4mno-native-ACK-causal-replay.json
   bash search/spk_bv_v4mno_inherited_regression_gate.sh
   ```

   If the new output file already exists, the creation command **rejects**
   it intentionally. Choose a new output filename without deleting evidence.
   The tests support `SPK_V3TUV_REPORT` and `SPK_V4JKL_REPORT` to override
   predecessor locations when they are not under `/tmp` or alongside the
   repositories.

Release-level result: **conditional causal transport replay verified; actor
credit, application and learning remain unproven.**
