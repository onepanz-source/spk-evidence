# SPK BV v1u: bounded incremental shadow control-channel (research only)

## Gate and source custody

- Source: exact canonical **v1t** JSON, produced after full v1s->v1r->v1q->v1p->v1m predecessor replay. The v1u CLI invokes **v1t's CLI** with all predecessor files and requires a byte-for-byte match before setting the inherited native-v1t-recomputation flag.
- No replay of new native scheduler arms is claimed. The v1u laboratory contains a separate research-owned clock, delivery bus and receiver B projection. It does **not** add callback hooks to `execute_live_v0e` and does **not** alter frozen Core/Network, Compiler, Architecture, scheduler or persistent neuron state.
- A hash verifies byte identity, not source authentication; laboratory seals rely on Python object identity and have no interprocess or cryptographic authority.

## The bounded incremental experiment

For each of the four v1t A->B projections (original/variant x BV OFF/ON):

1. Set up a separate **laboratory** B mailbox with an ingress counter only. The experimenter alone owns the original native *posthoc* source counts.
2. At laboratory tick 0 mint the preregistered expectation, delivered at tick 1. At tick 3 mint and (optionally) deliver the *experimenter-declared* decision label. At ticks 4 and 5 replay 0 or 2 ingress events based solely on the posthoc count, **not native event IDs**.
3. At tick 7 mint sender-count and coverage declarations and deliver them at tick 8 if the bounded channel remains healthy. **No packet is minted earlier than its declared generation tick.**
4. The lab receiver can close its episode only after tick 9; before close, it has no verdict. A queue-capacity fault causes a fail-closed `CONTROL_FAULT_UNKNOWN`. Failure of a source report, interval coverage or preregistered expectation also prevents an absence conclusion.
5. The receiver view contains only locally replayed ingress counts and delivered, valid packets. It does not hold or query scheduler-owned trace records, factorial matrices, or another counterfactual branch.

All control messages are injected by the research driver. The clock, identity of episodes, intervals, and coverage are **lab constructs**. Native scheduler event times cannot be inferred from these timestamps. The two counterfactual worlds have separate episode IDs and no asserted event correspondence.

### Cases and expected classifications

Fifteen adversarial/normal control plans are bounded. The contradictory sender-count case is meaningful only for original (two ingress events); the remaining fourteen plans are present in both worlds and BV modes, giving **58 sessions**.

- Normal variant (`all_disclosed`): `LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY` (never a native absence certificate).
- Variant with no expectation: `NO_RECEIVED_EXPECTATION_UNKNOWN`.
- Variant with source report lost: `NO_SENDER_REPORT_UNKNOWN`.
- Variant with one coverage record lost: `UNCOVERED_INTERVAL_UNKNOWN`.
- Control outage and queue overflow: `CONTROL_FAULT_UNKNOWN`.
- Original with contradictory source report: `CONFLICTING_EVIDENCE_UNKNOWN`.
- Forgery, duplicate/replay, wrong episode, late and causally out-of-order packets: explicitly rejected. No malicious packet gains authority.
- Original observed ingress: `LAB_INGRESS_OBSERVED`, without any utility inference.

## Boundary to the next increment

**v1u does not observe native execution while it happens.** That would require a *source-verifiable*, in-process event interface or another genuine native provenance mechanism. Since the frozen public scheduler API returns its complete result at the end and no authorized event hook is available to this package, v1u demonstrates the **bounded runtime protocol for a separate research driver** using posthoc native seeds. It cannot be promoted to a native receiver test without a new, separately reviewed integration interface.

Future integration requirements: (1) independently observable producer and ingress hooks with source authority, (2) no forward scheduler mutation, (3) pre-event acknowledgement, (4) complete interval coverage with independent timing, (5) bounded queues and unambiguous loss semantics, (6) fail-closed replay/forgery guards, (7) receiver-local receipt, and only thereafter (8) a receiver value criterion and causal decision binding. BV scoring, operator commit/rollback and learning remain **zero**.

## Commands on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1u_Bounded_Incremental_Shadow_Channel.tar.gz
bash search/spk_bv_v1u_research_gate.sh
```

Then run:

```bash
python -m search.spk_bv_v1u_incremental_shadow_channel \
  --v1t /tmp/spk-bv-v1t-native-trace-shadow-mailbox.json \
  --v1s /tmp/spk-bv-v1s-receiver-disclosure-channel.json \
  --v1r /tmp/spk-bv-v1r-factorial-allocation.json \
  --v1q /tmp/spk-bv-v1q-native-factorial-interactions.json \
  --v1p /tmp/spk-bv-v1p-native-causal-locus.json \
  --v1o /tmp/spk-bv-v1o-decision-disclosure.json \
  --v1n /tmp/spk-bv-v1n-receiver-knowledge-disclosure.json \
  --v1m /tmp/spk-bv-v1m-native-passive-trace-projection.json \
  --v1l /tmp/spk-bv-v1l-two-port-observer.json \
  --v1k /tmp/spk-bv-v1k-receiver-witness-authority.json \
  --v1j /tmp/spk-bv-v1j-receiver-silence-observability.json \
  --v1i /tmp/spk-bv-v1i-native-feedback-silence.json \
  --v1h /tmp/spk-bv-v1h-isolated-network-counterfactual.json \
  --v1g1 /tmp/spk-bv-v1g1-native-original-route-lineage.json \
  --v1f /tmp/spk-bv-v1f-receiver-preference-polarity.json \
  --v1e /tmp/spk-bv-v1e-conditional-receiver-impact.json \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1u-bounded-incremental-shadow-channel.json
```

The CLI output file must not already exist; source reports must be distinct, safe and outside the checkout.
