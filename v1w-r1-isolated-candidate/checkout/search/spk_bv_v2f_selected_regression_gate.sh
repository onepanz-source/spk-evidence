#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Curated independent-import suite. Early native fixture/codec tests must run
# from their owning frozen native gates; v1n has isolated cross-test imports.
files=(
  "tests/test_spk_bv_v0y_judgment_contract.py"
  "tests/test_spk_bv_v0z_shadow_update.py"
  "tests/test_spk_bv_v1a_symbolic_holdout.py"
  "tests/test_spk_bv_v1b_native_operator_replay.py"
  "tests/test_spk_bv_v1c_native_sensitivity.py"
  "tests/test_spk_bv_v1d_native_criterion.py"
  "tests/test_spk_bv_v1e_receiver_impact.py"
  "tests/test_spk_bv_v1f_receiver_preference.py"
  "tests/test_spk_bv_v1g_native_route_lineage.py"
  "tests/test_spk_bv_v1i_native_feedback_silence.py"
  "tests/test_spk_bv_v1j_silence_observability.py"
  "tests/test_spk_bv_v1k_witness_authority.py"
  "tests/test_spk_bv_v1l_two_port_observer.py"
  "tests/test_spk_bv_v1m_native_passive_projection.py"
  "tests/test_spk_bv_v1o_decision_disclosure.py"
  "tests/test_spk_bv_v1p_native_causal_locus.py"
  "tests/test_spk_bv_v1q_native_factorial_interactions.py"
  "tests/test_spk_bv_v1r_allocation_boundary.py"
  "tests/test_spk_bv_v1s_receiver_disclosure_channel.py"
  "tests/test_spk_bv_v1t_native_trace_mailbox_adapter.py"
  "tests/test_spk_bv_v1u_incremental_shadow_channel.py"
  "tests/test_spk_bv_v1v_frozen_observation_surface.py"
  "tests/test_spk_bv_v1w_observation_seam.py"
  "tests/test_spk_bv_v1x_reference_observation_port.py"
  "tests/test_spk_bv_v1y_native_external_probe.py"
  "tests/test_spk_bv_v1z_native_observer_admission.py"
  "tests/test_spk_bv_v2a_versioned_executor.py"
  "tests/test_spk_bv_v2b_differential_boundary.py"
  "tests/test_spk_bv_v2c_temporal_differential.py"
  "tests/test_spk_bv_v2d_native_holdout_differential.py"
  "tests/test_spk_bv_v2e_native_admission_discrimination.py"
  "tests/test_spk_bv_v2f_integrated_milestone.py"
)
echo '[1/2] Selected independent BV regression with stable import boundaries'
python -m pytest -q --import-mode=importlib "${files[@]}"
echo '[2/2] SOURCE-OWNED BATCH AND RECEIVER FEEDBACK: SELECTED REGRESSION PASS'
