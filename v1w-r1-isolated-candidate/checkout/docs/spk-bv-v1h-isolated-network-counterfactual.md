# SPK/* Back Validation · v1h: Source-bound Isolated Native Network Counterfactual

Status: **research-only**. No modifications to frozen Core, Network, Architecture v1, Compiler v0, or scheduler v0e.

## Motivation from native v1g.1

The exact fwork v1g.1 result for the original fixture identifies two static
routes, **A(channel 7) → B(channel 0) → C(channel 0)**. C is A's causal
descendant but not its direct recipient. Four forward occurrences consist of
two A→B and two B→C deliveries; two assessments at C generate four reverse
packet deliveries, C→B and B→A. The packet `independent_receiver` flag does
not certify independent causal votes, and packets have no scored judgment.

This corrects the earlier v1e/v1f *hypothetical* direct mapping A→C.

## Exact intervention

1. Replay v1b.1, v1d, v1e, v1f and the full v1g.1 native report with the
   original pinned fixture and frozen runtime. Reject if any reference differs.
2. Construct a **detached dataclass copy** of the original case. Replace only
   A's third instruction `('CMP',1)` with `('CMP',2)`; preserve every other
   instruction, all external events, B, C, fabric and resource plans.
3. Execute the unchanged scheduler on the **original** with BV OFF and ON
   (forward-first) and on the **variant** with BV OFF and ON (forward-first).
   Replay both variant arms twice and compare whole results deterministically.
4. Audit static routes, forward occurrences, grants, consumers, terminal
   emissions and state digests. A variant with **zero forward occurrences**
   is legal, but may not contain orphan grants or unaccounted routed emissions.
5. Report changed batches, emissions, terminal events, occurrences and feedback
   assessments, without converting counts into utility. Never compare packet
   identities across the two interventions as if they denoted a shared event.
6. Fail closed on reference drift, forged timestamps/parents, non-equivalent
   source pins, nondeterminism, non-source-bounded test inputs or preexisting output.

The intervention is a **prospective pre-episode experiment**, not a runtime
commit made after feedback. The v1d choice came from the declared *synthetic*
local guard criterion and was **not** recommended by the recipients.

## Native CLI (on fwork, in existing research repo)

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1h_Isolated_Native_Network_Counterfactual.tar.gz
bash search/spk_bv_v1h_research_gate.sh
python -m search.spk_bv_v1h_network_counterfactual \
  --v1g1 /tmp/spk-bv-v1g1-native-original-route-lineage.json \
  --v1f /tmp/spk-bv-v1f-receiver-preference-polarity.json \
  --v1e /tmp/spk-bv-v1e-conditional-receiver-impact.json \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1h-isolated-network-counterfactual.json
```

The output path **must not exist**. Run the complete native CLI on fwork.
Passing the local research gate alone does not execute the native variant.

## Scientific boundary

This experiment may show that changing one genuine A operand alters downstream
B and C execution and the number of feedback packets in a bounded network.
It cannot establish a preferred operator without an explicit justified
receiver objective, nor establish learning absent an actual feedback-derived
selection and applied update with an independent future outcome. Suppressed
spikes do not automatically constitute a benefit. The native scheduler is a
logical model, not a physical timing/energy or scale test.

`v1h` does not promote the v1e assumption of *direct* A→C communication: the
full network variant is always routed through B.
