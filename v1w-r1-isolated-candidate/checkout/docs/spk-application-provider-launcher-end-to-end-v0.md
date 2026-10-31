# SPK S3.7d/24k: Offline Provider + Launcher End-to-End v0

**Status: INTEGRATION PASS – finite offline reference scope (2026-10-15).**

Baseline Git: `f7328d0` (24j reference host committed). Frozen Core v0,
Network v0 and Compiler v0 are not modified; neither are k24b and 24d–24j.

## Intent and honest scope

One cohesive development cycle: provider adapter, offline command-line launcher,
real fixture demonstration, negative tests, and documented integration gate.
No new ownership layer, no new service clock, no sockets, persistence, lease,
process fence, automatic rollback, or global uniqueness guarantee.

This **is** an executable consumer of `ApplicationRuntimeHostV0`, not merely a
library with no caller. The executable is a **local, explicit-trust, finite
reference launcher**, not an application deployment host with an authenticated
sensor/epoch provider. H10 and production H11 remain OPEN.

## Implemented modules

1. `spk_simulator/application_epoch_provider_v0.py`:
   `SingleUseSealedEpochProviderV0(epoch, source_id=...)`, in-memory one-time
   callable provider. Revalidates canonical epoch structure before issuance,
   rejects repeat issuance, serializes concurrent issuance. Its `source_id`
   is an informative label, not an authentication credential. The caller
   keeps its original epoch object and can trivially construct another
   provider; no global exclusion is claimed.
2. `search/spk_application_runtime_launcher_v0.py`: executable local offline
   host consumer with `--provider module.path:factory --epoch-id --max-actions
   --chunk-size`. The selected factory is *trusted executable local Python*
   supplied by the operator, runs once, and returns the initial
   `OwnedSharedEventCycleStateV0`. This is not an untrusted plugin sandbox.
   No test module is imported by the launcher itself.
3. `tests/spk_offline_demo_epoch_v0.py`: explicitly **lab-only** provider using
   the project's real finite-root fixtures, with a quiet Core C threshold.
   It begins with unconfirmed service, no consumed inputs, no fabricated P/S,
   no prepared Core state, and real service proceeds through the dispatcher.
   This is not a physical-device or production provenance source.
4. `tests/test_application_runtime_launcher_v0.py`: positive and negative
   unit/integration tests for provider, CLI, budget, completion, failure,
   concurrency, and end-to-end commit.
5. `search/spk_24k_final_gate_v0.sh`: a single explicit integration gate
   including complete/incomplete CLI return-code checks and full regression.

## Live demonstration on fwork

```bash
python -m search.spk_application_runtime_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --epoch-id E0 --max-actions 100 --chunk-size 6
```

The program produces one JSON object and exits with:

- `0`: **CLOSED** with verified output-free S commit, version 0 → 1;
- `3`: **INCOMPLETE**, budget exhausted without receipt; there is NO
  persistent continuation across process exit;
- `2`: **ERROR**, no fabricated success; previously executed service may
  already have occurred inside the now-abandoned process. If failure follows
  admission, JSON includes the last observable phase/revision/service tick
  (or an explicit observation error); this is a diagnostic, not recovery.

The launcher obtains each subsequent revision only from the accepted RUN
response (via a new explicit request). It never retries a stale revision,
constructs an owner directly, synthesizes a service tick, or reopens an epoch.
Every completed run verifies the 24g `AUDIT` observation and checks:

- one handoff, costing zero SERVICE_TIME;
- all other actions each spend one SERVICE_TIME;
- final result revision equals total actions;
- closed terminal has an output-free receipt and exactly +1 version.

An incomplete launcher run ends the only local host without persisting it.
A subsequent process invocation creates a *new* local host, **not** recovery of
the previously progressed epoch; repeated invocation can duplicate authority.
The `module:factory` path is trusted user-supplied Python and executes code
at import/call time; do not use it with externally supplied untrusted values.

## H01–H12 gate notes

| ID | Assessment from 24k implementation | Remaining limits |
| --- | --- | --- |
| H01 | Executable offline entrypoint invokes 24j `admit` / `RUN` / `AUDIT` on actual shared epoch | Not an always-on production application |
| H02 | Canonical initial state checked by provider and 24j | No source authentication |
| H03 | One host per invocation; one provider issuance | Distinct invocations may reuse the same epoch |
| H04 | In-process provider issuance serialized; host CAS inherited from 24j | No global writer fence |
| H05 | Explicit bounded chunks, total finite action budget; incomplete exit 3 | No crash/restart resume |
| H06 | Real root→handoff→terminal commit demo & tests | Only output-free single-root scenario |
| H07 | Failure distinct from completion; no rollback claims | Host error may follow accepted substeps |
| H08 | Incomplete sessions halted in-process; CLOSED read-only | No durable recovery |
| H09 | Launcher uses only 24j public API, not raw owner APIs | Cooperative, not Python sandbox |
| H10 | Demo and selected factory names explicit | **OPEN: real trusted sensor/provider origin** |
| H11 | One process per invocation, single epoch per host | **OPEN: uniqueness across processes and actual deployment** |
| H12 | Full regression and six-stage integration gate on fwork | **PASS** |

24h scanner may see the launcher's `__main__` as a host candidate, but its
`application_dispatcher_consumers` count is based on direct 24g construction.
A launcher correctly using 24j need not instantiate 24g directly. Do not
misinterpret a count of zero as proof that the launcher bypasses 24j.

## Gate commands on fwork

Preferred single-session gate:

```bash
bash search/spk_24k_final_gate_v0.sh
```

Equivalent manual verification:

```bash
python -m pytest -q tests/test_application_runtime_launcher_v0.py
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py \
  tests/test_owned_root_custody_execution_v0.py \
  tests/test_owned_root_execution_dispatch_v0.py \
  tests/test_application_runtime_host_v0.py \
  tests/test_application_runtime_launcher_v0.py
python -m search.spk_application_runtime_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --epoch-id E0 --max-actions 100 --chunk-size 6
python -m pytest -q
git diff --check
git status --short
```

A failure in any command blocks promotion. Only after fwork results should
acceptance evidence and staged commit be produced. Keep out of staging:
`search/core_temporal_depth5_v1.py`,
`search/core_temporal_quotient_alignment_v0.py`, `spk_24d_collect.py`.

## SPK progression

The last certified baseline remains S1=100%, S2=100%, S3=60%, S4=0%, S5=0%:
52% average with equal phase weights. 24k is a substantive but not yet gated
integration milestone. Next stage is a *criteria-based* S3 recalibration and
provider trust/authority design, rather than another custody-wrapper layer.

## Certified fwork integration gate – 2026-10-15

Baseline: f7328d0.

- Provider and launcher: 43 passed.
- Root-to-launcher integration: 260 passed.
- Full repository regression: 2592 passed.
- Complete demo: EXIT 0, CLOSED, version 0 -> 1.
- Accounting: 6 actions, 5 SERVICE_TIME ticks, 1 zero-tick handoff.
- Limited demo: EXIT 3, INCOMPLETE, no commit receipt.
- Whitespace and working-tree checks: PASS.

Acceptance applies only to the local finite reference execution.

Not established: authenticated production input provenance,
cross-process exclusive ownership, durable restart or crash recovery.
