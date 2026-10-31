# SPK Native Learning Runtime v1: durable causal P across epochs

## Scope

Additive, research-only **v1r** successor of the first same-scheduler native
P transition. Frozen BV-v0e / PE / Core / Network / Architecture sources are
untouched. The predecessor report SHA-256 is pinned and checked by the gate.

One **macro checkpoint** covers multiple substantive capabilities:

1. The actual original `_compute_local` is invoked for C, B and A in a
   versioned BV-derived scheduler. Actual reverse delivery is the only path
   that may alter C's running P program. P0->P1 changes C's subsequent PE
   output *within the same episode*.
2. The new `tick_sink` records a canonical end-of-tick snapshot **after**
   admitted BV/PE/P work. Each tick is a separate SQLite transaction,
   `synchronous=FULL`, with a hash-chained record, source fingerprint and
   binary program P. A simulated crash before a commit has no journaled P
   effect. A crash immediately after a commit is replay-verified.
3. Restart reexecutes the bounded computation **from episode genesis**,
   checking every previously committed record exactly before appending new
   ticks. Committed rows are not replay-inserted. This is event-sourced
   recovery, **NOT** instant restore of arbitrary interpreter state.
4. After an epoch closes, its final P becomes the next epoch's input P.
   Prior history is replay-verified before inheritance. A second episode
   begins using the previous choice/version in actual `_compute_local`, not
   the host-authored initial program template.
5. Versioned CAS and P ownership remain enforced. 42 dedicated tests cover interruption
   before and after the credit, duplicate resume, tampered tick rows,
   altered inputs, forged owner/P version, wrong order, incomplete parents,
   final-P tampering and original scheduler parity with learning disabled.
6. Independent runs produce byte-identical reports and never claim learning
   in the original frozen BV-v0e.

## Falsifiable acceptance

- First episode: C(12, P0) -> A PE negative -> reverse BV -> C(11, P1).
- Immediate restart after ticks 1, 9, 13, 14, 15, 22, 24 reconstructs exactly
  the continuous execution; **one** P grant, no duplicate committed tick.
- The next epoch reads C(11,P1) from inherited P even when its host-supplied
  case template was C(12). The subsequent negative episode transitions to
  C(12,P2). Replaying a CLOSED epoch changes no records.
- Control paths (no BV, no learning, `verify`, budget zero) have no P grants.
- Any historical record mismatch, parent mutation or source drift fails closed.

## Explicit limits

This remains **bounded three-neuron binary learning**, not arbitrary SPK
learning. World goals are host authored. No physically authenticated sensor,
protected key source, independent credit authority, stochastic world model,
general N-node topology or distributed PE. Local SQLite protects against
accidental corruption and provides detectable causal divergences, but a
privileged host controlling both source and ledger can rewrite/reseal evidence.
No external irreversible side effects occur in this proof. Restart by
reexecution could **repeat external effects** if such effects are added
without separate idempotent custody; that extension is explicitly blocked.

Hash chaining is evidence of internal consistency, not a security signature.
Runtime code and source fingerprints are bound to each episode.

## Deployment

Use only the additive archive and a single script:

```
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_Native_Learning_Runtime_V1_Durable_Macro_Cumulative_20261023.tar.gz
bash search/spk_native_learning_v1_durable_macro_gate.sh \
  ~/workspace/spk-evidence/spk-native-learning-v1-durable-macro.json
```

The gate rejects preexisting report files and verifies the predecessor report
and the original frozen source bytes and loaded identities before execution.
It runs cumulative regressions and twice recomputes evidence on two
independent temporary SQLite stores; only then publishes the report.
