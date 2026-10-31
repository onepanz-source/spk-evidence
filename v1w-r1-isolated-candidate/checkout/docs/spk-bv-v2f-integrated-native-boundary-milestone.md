# SPK/* Back Validation v2f: Integrated Tick-Batch + Receiver Feedback Vertical Slice

## Purpose and release boundary

This is **one integrated milestone** (v2f), not successive research patch versions. It
closes a genuine *micro-runtime* vertical slice with batch admission, source-owned
forward events, receiver-local judgment, asynchronous feedback, and bounded
loss/overflow controls. **It does NOT provide a native frozen-scheduler feedback
channel, native CMP semantics, native operator mutation, or SPK learning.** No
frozen Core, Network, Compiler, Architecture, or Scheduler source is altered.

### Native evidence and finite result

Input is the canonical v2e report from fwork, SHA256:
`219cce4eadd862bc09d0f4d8f385057fa8e3db3084a59c5f1b2274a485aaa916`.
It attests 45 native v0e runs on 15 workloads with 3 BV plans and all 12 prior
v0w anchors. A finite empirical pattern holds across these records:

- `g = count(distinct input timestamps)` and `n = count(input events)`.
- `forward_emissions = 3*g`, `forward_terminal = g`.
- `processed_batches = forward_batches = 3*g`.
- `processed_events = n+2*g`, `forward_occurrences = 2*g`.

For same-tick 3-source work, `processed_events=5` while `processed_batches=3`.
This is **not** proof that frozen CMP aggregates by tick, because template
indices are not independently distinguishable, the fixture is finite, and
potentially different internal algorithms produce identical counts.

### Versioned research executor

- `spk_backvalidation_v2/batched_feedback_executor_v2f.py`: bounded independent
  tick-batch queue. One *research* decision/emission per (node,tick) batch.
  Every input is still admitted, and all parents remain in the decision log.
  Phase observations are published at execution time to optional `ObserverV2a`.
- Research recipient B or C evaluates a real admitted parent emission during
  its own decision using a **declared experimental value criterion**:
  `+1` if it emitted, `-1` otherwise. A feedback packet with source token,
  issuer/recipient and decision id traverses a separate delayed CONTROL queue
  to A or B respectively. This is actual mailbox delivery **inside v2f only**.
- The forward execution does not read the feedback mailbox. The observer and
  control queues cannot change forward results on the bounded supported cases.
  There are no operator updates or persistent learning. The feedback is not
  cryptographically authenticated and is not an independent absence witness.
- Loss and queue overflow cannot be interpreted as sender silence. Control
  loss/drop and failed observer sinks are exercised with negative controls.

### Integrated audit and acceptance

- 15 native workload rows × 3 native BV modes = **45 comparisons** against
  inherited native evidence. Five *aggregate* forward metrics match in each
  row; payload/state/event identity and CMP semantics are not compared as equal.
- 15 cases × four observation/control combinations + five negative experiments
  = **65 new v2f micro-executor calls**.
- 52 control packets reach their **research** sender mailboxes across the
  15 positive workload experiments; negative and loss tests are additional.
- 83 new tests PASS; integrated short gate also runs 296 v2a-v2e tests. Curated
  independent historical regression selected 1957 PASS on seeds 13 and 811.
  Running every historical test as one unstructured pytest batch can trip
  legacy import/fixture boundaries and is not represented as a full-suite PASS.
- Native v2e data is input, **not regenerated in v2f**. fwork CLI verifies
  pinned frozen bytes again before and after micro execution.

### Run on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v2f_Integrated_Tick_Batch_Receiver_Feedback_Milestone.tar.gz
bash search/spk_bv_v2f_integrated_milestone_gate.sh
bash search/spk_bv_v2f_selected_regression_gate.sh
python -m search.spk_bv_v2f_integrated_milestone \
  --v2e /tmp/spk-bv-v2e-native-admission-discrimination.json \
  --v2d /tmp/spk-bv-v2d-native-historical-holdout.json \
  --out /tmp/spk-bv-v2f-integrated-milestone.json
```

Output is safely created once: an existing path is rejected, input files outside
checkout are required, fixed research-module SHA256 pins are checked, and the
v2e report itself is pinned to the supplied native attestation. If native frozen
files are unavailable to the checker, `--contract-only` produces a report with
`frozen_native_source_pins_rechecked_in_this_run=false`, never a native claim.

### Next production gate: native versioned fork, not more posthoc lab increments

Native milestone requirements **all remain open**:

1. New separately versioned, source-owned scheduler fork with instrumented
   admission, decision, emission, ingress and closure semantics. Reject if it
   changes the frozen scheduler source or lacks forward parity and new holdouts.
2. Receiver-local BV control port **inside the fork**, with bounded queues,
   source identity, causal token binding, ordered delivery and overflow policy.
3. Receiver-owned score from a preregistered local value criterion, with
   explicit distinction between no packet, negative judgment and trustworthy
   absence evidence. Fail closed on missing coverage.
4. Actual source-neuron receipt and gated application/rollback of changes in
   a second episode, with randomized controls, native receiver-level traces,
   and testable operator-state changes. Only then consider a learning claim.

Until these gates are met, retain the five-phase BV estimate at 71%. A research
actor mail does **not** count as frozen-native learning or delivery to B.
