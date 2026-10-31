# SPK S3.7d/24h: Application Host Integration Audit v0

**Status: FULL-CHECKOUT STATIC INVENTORY PASS (24h CORRECTED); APPLICATION ADOPTION NOT PROVEN.**
Baseline: `8405f4c` (24g dispatch boundary). The audit adds **no** runtime
execution path and does not modify the frozen Core, Network, Compiler, k24b,
or the 24d–24g modules.

## 1. Question and boundary

24g provides a single-epoch dispatch boundary **for callers that use it**.
It does not imply that there is a top-level host, that all clients pass through
it, or that two independently allocated dispatcher instances cannot process
the same epoch. 24h inventories source-level entrypoint and import evidence
before proposing another layer of enforcement.

We do **not** infer a host from the existence of tests, the existence of the
24g class, a Python module import, or a successfully completed root test.

## 2. Read-only auditor

`search/spk_application_host_audit_v0.py` is an independent, Python standard
library-only AST scanner. It imports **none** of the scanned project's modules.
It records:

- Python source count and a deterministic SHA-256 fingerprint of the files read;
- `if __name__ == '__main__'` entrypoint candidates outside test/research trees,
  excluding the inspected root-level `spk_24d_collect.py` collector while it
  has no static dispatcher/owner references or dynamic invocation;
- declared `project.scripts` / `project.gui-scripts` and Poetry script targets;
- literal references to 24g, distinguishing tests, library and unknown source;
- syntactic hints for dispatcher construction, `install`, and `dispatch`;
- direct source import edges to the old raw owner APIs (24b/24d/24e/24f);
- explicit dynamic import/exec syntax, star imports, AST parsing errors;
- limits requiring manual review for `setup.cfg`, `setup.py` and other hosts;
- `non_application_repository_tools`: exact-path exceptions present in the
  scanned source tree; a change to the excluded tool's imports or calls
  restores its candidacy rather than silently hiding a prospective host.

An `ADOPTION_CANDIDATE_UNVERIFIED` status is **not** a pass for mandatory
host routing. The scanner cannot prove runtime reachability, exclusivity,
control-flow coverage, absence of reflective calls, or process-wide fencing.
`NO_APPLICATION_ADOPTION_EVIDENCE` means nothing was established by the
visible static corpus, **not** that no host exists elsewhere.

Run on the full checkout on `fwork`:

```sh
python -m pytest -q tests/test_spk_application_host_audit_v0.py
python -m search.spk_application_host_audit_v0 \
  --repo . --json-out /tmp/spk-host-integration-audit-24h.json
python -m pytest -q

git diff --check
git status --short
```

Optional **evidence presence** check:

```sh
python -m search.spk_application_host_audit_v0 \
  --repo . --require-adoption-evidence
```

Exit codes: `0` complete inventory (or candidate exists when explicitly
required); `2` no non-test dispatcher source consumer with
`--require-adoption-evidence`; `3` incomplete static scan. None of these codes
is proof of enforcement. The JSON report belongs outside the repository.

## 3. Reconstructed-bundle findings (not the full fwork checkout)

We reconstructed the previously supplied 24d source bundle and overlaid the
24d–24g implementations and updated acceptance documents. This reconstructed
subset contains `spk_simulator`, `docs`, and `tests`; it **does not** contain
the full `fwork` repository (`search`, `spk_core`, `spk_network`,
`spk_architecture`, `spk_compiler`, packaging/host roots). We added the new
24h auditor and its tests to this reconstructed subset before scanning it.

**Source audit findings:**

- No non-test/research source consumer of 24g appears in the reconstructed
  subset; the explicit 24g references are in its implementation and tests.
- Four source modules import raw owner interfaces, all belonging to the
  existing **internal** chain: 24d, 24e, 24f and 24g. These imports do not
  constitute application bypasses by themselves.
- No application host or packaged entrypoint is present in the reconstructed
  subset. This is a **visibility limit**, not proof of absence on `fwork`.
- No global single-dispatcher adoption, privilege isolation or independent
  epoch uniqueness can be claimed on this evidence.

Re-run the script on the full checkout and use **that report** as the source
for any eventual host wiring decision. The static report itself never upgrades
to a global authority guarantee.

## 4. Required host adoption contract (not implemented)

An eventual application host must explicitly own lifecycle and traffic:

1. Resolve and validate one trusted, fresh sealed `OwnedSharedEventCycleStateV0`
   and its actual `epoch_id`. Epoch strings are identifiers, not credentials.
2. Construct/install one `OwnedRootExecutionDispatcherV0` for that epoch in
   a declared authoritative, cooperative host scope; retain it privately.
3. Route all supported client mutations as typed `DispatchRequestV0`
   `ADVANCE` or bounded `RUN`, at the observed `expected_revision`.
4. Expose read-only `SNAPSHOT`, `AUDIT`, and `TRACE` observations instead of
   the raw 24b, 24d, 24e or 24f objects.
5. Reject stale/duplicate requests; handle bounded non-completion and
   errors without fabricating successful commits or resetting the epoch.
6. Refuse new mutations after `CLOSED`; preserve the single existing
   `SERVICE_TIME` and zero-time handoff.
7. Inventory legacy consumers; do not silently reinterpret their old APIs
   as dispatch-governed. Make migration/adoption an explicit deployment step.

These seven obligations require **host-level integration tests**, for example:
client request to dispatch to actual 24g; negative direct-owner attempts inside
the cooperative host adapter; conflicting revision requests; shutdown/closed
behavior; and a verified list of deployed consumer entrypoints. A non-test
`import` or AST construction call alone meets none of these acceptance gates.

## 5. Scope and next gate

**24h acceptance:** reproducible independent inventory, conservative results,
negative tests that reject false adoption evidence, no runtime modifications.
This can be accepted independently of host integration. The next decision is
whether SPK actually needs a concrete application host now, and, if so, which
process/module will own all client traffic. Do not fabricate a host wrapper
merely to create another green test suite.

**Explicit limitations:** no cryptographic legitimacy of the initial epoch;
no guarantee against arbitrary in-process Python; no uniqueness across
independent dispatcher instances or processes; no crash durable authority;
no implicit coverage of shell/native/plugin/dynamically loaded callers.

## 6. Verification record (2026-10-15)

**Full-checkout evidence supplied from `fwork`** (branch
`spk-simulator-compiler-v0`, prior checkpoint `8405f4c`; 24h files still
untracked at the time of the run):

| Verification | Observed result |
| --- | --- |
| Focused auditor tests | **19 passed** |
| Full repository pytest suite | **2,506 passed** in 9.94 seconds |
| Difference from 24g full suite (2,487) | **+19 tests** |
| Static audit status | `NO_APPLICATION_ADOPTION_EVIDENCE` |
| Python files scanned | **357** |
| Source SHA-256 fingerprint | `bf1f8067a87b1225f01b235c9a379693d50a20e679e88cd9dc59a5f282ddef2c` |
| Host candidates | **1 syntactic candidate**: `spk_24d_collect.py` (source collector, *not* an application host) |
| Application dispatcher consumers | **0** |
| Raw-owner importing source modules outside tests | **4** |
| AST parse errors | **0** |
| `git diff --check` | No issues reported |

The focused 19 tests also passed independently on the reconstructed subset;
the full 2,506-test count above is the authoritative integration result from
`fwork`. The JSON report path used on `fwork` was
`/tmp/spk-host-integration-audit-24h.json`.

**Gate decision: 24h STATIC INVENTORY PASS.**
No application adoption or global execution-enforcement proof is claimed.
The one syntactic candidate was subsequently identified from the actual
JSON report: `spk_24d_collect.py`, a read-only source-bundle collection tool.
It is **not an application host** and does not install or dispatch a simulation
epoch. The original audit output above is retained as historical evidence.
An application-wide enforcement gate remains **OPEN**.

## 7. Next decision: host identity before integration

Extract candidate identity and packaging hints from the report:

```sh
python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('/tmp/spk-host-integration-audit-24h.json').read_text())
for key in ('host_candidates', 'packaging_entrypoints',
            'application_dispatcher_candidates', 'raw_owner_importers',
            'limitations'):
    print(f'\n{key}:')
    for item in report.get(key, []):
        print(' ', item)
PY
```

Do not introduce a new host class or modify frozen modules just to make the
adoption status turn green. Once the candidate is identified, verify whether
it is an actual supported application entrypoint, a command-line tool, or a
historical script. If no authoritative host exists, decide its ownership and
runtime scope explicitly before implementation. This decision is outside the
24h acceptance gate.

## 8. Corrigendum following inspection of the full-checkout report

The full-checkout JSON was inspected on `fwork` on 2026-10-15. The sole
`host_candidates` entry was `spk_24d_collect.py`. It only packages source
files and Git diagnostics, and does not own an execution epoch.
`packaging_entrypoints` and `application_dispatcher_candidates` were empty.
The four `raw_owner_importers` were exactly the 24d/24e/24f/24g internal
`spk_simulator` modules. **No actual application host is identified.**

The first scanner version reported the collector as a host candidate purely
because it has a `__main__` guard. This corrigendum limits that false positive
through an **explicit exact-path exception**, `spk_24d_collect.py`, valid only
while no dispatcher or owner references and no dynamic calls are detected.
It does **not** broadly exclude scripts with main guards or similar names;
any such program remains visible in the candidate report. The collector
continues to be hashed and counted as scanned source.

**Independent corrigendum evidence:** 23 focused tests passed locally, up from
19; all 23 passed when run against the reconstructed source tree with the
actual collector present. That scan found 190 Python files, zero host
candidates, zero application dispatcher consumers, four internal raw-owner
importers, and zero parse errors. These are *subset* measurements.

The previous full-checkout fingerprint
`bf1f8067a87b1225f01b235c9a379693d50a20e679e88cd9dc59a5f282ddef2c`
is preserved as the original 19-test evidence. A corrected full-checkout
fingerprint must be obtained by rerunning the auditor on `fwork`; it cannot
be calculated from the partial source bundle. Full pytest regression after
this change is likewise **pending on `fwork`**.

**Decision for 24i:** Do not invent a new executable host or adapter without
an actual application lifecycle, trusted epoch creation source and consumer
interface. 24g remains an opt-in library dispatcher, not an installed
application runtime. A future host integration must define its process
boundary, activation, failure semantics and deployment entrypoint before any
claim that custodian routing is mandatory.


## 9. Final corrected full-checkout verification (2026-10-15)

After the exact-path false-positive correction, the user executed the tests
and read-only auditor on the **full `fwork` checkout**. Results:

| Verification | Observed result |
| --- | --- |
| Focused 24h audit tests | **23 passed** in 0.13 s |
| Full repository pytest suite | **2,510 passed** in 9.76 s |
| Increment over the previous 24h suite | **+4 tests** (2,506 to 2,510) |
| Corrected audit status | `NO_APPLICATION_ADOPTION_EVIDENCE` |
| Scanned Python files | **357** |
| Corrected full-checkout SHA-256 fingerprint | `590181d7af67439e77540b47c440bcc8d02732b10742d668eb88b3e08517ea49` |
| Host candidates | **0** |
| Application dispatcher consumers | **0** |
| Internal raw-owner importing modules | **4** |
| Parse errors | **0** |
| `git diff --check` | No issues reported |

The original fingerprint and initial 19-test figures in section 6 are
historical *pre-corrigendum* evidence, not the current gate result.
This final record supersedes the pending full-checkout verification notice
in section 8. No claim of mandatory runtime adoption is made.

**Final 24h gate: PASS for reproducible static inventory and corrected
false-positive classification; application-host integration remains OPEN.**
There is no verified application host to patch in the examined checkout.
Defining one requires an explicit lifecycle and deployment boundary, not
another wrapper around the existing custody chain.
