# SPK Back Validation v4ah–v4aj — restart-persistent review escrow

**RESEARCH ONLY.** No native learning, no program adoption and no modifications
to frozen native v0e, Core/Compiler or Architecture v1.

## Research question and result

Can a bounded two-view task-review verdict be recorded so a process restart,
duplicate submission or interrupted transaction cannot silently consume,
lose or relabel reviewer receipts? On one trusted host, in this research
fixture, **yes**. The SQLite escrow writes a canonical review event, the two
view-specific nonce indices, the monotonic per-source decision tick and the
linked journal head in **one transaction**. Each reopen recomputes the chain,
validates signed test reviews and compares the materialized indices to their
log derivation. Replayed nonces remain rejected across process restarts.

Quarantine is first-class, not a failure to write: explicit disagreement and
abstention records are retained, tagged and barred from program adoption. Only
invalid, replayed, out-of-order, forged or unsigned judgments fail closed
without a new journal event. Even a unanimous agreement is simply recorded;
it **does not** authorize a native weight, algorithm or state update.

## Source and execution custody

- Exactly SHA-bound predecessor reports: v3tuv grant/rank and v4ae–v4ag
  two-view adjudication, including predecessor native digests and projections.
- 18 original frozen native v0e reexecutions (3 signed schedules × 2 BV
  modes × 3 native PE capacities), with exact original SHA checks.
- 72 additional native base/candidate × input-channel probes, verifying both
  terminal endpoint and emitted-spike projections against predecessor evidence.
- 11 persistent-review variants per original source, **198 review attempts**;
  **72 committed journal events** and **144 persisted unique nonces**.
  The commits comprise 36 consistent research-only judgments, 18 explicit
  disagreements and 18 abstentions. There are 18 injected rollbacks followed
  by successful submissions of the same otherwise valid review.
- A 29-test v4ah–v4aj suite, plus seven inherited suites totaling 141 tests:
  **170 passed**, an independent frozen-native smoke witness, create-only
  reproduction and byte-for-byte comparison to the pinned reference report.

The recorded logical head for the pinned fixture is:

`3beb754a5f7a35b80142be9a97b057b84db65a9defeb62c8dae8dd7466e63e97`

The report contains this witness and must be retained in custody **separate
from the mutable database**. The gate verifies the database against that
head; the hash alone is not a trusted timestamp or cryptographic identity.

## Concrete fault coverage

| Condition | Research observation |
| --- | --- |
| Process close/reopen | Persistent nonces and monotonic source clocks survive |
| Duplicate submission across two SQLite connections | Exactly one transaction commits |
| Injected exception after journal record insert | Entire uncommitted transaction rolls back |
| Injected exception after nonce and source-clock insert | Entire uncommitted transaction rolls back |
| Child process `os._exit(77)` before commit | Reopened DB has no partial event |
| Changed on-disk journal row / nonce index | Reopening rejects the database |
| Wrong externally retained head | Reopening rejects even an internally coherent DB |
| Signed disagreement or abstention | Recorded and quarantined, no adoption |
| Incorrect MAC, binding, time or task-label canary | Rejected, no nonce consumed |

The database is an exclusively created, owner-only mode-0600 file, on a
single local host; it uses SQLite `BEGIN IMMEDIATE`, full synchronous mode
and rollback journaling. The JSON report is separately created with
exclusive-create semantics. **Those two output files are not committed as
one cross-file transaction**: if report creation fails after database
creation, the database may remain as a forensic artifact, never silently
overwritten by the CLI.

## What this emphatically does not prove

1. The `endpoint` and `emission` views derive from the **same native
   execution**, so their agreement is correlated, not independent task truth.
   Counterfactual task labels can reverse the alleged improvement without
   changing the execution evidence.
2. The signed review HMAC keys are **public laboratory fixtures**; they are
   not provisioned reviewer credentials and cannot defeat impersonation.
3. The journal's SHA-256 links detect local accidental or unauthorized
   partial changes, but a storage adversary with control of all rows,
   fixture keys **and the head** could replace the whole history. An
   independently retained, authenticated head is a required trust boundary.
4. Test crashes prove SQLite transaction rollback in these scenarios, **not**
   power-loss, storage-controller or actual hardware durability. This is not
   replicated consensus, a distributed replay guard or disaster recovery.
5. No independently validated real-task holdout, no learner efficacy claim,
   no physical-energy claim and no promotion of results into frozen native
   logic. Program adoptions = **0**; native learning updates = **0**.

The next research gate is genuinely independent task evidence provisioned
with a distinct trust root and separately custodialized heads. Before that,
promoting a consistent review into a self-modifying neuron's choice would be
scientifically unjustified.
