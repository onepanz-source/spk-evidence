# SPK S3.7d/24l: Offline Source Pin, Live Lease and Replay Evidence v0

**Status: INTEGRATION PASS (2026-10-16, cooperative offline scope).** Baseline Git `fe292dc`, frozen Core v0, Network v0,
Compiler v0, k24b, 24d–24k unchanged. One integrated development/gate.

## 1. Purpose and scope

This component protects the *cooperating, offline, local reference launcher*
against three avoidable errors:

- launching the wrong **version of an operator-selected local provider module**;
- simultaneously launching the **same epoch ID** in two participating local
  processes using one private lock directory;
- mistaking divergent **public execution summaries** for deterministic runs.

This is not sensor/producer authentication, authority persistence, tamper-proof
logging, deterministic proof of full internal histories, or cross-host fencing.
The underlying 24k application host and service semantics are not altered.

## 2. Provenance vs structural consistency

The operator supplies `module:factory` and an *expected SHA256* of the module's
exact `.py` bytes. The launcher resolves the factory in the operator-managed
Python installation, verifies that it is defined in the chosen module and
checks its module-file digest before the factory call. A mismatch fails closed
without requesting an epoch. This is **source-version pinning**, not evidence
that incoming EVENTs came from a particular physical sensor.

Importing the module or its parent packages executes trusted Python code even
before the digest check, and local code can be swapped after checking: no
sandbox, signature validation or malicious-local-code resistance is claimed.
The snapshot's SPK seal is a structural integrity condition **relative to a
provided network**; it does not authenticate the external source. A future
production producer must establish provenance outside these components.

## 3. Live epoch lease

One `LocalEpochLeaseV0(epoch_id, lock_dir)` holds a POSIX advisory `flock` from
before provider import until the 24k execution returns or fails. It costs zero
SERVICE_TIME. The lock directory must be a pre-existing, local, non-symlink
folder owned by the effective user with mode `0700`; lock files have mode
`0600` and names derived from SHA256 of exact `epoch_id`. Symbolic link files,
wrong permissions, or replaced inodes are rejected.

**Claim proved only for participating local processes on a compatible
filesystem using the same directory while leases overlap.** The lock is
released on normal exit, exceptions or process termination. Thus sequential
rerun of the same epoch after process exit is **allowed** and can duplicate
computational authority. Another lock directory, another host, direct owner
calls or malicious processes bypass this policy. It is neither a lease with
renewal nor a durable single-use ledger; no crash-recovery protocol exists.

The operator must keep the lock directory stable and avoid unlinking files
while in use. Directory ownership/mode checks do not protect against another
process running with the same user's privileges.

## 4. Reproducible public outcomes

The existing 24k `OfflineEpochResultV0` is canonically serialized (sorted JSON
fields and typed values) and SHA256-hashed with a domain separator. A caller
may supply a golden expected result digest. On mismatch, the launcher exits
with `ERROR` rather than a success-shaped record. In particular, a `CLOSED`
execution with an unexpected summary is reported as **verification failure**.

This digest covers only the public summary fields, not every EVENT, P/S,
quantum, Core state, emission or the source epoch snapshot. Different hidden
traces could share an identical public summary. The full existing 24d–24g
replay/audit checks remain necessary. This is an *integration reproducibility*
probe, not an execution trace attestation.

Comparing two independent launches of the deterministic lab fixture must be
understood as two **new** local reference executions. It is not resumption of
one epoch, and it does not demonstrate exactly-once effect across runs.

## 5. CLI boundary

Example from repository root (local lab only):

```bash
install -d -m 700 /tmp/spk-local-locks-operator
python -m search.spk_24l_pinned_offline_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --provider-sha256 "$(sha256sum tests/spk_offline_demo_epoch_v0.py | cut -d' ' -f1)" \
  --lock-dir /tmp/spk-local-locks-operator \
  --epoch-id E0 --max-actions 100 --chunk-size 6
```

`--expected-result-sha256 <64 lowercase hex>` optionally rejects results
whose *public summary* differs from a previously observed reference.

Exit codes are inherited from 24k: `0` complete with verified output-free
S receipt, `3` incomplete without receipt, `2` failed (including bad pin,
lease conflict, invalid result digest). `ERROR` responses never have a
`completed:true` field. Incomplete runs are not resumable across process exit.

## 6. Acceptance matrix for fwork

| Gate | Observable criterion | Limit |
| --- | --- | --- |
| L01 | Correct source pin accepts operator-selected demo provider | Source bytes, not trusted origin of data |
| L02 | Wrong source/version pin fails closed | Import may already have executed local code |
| L03 | Same epoch, same directory, overlapping processes: one blocked | Advisory cooperating local flock only |
| L04 | Lock released on exception/exit; incomplete no receipt | **Sequential replay still possible** |
| L05 | Two lock directories can admit same epoch in parallel | No global/federated ownership |
| L06 | 24k finite true Core execution: `CLOSED`, version 0 → 1 | Output-free one-root test fixture |
| L07 | Different chunk sizes: same public summary/digest | Not full trace equality |
| L08 | Wrong golden digest: failure, no success-shaped JSON | Does not roll back prior accepted service |
| L09 | Limited positive budget: incomplete, no receipt; invalid/zero budget: reject | No durable continuation |
| L10 | Full regression, 24d–24k unmodified, isolated gate succeeds | No claim of deployed producer |

## 7. Scope and source inventory

New files only:

- `spk_simulator/application_trust_boundary_v0.py`
- `search/spk_24l_pinned_offline_launcher_v0.py`
- `search/spk_24l_final_gate_v0.sh`
- `tests/test_application_trust_boundary_v0.py`
- this document and the S3 acceptance review document

No modifications to Core, Network, Compiler, k24b, 24d–24k, the canonical
24k offline launcher, or the demo fixture. Keep unrelated untracked
`core_temporal_*` and `spk_24d_collect.py` out of staging.

**Gate:** `bash search/spk_24l_final_gate_v0.sh` on the complete fwork tree.
This archive's local checks do **not** imply the real gate has passed.

## 8. Certified fwork gate - 2026-10-16

Baseline: fe292dc.

- Trust boundary tests: 46 passed.
- Root/host/launcher integration: 306 passed.
- Full repository regression: 2638 passed.
- Two finite executions: identical public summaries.
- Source drift, result drift and limited budget: negative gates PASS.
- Patch whitespace and frozen-module non-interference: PASS.
- Public result SHA256:
  5b2bb3454d570488ea74141f8678498ca5887cd85e32546f672511b4bc79d060

Acceptance is limited to cooperative offline execution.
No authenticated sensor provenance, durable exactly-once execution,
cross-host fencing or full internal-trace equivalence is claimed.
