"""BV v0x: source-attested *observability boundary* for workload v0w.

Does not create a judgment, reward, adaptation, or causal credit claim.
No simulator mutation; read-only negative-control interpretation.
"""
from __future__ import annotations

from collections import Counter
from spk_bv_research.workload_sensitivity_v0w import (
    SCHEMA as W_SCHEMA, STATUS as W_STATUS, WORKLOADS, CAPACITY_PROFILES,
)

SCHEMA = 'spk-bv-workload-value-observability-boundary/v0x'
STATUS = 'REPORT_ONLY_COST_OBSERVABILITY_NO_INFORMATIONAL_BENEFIT_IDENTIFICATION'
ARMS = ('off', 'on_forward_first', 'on_feedback_first')
COSTS = ('bv_link_grants', 'bv_service_units', 'bv_memory_units',
         'timeline_link_unit_sum', 'timeline_service_unit_sum',
         'timeline_memory_unit_sum', 'feedback_grant_wait_sum',
         'forward_grant_wait_sum')
RESTRICTIONS = [
    'source-attestation-does-not-infer-judgment-truth',
    'forward-payload-conservation-does-not-prove-feedback-useless',
    'native-feedback-has-no-program-update-in-this-v0e-reference',
    'no-learned-performance-or-counterfactual-learning-benefit',
    'no-independent-replicates-repeated-episodes-share-one-fixture',
    'native-ticks-and-grants-are-not-hardware-latency-or-energy',
    'single-bounded-three-neuron-workload-not-N-node-scalability',
    'not-v0h-528-stress-equivalence', 'no-architecture-promotion',
]

class BoundaryError(ValueError):
    pass


def check(ok, message):
    if not ok:
        raise BoundaryError(message)


def natural(value, label):
    check(type(value) is int and value >= 0, f'{label} must be nonnegative integer')
    return value


def validate(report):
    check(type(report) is dict and report.get('schema') == W_SCHEMA and
          report.get('status') == W_STATUS, 'not native v0w workload report')
    check(report.get('same_fixture_before_after_every_run') is True,
          'fixture invariance not verified')
    check(report.get('variation_scope') == 'external_event_timestamps_and_episode_repetition_only',
          'unexpected experiment variation')
    check(report.get('v0v_reference_check', {}).get('status') ==
          'THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED' and
          report['v0v_reference_check'].get('v0v_v0u_v0t_v0o_chain') is True,
          'baseline chain missing')
    check(type(report.get('source_sha256')) is dict and
          len(report['source_sha256']) == 3 and
          all(type(x) is str and len(x) == 64 for x in report['source_sha256'].values()),
          'missing source pins')
    check(type(report.get('cells')) is list and
          len(report['cells']) == len(WORKLOADS) * len(CAPACITY_PROFILES),
          'incomplete native workload grid')
    seen = set()
    for cell in report['cells']:
        check(type(cell) is dict and cell.get('status') == 'COMPLETE_THREE_ARM_WORKLOAD_CELL',
              'incomplete workload cell')
        key = (cell.get('workload'), cell.get('fabric_slots_per_tick'),
               cell.get('max_inflight_occurrences'))
        check(key in {(w, f, i) for w in WORKLOADS for f, i in CAPACITY_PROFILES},
              'unexpected workload/capacity')
        check(key not in seen, 'duplicate workload cell')
        seen.add(key)
        check(type(cell.get('shared_cell_input_sha256')) is str and
              len(cell['shared_cell_input_sha256']) == 64, 'cell input hash absent')
        runs = cell.get('runs')
        check(type(runs) is dict and set(runs) == set(ARMS), 'not three arms')
        off, fw, bv = (runs[a] for a in ARMS)
        for label, arm in runs.items():
            check(type(arm) is dict and type(arm.get('metrics')) is dict,
                  f'{label}: missing metric records')
            check(type(arm.get('last_forward_terminal_tick')) is int and
                  type(arm.get('whole_result_sha256')) is str and
                  len(arm['whole_result_sha256']) == 64, f'{label}: invalid run identity')
            check(type(arm.get('contention_by_reason')) is dict and
                  all(type(k) is str and type(v) is int and v >= 0
                      for k,v in arm['contention_by_reason'].items()),
                  'native contention reasons invalid')
            for k in COSTS + ('feedback_assessments', 'feedback_deliveries',
                               'forward_batches', 'forward_terminal',
                               'feedback_link_grants', 'feedback_unique_receiver_votes',
                               'fabric_link_contention'):
                natural(arm['metrics'].get(k), f'{label}.{k}')
            check(arm['contention_by_reason'].get('fabric_link', 0) ==
                  arm['metrics']['fabric_link_contention'], 'fabric contention differs')
        check(off.get('enabled') is False and fw.get('enabled') is True and
              bv.get('enabled') is True and fw.get('priority') == 'forward-first' and
              bv.get('priority') == 'feedback-first', 'invalid OFF/ON intervention labels')
        check(all(off['metrics'][k] == 0 for k in
                  ('feedback_assessments', 'feedback_deliveries', 'feedback_link_grants',
                   'bv_link_grants', 'bv_service_units', 'bv_memory_units',
                   'feedback_unique_receiver_votes')), 'OFF generated feedback')
        for arm in (fw, bv):
            for name in ('forward_states_sha256',
                         'forward_emission_payload_multiset_sha256',
                         'forward_terminal_payload_multiset_sha256'):
                check(arm.get(name) == off.get(name) and type(arm.get(name)) is str,
                      'forward payload/state divergence: '+name)
            check(arm['metrics']['forward_terminal'] == off['metrics']['forward_terminal'] and
                  arm['metrics']['forward_batches'] == off['metrics']['forward_batches'],
                  'forward workload count drift')
        check(fw['metrics']['feedback_deliveries'] == bv['metrics']['feedback_deliveries'] and
              fw['metrics']['feedback_assessments'] == bv['metrics']['feedback_assessments'],
              'ON payload count drift')
        check(type(cell.get('interventions')) is dict and
              all(cell['interventions'].get(k, {}).get('state_hash_equal') is True and
                  cell['interventions'][k].get('emission_payload_multiset_equal') is True and
                  cell['interventions'][k].get('terminal_payload_multiset_equal') is True
                  for k in ('toggle_enabled_only', 'change_priority_only',
                            'off_to_feedback_first_combined')),
              'intervention invariants absent')
    check(seen == {(w,f,i) for w in WORKLOADS for f,i in CAPACITY_PROFILES},
          'missing or duplicated workload cells')
    return report


def summarize(report):
    validate(report)
    rows = []
    reasons = Counter()
    positive_delay = 0
    total_extra_link = 0
    for c in report['cells']:
        off, fw, fb = (c['runs'][a] for a in ARMS)
        diff_fw = fw['last_forward_terminal_tick'] - off['last_forward_terminal_tick']
        diff_fb = fb['last_forward_terminal_tick'] - off['last_forward_terminal_tick']
        check(diff_fw >= 0 and diff_fb >= 0, 'negative last-output delay: audit assumption invalid')
        for a in (fw, fb):
            for reason, count in a['contention_by_reason'].items():
                reasons[reason] += count
        positive_delay += diff_fb > 0
        link_extra = fw['metrics']['timeline_link_unit_sum'] - off['metrics']['timeline_link_unit_sum']
        check(link_extra == fw['metrics']['bv_link_grants'] and
              link_extra == fb['metrics']['bv_link_grants'],
              'feedback grants != abstract incremental link units')
        total_extra_link += link_extra
        rows.append({
            'workload': c['workload'],
            'fabric_slots_per_tick': c['fabric_slots_per_tick'],
            'max_inflight_occurrences': c['max_inflight_occurrences'],
            'stimulus_timestamps': c['stimulus_timestamps'],
            'feedback_assessments': fw['metrics']['feedback_assessments'],
            'feedback_deliveries': fw['metrics']['feedback_deliveries'],
            'last_output_off_tick': off['last_forward_terminal_tick'],
            'last_output_forward_first_tick': fw['last_forward_terminal_tick'],
            'last_output_feedback_first_tick': fb['last_forward_terminal_tick'],
            'forward_first_delay_vs_off': diff_fw,
            'feedback_first_delay_vs_off': diff_fb,
            'added_link_units_per_on_arm': link_extra,
            'added_service_units_per_on_arm': fw['metrics']['bv_service_units'],
            'added_memory_units_per_on_arm': fw['metrics']['bv_memory_units'],
            'contention_forward_first': fw['contention_by_reason'],
            'contention_feedback_first': fb['contention_by_reason'],
        })
    return {
        'schema': SCHEMA, 'status': STATUS,
        'input_v0w_schema': W_SCHEMA,
        'input_fixture_sha256': report['original_fixture_sha256'],
        'input_source_sha256': report['source_sha256'],
        'native_cells': len(rows),
        'native_arms_examined': len(rows)*3,
        'forward_outcome_conservation_cells': len(rows),
        'forward_first_zero_delay_cells': sum(r['forward_first_delay_vs_off']==0 for r in rows),
        'feedback_first_positive_delay_cells': positive_delay,
        'feedback_first_zero_delay_cells': len(rows)-positive_delay,
        'aggregate_link_grants_across_repeated_capacity_cells_not_independent_trials': total_extra_link,
        'contention_attempt_counters_across_cells_not_independent_trials': dict(sorted(reasons.items())),
        'rows': rows,
        'observed_forward_information_benefit': 'NOT_IDENTIFIABLE_WITHOUT_JUDGMENT_AND_ACTION',
        'why_not_identifiable': {
            'feedback_data': 'v0e packet records carry assessment/evidence lineage, not a scored judgment',
            'action': 'v0e does not apply feedback to the neuron program or state update rule',
            'evaluation': 'no independent objective, next-episode intervention or held-out loss defined',
        },
        'required_next_contract': {
            'judgment': ['assessment_criterion','value','source_evidence','receiver','availability_tick'],
            'decision': ['neuron_id','predecision_state','candidate_operator','decision_tick'],
            'update': ['eligibility_window','proposed_delta','bounded_commit_or_noop'],
            'evaluation': ['predeclared_external_score','paired_no_feedback_control','next_episode'],
        },
        'claims_excluded': RESTRICTIONS,
    }
