# SPK BV v1n.1 — Isolated Test Fixture Import Hotfix

## Defect reproduced

Running `python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1n_receiver_knowledge_disclosure.py`
against the original v1n archive fails during collection:

`ModuleNotFoundError: No module named 'test_spk_bv_v1m_native_passive_projection'`.

The v1n test file accidentally imports two ordinary helpers (`specimen`, `canon`) from
an unrelated pytest module by unqualified name. This depends on how pytest prepends
module directories to `sys.path` and can fail on fwork even when the v1m source exists.

## Correction

The *tests only* now own a private, byte-equivalent synthetic fixture, transcribed
from the preceding v1m test. The fixture still reuses the same v1m production
`analyze` routine, kernel-projection and route-audit helpers. No research implementation,
CLI, previous gate, frozen runtime, or architecture file is changed.

## Verification

- Run v1n tests in isolated pytest import mode (regression for the original failure).
- Run v1m inherited tests in isolated import mode (fixture equivalence).
- Run the original v1n gate (including all inherited gates and architecture custody).
- Native v1n replay remains a separate fwork command, with the original output
  location unchanged. This hotfix neither creates new native evidence nor authorizes
  endogenous receiver judgment, causal credit, an update or learning.

## Safety and versioning

Research-only overlay. Does not modify SPK Core/Network/Compiler/Architecture freezes.
