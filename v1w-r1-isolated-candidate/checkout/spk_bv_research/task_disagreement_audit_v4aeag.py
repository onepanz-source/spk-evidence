"""Source-bound native reexecution and auditable v4ae-v4ag disagreement escrow."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.grant_rank_integration_v3tuv import ARMS, CAPACITIES, NEW_SCHEDULES
from spk_bv_research.native_actor_objective_v4yzaa import OBJECTIVE
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.task_oracle_fixture_v4abad import VARIANTS as PRIOR_VARIANTS
from spk_bv_research.task_disagreement_v4aeag import (
    SCHEMA, STATUS, digest, expected_vote,
)
from spk_bv_research.task_disagreement_fixture_v4aeag import (
    VARIANTS, VERDICTS, project_actual_native, run_variant,
)

SIGNED_V3_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4ABAD_SHA = '2c5d2971a1df638d00341dd91c39e1f3a1212c712dd7a97641601fb876e043bf'


def require(condition, description):
    if not condition:
        raise CausalProbeRejected(description)


def audit_row(row, projections, source_key, original_sha, parent, issued,
              completed):
    require(type(row) is dict and row == run_variant(
        projections, source_key, original_sha, parent, issued, completed,
        row['variant']), 'two view report witness was forged')


def evaluate(v3, raw3, previous, raw_previous, *, fixture_fn=fixture,
             native_executor=execute_live_v0e):
    require(type(v3) is dict and type(previous) is dict and
            type(raw3) is bytes and type(raw_previous) is bytes and
            canon(v3) == raw3 and canon(previous) == raw_previous and
            sha256(raw3).hexdigest() == SIGNED_V3_SHA and
            sha256(raw_previous).hexdigest() == SIGNED_V4ABAD_SHA and
            previous['signed_v3tuv_sha256'] == SIGNED_V3_SHA and
            previous['precommitted_task_canary_labels'] == {'0': 1, '1': 0} and
            previous['program_adoptions'] == 0 and
            previous['native_learning_implemented'] is False and
            previous['totals']['signed_native_replays'] == 18 and
            previous['totals']['provenance_scenarios'] == 216 and
            previous['totals']['verdict_VETO_SEMANTIC_CANARY_CONFLICT'] == 18,
            'signed two-view predecessor/canary drift')
    require(OBJECTIVE['expected_terminal_counts'] == {'0': 1, '1': 0},
            'previous task labels changed')
    parent = sha256(raw_previous).hexdigest()
    totals = Counter()
    rows = []
    evaluated = 0
    for signed, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(signed['schedule'] == schedule and
                signed['source_external_ticks'] == list(ticks),
                'signed two-view schedule mismatch')
        case, fabric, plans = fixture_fn(ticks=ticks)
        for signed_mode, (mode, enabled, priority) in zip(signed['modes'], ARMS):
            require(signed_mode['mode'] == mode,
                    'signed two-view mode mismatch')
            for signed_capacity, capacity in zip(signed_mode['capacities'], CAPACITIES):
                require(signed_capacity['native_PE_capacity'] == capacity,
                        'signed two-view fabric capacity mismatch')
                pp = replace(plans[1], fabric_slots_per_tick=capacity)
                active_plans = (plans[0], pp, plans[2], plans[3])
                bv = LiveBVPlanV0e(enabled=enabled, priority=priority)
                original = native_executor(case, fabric, *active_plans, bv)
                source_sha = snapshot(original)
                require(source_sha == signed_capacity['original_native_sha256'],
                        'signed native replay drift in two-view gate')
                old = previous['scenarios'][evaluated * len(PRIOR_VARIANTS)]
                require(old['schedule'] == schedule and old['mode'] == mode and
                        old['native_global_PE_capacity'] == capacity and
                        old['witness']['variant'] == 'valid_quorum' and
                        old['witness']['decision']['verdict'] ==
                        'ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST',
                        'prior role-attestation source mismatch')
                projections, completed = project_actual_native(
                    case, fabric, active_plans, bv,
                    native_executor=native_executor)
                for view in ('endpoint', 'emission'):
                    require(expected_vote(projections[view], {'0': 0, '1': 1}) ==
                            ('REGRESSES', 4, 9),
                            'wrong-label indistinguishability control drift')
                source_key = f'{schedule}/{mode}/{capacity}'
                totals['signed_native_replays'] += 1
                totals['counterfactual_native_probe_executions'] += 4
                totals['same_observation_opposite_task_label_interpretations'] += 1
                for variant in VARIANTS:
                    witness = run_variant(projections, source_key,
                                          source_sha, parent,
                                          case.events[0].timestamp,
                                          completed, variant)
                    audit_row(witness, projections, source_key, source_sha,
                              parent, case.events[0].timestamp, completed)
                    verdict = witness['decision']['verdict']
                    require(verdict == VERDICTS[variant] and
                            witness['decision']['program_adopted'] is False and
                            witness['decision']['promotion_authorized'] is False and
                            witness['decision']['native_learning_implemented'] is False,
                            'unfounded two-view research adoption')
                    totals['adjudication_scenarios'] += 1
                    totals['verdict_' + verdict] += 1
                    rows.append({'schedule': schedule, 'mode': mode,
                                 'native_global_PE_capacity': capacity,
                                 'witness': witness})
                evaluated += 1
    require(len(v3['source_matrix']) == 3 and evaluated == 18 and
            totals['signed_native_replays'] == 18 and
            totals['counterfactual_native_probe_executions'] == 72 and
            totals['same_observation_opposite_task_label_interpretations'] == 18 and
            totals['adjudication_scenarios'] == 18 * len(VARIANTS) and
            all(totals['verdict_' + VERDICTS[v]] >= 18 for v in VARIANTS),
            'two-view source matrix or conflict coverage incomplete')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4abad_sha256': parent,
        'precommitted_synthetic_canary': OBJECTIVE['expected_terminal_counts'],
        'views': {
            'endpoint': 'forward.terminal -> bounded C/channel7 counter',
            'emission': 'forward.emissions -> filtered C/channel7 counter',
            'independence': 'DISTINCT_EXTRACTION_PATHS_SAME_NATIVE_RUN_CORRELATED',
        },
        'test_attestation': 'PUBLIC_EMBEDDED_HMAC_KEYS_NOT_EXTERNAL_IDENTITY',
        'epistemic_limit': 'UNANIMITY_ON_CORRELATED_TRACES_DOES_NOT_PROVE_TASK_TRUTH',
        'observation_underdetermination': {
            'same_native_view_counts': [1, 1, 1, 0],
            'pinned_labels': {'0': 1, '1': 0},
            'pinned_costs': [4, 0],
            'opposite_labels': {'0': 0, '1': 1},
            'opposite_costs': [4, 9],
            'semantic_claim': 'SAME_OBSERVATION_CAN_REVERSE_OBJECTIVE_RANKING',
            'which_labels_are_real_world_true': 'UNKNOWN',
        },
        'replay_protection': 'TRANSIENT_IN_MEMORY_ONLY',
        'tested_variants': list(VARIANTS), 'totals': dict(sorted(totals.items())),
        'scenario_roots_sha256': digest(rows), 'scenarios': rows,
        'research_consensus_only': totals['verdict_CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST'],
        'reviewer_conflicts_quarantined': totals['verdict_QUARANTINE_REVIEWER_DISAGREEMENT'],
        'reviewer_abstentions_quarantined': totals['verdict_QUARANTINE_ABSTENTION'],
        'program_adoptions': 0, 'native_learning_implemented': False,
        'native_v0e_modified': False, 'architecture_v1_modified': False,
        'claims_excluded': [
            'projection diversity is not sensor, organization or ground-truth independence',
            'test HMAC keys do not authenticate production reviewers',
            'two reviewers may share the same wrong task definition',
            'transient replay/escrow custody cannot survive restarts',
            'no algorithm promotion, native learning, generalization or physical costs',
        ],
        'next_gate': 'INDEPENDENT_GROUND_TRUTH_AND_DURABLE_REVIEW_PROVENANCE_REQUIRED',
    }
