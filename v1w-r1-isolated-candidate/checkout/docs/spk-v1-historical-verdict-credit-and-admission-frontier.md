# SPK V5 reference V1: historical feedback is not update authority

Status: **research-only**, successor to T9ABC/DEF/GHI. Frozen SPK Core, Network, Compiler,
Architecture v1, PE v1b and BV-v0e are unchanged. **No native learning.**

## T9JKL: observation / authorization separation

An actual V1 `SEM_B_C` tick can yield a judgment tied to an older version of C's P state.
T9ABC correctly logs `VETO_STALE_POLICY`. This checkpoint extracts the persisted source
`SEM_B_C` event, the `SEM_A_B` relay, the settled episode and the veto ledger record,
validates their consistency, and archives the judgment as `OBSERVATION_ONLY` in a
separate SQLite observer. A historical row **cannot** produce a P grant, including
following a restart. Replay and a broken hash chain are rejected. It is not a
trusted observer: a privileged host can fabricate or reseal its database.

## T9MNO: experimental admission frontier

Exactly the same 96 host-authored tasks, same original `_compute_local` function,
same V1 scheduler and same quota of three are used under three admission policies:

| Policy | In-flight per cue | Peak active | Admission waves | Successes | Stale vetoes | P grants |
|:--|:--|--:|--:|--:|--:|--:|
| serial | 1 globally | 1 | 96 | 88 | 0 | 8 |
| batch3 | No cue limit | 3 | 32 | 84 | 4 | 8 |
| context_affinity | 1 per cue | 2 | 48 | 88 | 0 | 8 |

All three execute 480 serialized dispatch events. The 16 additional affinity
**admission waves** are a real algorithmic tradeoff in this reference workload,
not a proven latency or throughput penalty in physical time. Because this test has
only two cues, context affinity never fills the third slot. No new native PE
resource admission has been implemented. The return to 88 successes is **not**
credit salvage; it is avoidance of avoidable policy-version collisions.

## T9PQR: negative witness, restart and source comparison

Two concurrent negative judgments for C cue 0 and version 0 must yield exactly one
P grant. After that grant, the P choice becomes 11, which satisfies A's PE goal.
Blindly applying the second, stale negative judgment would toggle C to 12 and
make A fail again. The unsafe counterfactual is evaluated through the unchanged
PE, but is never committed. Historical observer reopening and replay are tested.
The new report must reproduce the exact reduced row SHA-256 of its frozen-parent
T9ABC serial, three-inflight and two-inflight cases; two full runs must produce
byte-identical output.

## Nonclaims / boundaries

- No real sensor or identity authentication; host can forge source and ledger.
- No physical tick clock, energy measurement, real PE occupancy, or deployed throughput.
- No original BV-v0e scheduler changes or calls in the new research experiment.
- No native SPK P authorization, native semantic BV packet, or native learning.
- No general proof that context affinity beats other admission policies or workloads.
- All source custody uses SHA pins and must pass against fwork's original 12 files.
