# SPK Back Validation — v4p/v4q/v4r

**Status:** `REEXECUTED_ACTOR_JUDGMENT_TRANSPORT_AND_DERIVED_CREDIT_NO_NATIVE_LEARNING`

Three cumulative **research-only** steps over the pinned v4m–v4o causal
reexecution engine. No frozen Core, Network, Compiler, Architecture v1 or
original `spk_backvalidation_v0` scheduler was modified.

1. **v4p — Endogenous source:** when an actually delivered native occurrence
   is consumed in a reexecuted receiver batch, the receiver emits a *derived*
   judgment with v2h's local experimental rule `+1 if outputs else -1`.
   Ownership, occurrence ID, batch time, receiver identity and sign are checked
   against the resulting native forward trace. No judgment is inferred from
   silence. The control becomes eligible only at the next logical tick.
2. **v4q — Causal feedback transport:** each judgment request must obtain a
   real grant in the *simulated* global/PE, O/E memory, directional/shared
   link and in-flight budgets; it occupies the resource before subsequent
   native forward/BV work. All native events and BV are then recalculated.
   A no-feedback null run remains exactly equal to frozen native output.
3. **v4r — Actor credit receipt:** after a charged delivery, a separate derived
   actor-scoped register applies `+1/-1`, subject to bounded credit policy.
   Each accepted receipt has ordered actor sequence, source provenance,
   actual grant/delivery time and a local tamper-detection hash chain.
   Policy refusals are logged as refusals, not network losses or negative votes.

## Signed-source comparison

The CLI requires the exact canonical predecessor reports:

- `spk-bv-v3tuv-grant-rank.json`: SHA-256
  `f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827`.
- `spk-bv-v4mno-native-ACK-causal-replay.json`: SHA-256
  `0030c7bd9c84c022b3eddfadce4ae590f919186c5ee76a228cf57870b7f55721`.

The v4jkl report is additionally required for its **inherited v4m test suite**.
The source executor and new hooks have SHA pins. Extraction with
`tar --keep-old-files` is additive; the tarball does not overwrite predecessors.

## Reproducible report (fixed finite research matrix)

Input: three eight-tick schedules, three native BV modes, two native PE
capacities. Per original native run: four counterfactual derived policies
(`normal`, `feedback_disabled`, `zero_actor_credit`, `narrow_actor_credit`).

| Measure | Observation |
| --- | ---: |
| Independently replayed original native runs | 18 |
| Derived causal runs | 72 |
| Null-control runs with exact full native parity | 18 |
| Newly computed receiver judgments | 864 |
| Charged transport deliveries | 864 |
| Bounded derived actor credit receipts | 324 |
| Delivery accepted, credit policy denied | 540 |
| Native forward traces changed by actor traffic | 54/72 |
| Native learner/operator updates | 0 |

These figures **do not** compare equal workload with v4m's 399 *exogenous*
ACKs. That earlier experiment used different request provenance and policy.

## Local validation

From the `spk-backvalidation-v0` repository:

```bash
bash search/spk_bv_v4pqr_endogenous_actor_ACK_gate.sh \
  ~/Scaricati/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4jkl-shadow-arbiter.json \
  /tmp/spk-bv-v4mno-native-ACK-causal-replay.json \
  /tmp/spk-bv-v4pqr-endogenous-actor-ACK.json
```

The gate runs 18 new tests, 15 inherited v4m tests, frozen v0e capture,
produces a create-only report and compares it byte-for-byte with the pinned
observation. `REJECTED` lines inside the inherited negative tests are expected.
Output must not exist beforehand and must be outside the repository.

## Limits and next scientific question

- `derived_actor.applied_credit` is **not** a native runtime's admitted actor
  consumer and is **not** a neuron weight/program update. It is a separately
  simulated, causally charged research register.
- The `+1/-1` response is a receiver's local computational observation, not a
  claim about global effectiveness of the source's computational choice.
- Feedback's actor semantics is independent of *terminal* native BV on/off;
  these two distinct mechanisms compete for the same simulated fabric.
- A receipt hash-chain catches in-process tampering and replay; it does not
  provide network-source authentication.
- Extra actor consumer CPU/memory work is not quantified: current experiment
  models the previously charged transport service and derived application,
  **not** a physically separately scheduled native learner step.
- No convergence, global fairness, N-node scale, deadline guarantee,
  hardware energy, mesh reliability or adaptive weights are established.

The **next real barrier** is how to admit a consumer turn with native authority
and distinct PE/memory cost, preserving v1 architecture ownership and a
causal negative-feedback interpretation, before discussing learning updates.
