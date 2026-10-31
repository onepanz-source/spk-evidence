# T10JKL/MNO/PQR · Reference V1 P Resource Contract

Additive research-only checkpoint following T10ABC/DEF/GHI.

* `resource_authority_v1.py`: SQLite resource manifest, exact reference P scope, quota guard and versioned profile transitions.
* `cumulative_resource_gate.py`: deterministic behavior comparisons against source-pinned T10 and negative witnesses.
* `tests/test_resource_authority_v1.py`: functional, transactional, restart, quota and corruption tests.
* `reference/t10abc-def-ghi-cumulative.json`: byte-pinned prior source report.
* `../../docs/spk-v1-bounded-P-resource-admission-reference.md`: design and limitations.
* `../../search/spk_v5_t10jkl_mno_pqr_cumulative_gate.sh`: strict release gate.

No package requires modifications to frozen SPK components or previously released milestones. Reference grants and authorization are host-controlled and not native.
