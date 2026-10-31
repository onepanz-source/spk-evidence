# SPK/* Back Validation · v1y · External Python Trace Parity

**Status: research-only.** No changes to Core, Network, Compiler, Architecture,
`execute_live_v0e`, its signature, or other frozen sources.

## Objective

Use *external* CPython `sys.settrace` instrumentation around the unchanged frozen
`execute_live_v0e`, in a **separate native run**, to establish two strictly
bounded findings:

1. Interpreter `call`, `line`, and `return` observations of the exact frozen
   scheduler code object occur **while that scheduler is executing**.
2. For the pinned `A→B→C` fixture, returned native result bytes (canonical
   serialization) are identical with the external tracing OFF and ON. Both
   results must equal the earlier native no-observer v1x hash.

This is **not** an installed native producer-owned observer port. A Python line
trace is not a spike emission or receiving event, and a source line reached
before execution does not certify that the corresponding call succeeded.

## Input custody and the new evidence gate

- CLI reconstructs v1x, including its v1w replay and baseline checks, and
  demands exact byte equality to user-supplied native v1x.
- Frozen source SHA-256 is verified before and after replay and parity probing.
- Native scheduler module `__code__.co_filename` must resolve to the frozen
  checkout path; no monkeypatch or import substitution is applied.
- Four independent parity pairs: `(original, variant) × (BV OFF, BV ON)`;
  hence **eight additional scheduler executions** in this increment.
- Instrumentation counts only the exact scheduler Python `code` object, has a
  bounded event budget (16,384), and is removed in a `finally`-equivalent
  context-manager exit, including exceptions.
- An existing Python trace hook, unexpected trace exceptions, missing
  scheduler `call`/`return`, event budget overflow, altered result, source
  mismatch or output aliasing **fails closed**, without an attested report.
- For source-pinned line-hint candidates in v1w, record line-hit counters
  only. Zero line hits is not promoted to a claim that an event did not happen.

## Non-claims (mandatory)

- This is **not** a native `callback` from scheduler to neuron B.
- This does **not** deliver a control packet to B, establish source-origin
  authentication, or certify absence/independent coverage.
- Bitwise equality of returned results for this bounded fixture is **not**
  general noninterference: Python tracing incurs timing and CPU overhead,
  which may matter in concurrent and real-time contexts.
- No endogenous B utility criterion, judgment, causal credit, operator update,
  learning or architecture promotion occurs.

## Usage on fwork

Run the v1y gate after extracting the incremental tarball; then execute:

```bash
python -m search.spk_bv_v1y_native_external_probe \
  --v1x /tmp/spk-bv-v1x-reference-observation-port.json \
  --v1w /tmp/spk-bv-v1w-observation-seam.json \
  --v1v /tmp/spk-bv-v1v-frozen-observation-surface.json \
  --v1u /tmp/spk-bv-v1u-bounded-incremental-shadow-channel.json \
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
  --out /tmp/spk-bv-v1y-native-external-probe.json
```

For a non-native structural sanity check only, use `--contract-only --v1x
... --out ...`. This never connects a tracer and never executes the native
scheduler. The report records zero additional native runs.

## Next scientific gate

If fwork confirms four native external-probe parity pairs, explore a genuinely
**versioned native executor** that provides source-owned semantic event identity,
receiver-local delivery, and independent coverage, while preserving the
original frozen implementation and proving observer OFF/ON noninterference.
