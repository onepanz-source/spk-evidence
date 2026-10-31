# T12 v1d original A1d outcome bridge (additive hotfix)

Observed on fwork (v1c): genuine `admit_memory_v1a` succeeded, but the original `project_execution_memory_v1a` rejected an A1b result with `MemoryInvariantV1a: unrecognized A1d outcome`.

The frozen projection consumes an **A1d outcome**: `status=CLOSED` with `result.observations`, or `status=PE_FAULT` with `committed_prefix.observations`. The new bridge **never synthesizes** those wrappers. It locates only functions defined by the original `spk_architecture_v1.pe_fault_v1d` module, invokes a compatible A1d producer with original objects, and checks the A1d result before invoking the frozen memory projection and access authorization. The producer pathname is verified within the repository and its source digest recorded in the output.

Release requires at least one **single episode** to pass original service plan construction, memory admission, original A1d execution, memory projection, and `authorize_projection_v1b`. A count of memory admissions alone is not sufficient. Service admission `serve_projection_v1c` is attempted and independently reported, not confused with learning-P credit.

If the original A1d producer API differs, this gate fails closed with `blocked_stage=original_A1d_execution` and a list of callable signatures and individual rejections. We do not edit or imitate original A1d, and no learning-P grant is claimed. Frozen originals remain SHA protected by inherited cumulative gates. Tests use a **test-only** simulated A1d module as a fixture; it never enters the release runtime and cannot satisfy the pinned-source checks.

Install with `tar --skip-old-files` and run `search/spk_v5_t12_macro_native_memory_seam_gate_v1d.sh <report-path>` from the checkout root. The report is only published after the entire cumulative gate passes.
