# SPK S3.7d/24j — Application Runtime Host Reference v0

**Status: INTEGRATION PASS ON FWORK (REFERENCE HOST ONLY); APPLICATION ADOPTION OPEN.**

Baseline: `713525a` (24i application runtime host contract). This patch **adds**
`spk_simulator/application_runtime_host_v0.py`, its regression suite, and this
document. It does not edit Core, Network, Compiler, k24b, or k24d–k24i.

## 1. Scope and classification

This is a **reference in-process integration boundary**, not a deployed SPK
application entrypoint. A named test-scope provider returns a fresh
`OwnedSharedEventCycleStateV0` to a single `ApplicationRuntimeHostV0`. The
host constructs exactly one private `OwnedRootExecutionDispatcherV0` and
forwards each accepted application command as a canonical
`DispatchRequestV0`. Every mutation inside this host delegates to the
existing 24g → 24f → 24e → k24b/24d chain.

The provider's `provider_id` is a descriptive attribution **not a credential**.
The seal proves structural consistency of an epoch, not trusted provenance.
A new host process, duplicate host instance, direct legacy caller, or Python
reflection remains outside the control boundary. There is no global fencing,
crash recovery, durable ledger, network listener, message broker, background
loop or second clock.

The repository audit 24h previously found **no deployed application host**.
Adding this library plus fixture tests is not proof of application adoption.
**H01, H10 (production provenance) and H11 (deployed lifecycle) remain OPEN.**

## 2. Public host API

```python
from spk_simulator.application_runtime_host_v0 import ApplicationRuntimeHostV0
from spk_simulator.owned_root_execution_dispatch_v0 import (
    DispatchRequestV0, DispatchOperationV0,
)

# Explicitly selected in-process *integration fixture*, not production identity.
host = ApplicationRuntimeHostV0(provider=make_sealed_epoch, provider_id='fixture')
status = host.admit(epoch_id='E0')
first = host.dispatch(DispatchRequestV0('E0', DispatchOperationV0.RUN,
                                        status.view.revision, 1))
# Budget exhaustion != completion. Caller must choose a new bounded request
# with the actually returned revision; the host never silently retries.
# Only status.completed with CLOSED and genuine S receipt means completion.
```

`make_sealed_epoch()` is provided by the embedding test or application. The
reference host **does not** create, authenticate, sign, or source epochs.
It does not accept arbitrary owner selection and exposes no raw owner or
registry in its public return values.

### Lifecycle

| Transition | Contract | Result |
| --- | --- | --- |
| `NEW -> ACTIVE` | valid `admit(epoch_id=...)` from configured provider | one private 24g dispatcher installed |
| `NEW -> NEW` | rejected admission | no installation and no consumed service |
| `ACTIVE -> ACTIVE` | `SNAPSHOT`, `AUDIT`, `TRACE`, bounded/incomplete `ADVANCE` or `RUN` | 24g view, no synthetic receipt |
| `ACTIVE -> CLOSED` | underlying 24g reports `CLOSED` with output-free S commit + exactly +1 version | success eligible |
| `ACTIVE -> FAILED` | failure of accepted dispatch, inconsistent output, or incomplete shutdown | mutation permanently disabled; prior accepted substeps may remain |
| `CLOSED -> CLOSED` | read-only operations / shutdown | no second commit, no reset |
| `FAILED -> FAILED` | diagnostic read-only operations / shutdown | no restart or silent fresh dispatcher |

Malformed canonical requests, wrong epoch and stale revision are **rejections
before mutation**; the host remains `ACTIVE` when the dispatcher refuses a
stale revision. An accepted 24g operation that fails unexpectedly puts the
host in `FAILED`. `HostExecutionErrorV0` preserves the original exception
as its cause; `status()` offers best-effort underlying observation. When a
snapshot fails, it reports `view=None` and a diagnostic, not a stale cached
view masquerading as the current authoritative state.

**Shutdown of an incomplete host is not a commit.** It enters fail-stop and
never synthesizes a success receipt. Read-only diagnostics remain possible.

## 3. H01–H12 acceptance map

| Gate | Evidence from this patch | Assessment after fwork |
| --- | --- | --- |
| H01 Actual consumer and provider | Only integration tests with explicitly named fixtures | **OPEN**: no deployed app consumer |
| H02 Canonical admission | real shared epoch accepted; malformed, mismatched and provider exceptions rejected | **PASS** in reference-host integration tests |
| H03 Lifecycle | reject duplicate admit and any reset after CLOSED/FAILED | **PASS** in reference-host integration tests |
| H04 Single writer | parallel same-revision requests accept at most one | **PASS** in reference-host integration tests |
| H05 Bounded run | incomplete `RUN` and explicit resume with real next revision | **PASS** in reference-host integration tests |
| H06 Root/terminal | real fixture through handoff, output-free S and version 0 → 1 | **PASS** in reference-host integration tests |
| H07 Fail-stop / no rollback | inject a failure after an accepted quantum; inspect authoritative revision | **PASS** in reference-host integration tests |
| H08 Shutdown | incomplete shutdown never reports success; CLOSED still read-only | **PASS** in reference-host integration tests |
| H09 Boundary | host public responses omit owner, driver, registry, dispatcher | **PASS** as a cooperative API boundary; no Python sandbox guarantee |
| H10 Provenance | fixture source explicitly named; no authenticity claim | **OPEN** for production |
| H11 Deployment | one-process, one-epoch *per host instance* | **OPEN**: no real launcher/fencing |
| H12 Regression | new 24j tests, 24d–24j integration set and full checkout regression | **PASS**: 39/39, 217/217, 2549/2549 on fwork |

The test with two hosts accepting an identical epoch is intentionally
positive as a **demonstration of missing cross-host mutual exclusion**;
never report it as proof of exclusivity.

## 4. Observed integration gate on fwork (2026-10-15)

The following outputs were reported from the full `~/workspace/spk-algebra`
checkout after applying the 24j patch, with Git baseline `713525a`:

| Run | Observed result |
| --- | --- |
| `tests/test_application_runtime_host_v0.py` | **39 passed in 0.32 s** |
| Root/terminal/custody/dispatch/host integration set | **217 passed in 0.78 s** |
| `python -m pytest -q` complete suite | **2549 passed in 9.90 s** |
| Previous full suite at 24h | 2510 passed |
| Delta | **+39 tests**, no detected regression |

The shown `git status --short` reports the three new 24j files as untracked
plus the pre-existing, unrelated `search/core_temporal_depth5_v1.py`,
`search/core_temporal_quotient_alignment_v0.py`, and `spk_24d_collect.py`.
There is no 24j commit yet at this gate. The output does not include a fresh
24h static-adoption audit following the addition of 24j; **no deployed**
application adoption is inferred from test collection or from this library.

**Gate determination: PASS for the in-process reference-host contract and
non-regression tests. NOT a production-host release gate.** The tests establish
cooperative, instance-local invariants, not a cross-host fence, trusted epoch
provenance, process-launch integration, persistence, or fault recovery.
The duplicated-epoch-across-two-hosts test documents an intentionally
unresolved limitation.

## 5. Validation commands on the full fwork checkout

```bash
python -m pytest -q tests/test_application_runtime_host_v0.py
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py \
  tests/test_owned_root_custody_execution_v0.py \
  tests/test_owned_root_execution_dispatch_v0.py \
  tests/test_application_runtime_host_v0.py
python -m pytest -q
python -m search.spk_application_host_audit_v0 --repo . \
  --json-out /tmp/spk-host-integration-audit-24j.json
git diff --check
git status --short
```

The complete regression has now been executed successfully on `fwork` as
reported in section 4. The partial source bundle cannot independently rerun
that complete checkout; therefore this document records reported execution
evidence rather than claiming that all tests ran in the packaging environment.

## 6. Next checkpoint

With the full-checkout regression green, 24j may now be checkpointed **as a reference host**. The
application-adoption gate remains OPEN. The next actual integration task is
to identify a non-fixture provider and the process launcher/consumer and
validate end-to-end traffic. Do not add another authority registry merely
to close a scanner checkbox. Core/Network/Compiler remain frozen.

Five-phase SPK baseline S1=100%, S2=100%, S3=60%, S4=0%, S5=0%:
52% total (equal-weight average), unchanged until stage criteria are reviewed.
