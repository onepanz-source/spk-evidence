# SPK V5 T17 Macro: Unknown Actuator Polarity Learned from Receiver PE Observations

**Research only. No changes to frozen SPK architecture, compiler, original BV or memory authority.**

T15/T16 established improvement under a *known* actuator law but failed badly when the law was reversed. T17 preregisters and tests one deliberately narrower relaxation: C starts with unknown actuator polarity (`P.actuator_sign=0`), then infers whether command HEAT increases or decreases temperature from A's independently observed before/after readings. A calculates the sign and improvement using frozen SPK `_compute_local`, and B relays the corresponding PE evidence. C updates its own versioned `P` in one database transaction only for an exact-matching relay.

The system does **not** learn arbitrary dynamics. It is still given that there are two complementary commands with a monotone signed effect; it must learn only which physical command has positive effect. C does not know the world's `reverse_actuator` setting and does not call the world plant while authorizing a P update. World transitions and correctness are independently checked *after* episodes by the audit.

The same 10 setpoints and 3 training orders from T15/T16 are used. Training temperatures are even; held-out test temperatures are odd, with setpoint excluded. Prespecified scientific thresholds: normal gained accuracy >= 15 points, reversed gained accuracy >= 25 points; all adaptive cells must infer the actual direction by the end of training; four denial controls plus fixed policy may never update P. Negative outcomes are represented by `...NOT_SUPPORTED` status rather than recast as software errors.

## Actual tests and limitations

- `StagedCell` v2 owns a **two-dimensional P** `(theta,actuator_sign)`, one CAS revision for either kind of change, backed by SQLite `p_intent` and `p_grant`, a trigger and replayable ledger.
- Five durable stages: `C_PE → WORLD → A_PE → B_RELAY → C_CREDIT`.
- The A actor computes both distance-based evaluation and response sign using original PE primitives; Python encodes sensor differences and absolute distances as channels. The B actor uses an original PE fragment and binds the A digest, verdict and sign to the source episode.
- Clipped zero-change observations do not identify sign and cannot grant actuator polarity.
- Every P update requires a successfully bound B packet, current P version, execute mode and budget. Tampered direction, altered verdict, missing receipt and wrong lineage produce no update.
- All 360 cells are audited, and P is strictly read-only on held-out evaluations.
- The original T16 frozen-policy normal baseline and T16 reversed-control seed-17 baseline are rerun and compared.

**Not proven:** physical sensor authentication, independence of the Python/host world, stochastic or nonstationary dynamics, generalized reinforcement learning, original frozen BV semantic credit, original A1d permission for the thermal contract, or original SPK-native learning. The T13 (choices 11/12 with goals 11/12) and T17 (thermostat temperatures and goals) contracts are distinct. T17 deliberately does not mislabel them as interchangeable.

## Gate

```bash
bash search/spk_v5_t17_macro_unknown_actuator_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t17-macro-unknown-actuator.json
```

The gate verifies T16's exact fwork parent SHA, all 28 milestone manifests with source SHA pins, original PE/A1d/BV source identities, T17 tests, two byte-identical independent scientific experiments, and all inherited regression suites. It refuses to overwrite any report. The scientific hypothesis may fail without any false claim of native learning.
