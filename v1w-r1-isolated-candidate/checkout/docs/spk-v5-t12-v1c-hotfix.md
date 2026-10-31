# T12 original service admission hotfix v1c

Additive only. Original T12 and frozen SPK files remain unchanged.

The first T12 native API run rejected a constructed 16/32 service plan with
`PEServiceAdmissionV1c:invalid service plan`. V1c first tests the proven
frozen BV-v0e constructor at pe_slots=3, fabric_slots_per_tick=4, then tests
only original API-produced service plans and original V1c service admissions.
It never handcrafts a successful SPK admission; `admit_memory_v1a` must accept
and the original memory projection/access calls must execute.

If all original candidates reject, T12 still FAILS CLOSED. Candidate-specific
rejection reasons are retained in the diagnostic report. Original execution
memory access, if successful, must not be interpreted as a P-learning grant.

The release launcher retains 23 cumulative manifest checks, the genuine
original BV-v0e preflight, 23 inherited test suites, original file pins,
and byte-identical two-run evidence. End-to-end native-memory calls require
fwork (five original memory modules missing from local partial checkout).
