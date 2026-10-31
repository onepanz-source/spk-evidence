# SPK Native Learning v1u: Contextual P Bank Macro

**Status**: additive release candidate; only the Fedora `fwork` gate can establish full original-source conformance. Source of truth: v1t predecessor report SHA `6f11c639729d99c84907fa42e164714f014f93a8af3c0149ab6db40ae1788f8b`.

## Structural improvement

Native-v1t computes genuine local PE and transports A's judgment through BV before allowing receiver C to replace its own P program. Its durable journal preserves one global P state. Under changing tasks, a new target overwrites the previous choice and there is no task-specific recall.

Native-v1u adds a *bank of P profiles*, one per opaque declared context. All epochs use **the same** versioned v1t native PE/BV scheduler. A returning context obtains its last verified C P state from reconstructed causal history, not from the caller. A different context retains an independent P version and program.

The local five-epoch proof is:

| Epoch | Context | A goal | Initial C PE P and choice | Final context version | New P grants |
|---|---|---:|---|---:|---:|
| 0 | alpha | 15 | P0, 11 | P2 | 2 |
| 1 | beta | 12 | P0, 11 | P1 | 1 |
| 2 | alpha | 15 | P2, 15 | P2 | 0 |
| 3 | beta | 12 | P1, 12 | P1 | 0 |
| 4 | alpha | 11 | P2, 15 | P3 | 1 |

A total of 325 tick journal rows are persisted in five episodes. Re-execution creates zero new rows. Swapping the first two independent contexts preserves final P per context but changes the committed timeline digest.

## One release, not several patches

The bundle contains contextual ownership, journal durability, serial process lock, single causal re-execution of every predecessor, metamorphic context-order testing, seven interrupt/recovery boundaries, hostile journal and request tests, 49 new pytest cases and two byte-equal full conformance reports. Frozen BV-v0e, all v1r/v1s/v1t predecessors and the PE sources remain unchanged.

## Critical nonclaims

- **Host chooses context IDs and goal.** Neither context identity nor task meaning is authenticated. Malicious reassignment of a valid label to a different physical task cannot be detected without a trusted context source. Thus this proves memory partitioning and retention, not independent goal discovery.
- **Three candidate programs only:** 11/12/15 and bounded A/B/C. No arbitrary program synthesis or N-node proof.
- **No external irreversible actuation:** replay repeats calculations. Do not connect v1u to a physical actuator before adding a different external-effects protocol.
- **Advisory cooperative `flock`:** it does not prevent privileged edits or writers bypassing the wrapper.
- Persisted state is an audited logical replay from genesis, not a PE heap image or off-host tamperproof proof.
- The old frozen BV-v0e intentionally remains learning-free. The versioned native-v1u is the learner.

## Gate

`bash search/spk_native_learning_v1u_contextual_macro_gate.sh ~/workspace/spk-evidence/spk-native-learning-v1u-contextual-macro.json`

The gate requires the exact v1t predecessor, source SHA manifests v1r/v1s/v1t and v1u, original frozen source pins, all 49 new tests, inherited regressions, two independent real-source conformance reports, and a strict scientific scope check. A missing original module is **BLOCKED**, not a substitute grant or a test fixture.
