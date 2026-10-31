# SPK V5 T4ZABC · Differential BV/PE runtime topology correction

Original T4ZAB **FAIL CLOSED**: `C_NOT_EXECUTED_INSIDE_BV_SOURCE`.
The previous research gate assumed original frozen `execute_live_v0e` always
uses frozen `pe_execution_v1b._compute_local` for C. Earlier T3XYZ confirmed
that function on a **separate A1b/T3h path**, not automatically on BV-v0e.

This additive checkpoint preserves all earlier sources and the fail-closed history.
It uses the host CPython profile callback strictly for call graph characterization,
without source monkeypatching. The positive control runs one additional T3h/A1b
execution and must record PE-v1b C compute calls. Exactly 180 genuine BV-v0e
source executions are separately profiled, verified against T4GHI source hashes
and sign observations. Two independent producer processes must output exactly
matching reports. This distinguishes *path not executed* from *observer broken*.

A deterministic SHA-pinned **read-only source handoff** contains copies of the
original frozen PE and BV scheduler Python files. Original T4ZAB code and test
failures are not erased or rewritten.

When the observed BV path bypasses PE-v1b, the gate is considered a successful
**counterexample to the earlier probe assumption**, not a success of PE-owned
semantic messaging. When BV uses PE-v1b, its measured use is reported but remains
untrusted host observation. No native receipts, auth, sensor, blind learning, or
neuronal authority are promoted in either case.

`bash search/spk_v5_t4zabc_topology_correction_gate.sh ~/workspace/spk-evidence/spk-v5-t4zabc-topology.json`

Outputs: `spk-v5-t4zabc-topology.json` and
`spk-v5-t4zabc-frozen-source-handoff.tar.gz` in the same directory.
