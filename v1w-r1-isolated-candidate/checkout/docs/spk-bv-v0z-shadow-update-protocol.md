# SPK/* · BV v0z: shadow operator hypothesis and prospective holdout protocol

## Scope and scientific claim

**Research only. No native learning, commit, rollback or observed benefit.** BV v0y validates nominal judgments and `noop` proposals; v0z validates only *plans* to compare a single discrete alternative neuron operator against the frozen choice on a separate, future holdout episode. Validation never executes or modifies a neuron and never promotes Core/Network/Compiler/Architecture v1.

The real v0y attestation has `criteria=decisions=judgments=proposals=0`; therefore the default real v0z attestation must also admit **zero hypotheses**. A nonempty example ledger is synthetic SHADOW input supplied explicitly, not inferred from v0e packets.

## Mathematical boundary

Given an already validated v0y tuple (criterion `c`, decision `d`, nominal judgments `J`, noop proposal `p`), declare hypothesis `h` on a future episode `e_future`:

`H_shadow(c,d,J,p; t, e_future) = (chosen_operator, proposed_operator, paired-input-declaration, paired-budget-declaration, external-holdout-protocol)`.

Admission requires:

1. `c.registered_tick < d.decision_tick` and every `j` belongs to exactly the criterion named by `h`. Each judgment must have passed v0y availability and provenance checks. Repeated declared origins remain a single grouping, **not** certified independent votes.
2. `h.baseline_operator = d.chosen_operator`, `h.candidate_operator = p.proposed_operator ≠ baseline`; candidate must belong to the decision's **original** `admissible_operators`. The declared change bound is exactly **one discrete operator selection**. This does **not** prove the cost of executing that operator or boundedness of any native state change.
3. `p.created_tick ≤ h.planning_tick ∈ p.eligibility_window`, with each judgment available by planning; `h.planning_tick < h.holdout_start_tick ≤ h.holdout_end_tick`. `future_episode_id` must differ from the decision's episode. This is a declaration, not proof of independent or held-out sampling.
4. `control_input_sha256 == candidate_input_sha256` and `control_budget_sha256 == candidate_budget_sha256`. SHA hashes are supplied **declarations for a future experiment**, not a witnessed paired execution. A real runner must verify these later.
5. `evaluation_objective_id` and `evaluation_evaluator_id` match the preregistered criterion. The only permitted mode is `declared-paired-external-holdout`. Score fields or claims about measured benefit are forbidden.
6. One hypothesis per source decision and no two hypotheses targeting the same `(neuron, future_episode)` pair.

`admitted(h)` means **a well-formed, forward-only experimental hypothesis**, not a beneficial update, not a scored outcome, not causal credit, and not a right to commit.

## Anchor and custody

The v0z CLI checks (1) source-recomputed v0x against v0w using v0y's inherited verifier, (2) entire v0y attestation exactly reconstructed using v0w, v0x, and an optional explicitly supplied ledger, (3) ledger and optional hypothesis plan, (4) exact bytes stable before and after comparison, (5) no symlink/alias/repository writes/overwrites. Default empty plan is **empty**, not a fabricated experiment.

## What future verification still requires

The project must explicitly design external scoring (what is good or bad, whether observer judgments are truthful), bind every decision to actual native computational state and operator semantics, verify equal effective paired episodes, build an isolated executor and bounded rollback process for experimental updates, and then score prospective holdouts under a predeclared rule. Without those, v0z cannot increase the proven-learning percentage.

## Files and running

Included: `spk_bv_research/shadow_update_v0z.py`, `search/spk_bv_v0z_shadow_update.py`, `search/spk_bv_v0z_research_gate.sh`, `tests/test_spk_bv_v0z_shadow_update.py`, this document.

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v0z_Shadow_Update_Holdout_Research.tar.gz
bash search/spk_bv_v0z_research_gate.sh
python -m search.spk_bv_v0z_shadow_update \
  --v0y /tmp/spk-bv-v0y-shadow-judgment-contract.json \
  --v0x /tmp/spk-bv-v0x-native-verified.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v0z-shadow-update.json
```

A nonempty research trial needs both `--ledger /tmp/explicit-shadow-ledger.json` and `--hypotheses /tmp/explicit-shadow-hypotheses.json`, with the **same** ledger as the anchor recorded by v0y. Because the current v0y attestation has no ledger supplied, v0z correctly refuses any nonempty ledger until a new, separately source-anchored v0y shadow attestation is made.
