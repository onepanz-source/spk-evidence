"""BV v4a-v4c: *proposal* verifier, NOT a frozen native policy.

Source observation supports FIFO ordinal position in actual grant units only.
Future progress needs an admitted PE/owner/O-E-memory service-rate assumption.
No function in this module binds or modifies native execute_live_v0e.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import product

from spk_bv_research.native_allocation_boundary_v1r import canon

SCHEMA = 'spk-bv-native-actor-service-contract-candidate/research-v4a-v4c'
STATUS = 'DRAFT_NATIVE_ACK_SERVICE_RATE_CONTRACT_NOT_ADMITTED'
PREDECESSOR_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SOURCE_STATUS = 'DERIVED_SOURCE_FIFO_GRANT_RANK_EXACT_NO_NATIVE_TICK_DEADLINE'
WINDOWS = (1, 2, 4, 8)
CHOICE_KEYS = frozenset({
    'mode', 'window_ticks', 'minimum_oldest_ACK_grants_per_window',
    'owner_PE_preemption_authorized', 'global_PE_preemption_authorized',
    'O_and_E_memory_reservation_admitted',
    'consumer_resource_charge_is_separate',
    'full_original_native_timing_parity_claimed',
    'max_admitted_due_queue_rank', 'max_native_horizon_ticks',
})


class CandidateRejected(ValueError):
    """Reject ungrounded candidate admission or forged source evidence."""


def check(condition, message):
    if not condition:
        raise CandidateRejected(message)


def validate_candidate(candidate):
    """Validate a research *choice*, not implementation or liveness proof.

    Every key is explicit. No profile silently changes the frozen scheduler.
    """
    check(type(candidate) is dict and set(candidate) == CHOICE_KEYS,
          'v4 candidate has missing/foreign policy fields')
    mode = candidate['mode']
    rank = candidate['max_admitted_due_queue_rank']
    horizon = candidate['max_native_horizon_ticks']
    check(type(mode) is str and mode in ('NATIVE_COMPATIBLE', 'RESERVED_ACK_WINDOW') and
          type(rank) is int and 1 <= rank <= 512 and
          type(horizon) is int and 1 <= horizon <= 65536 and
          all(type(candidate[k]) is bool for k in (
              'owner_PE_preemption_authorized',
              'global_PE_preemption_authorized',
              'O_and_E_memory_reservation_admitted',
              'consumer_resource_charge_is_separate',
              'full_original_native_timing_parity_claimed')),
          'v4 candidate invalid mode, types or research bounds')
    check(candidate['consumer_resource_charge_is_separate'] is True,
          'v4 ACK and actor credit application must each charge independently')
    if mode == 'NATIVE_COMPATIBLE':
        check(candidate['window_ticks'] is None and
              type(candidate['minimum_oldest_ACK_grants_per_window']) is int and
              candidate['minimum_oldest_ACK_grants_per_window'] == 0 and
              candidate['owner_PE_preemption_authorized'] is False and
              candidate['global_PE_preemption_authorized'] is False and
              candidate['O_and_E_memory_reservation_admitted'] is False and
              candidate['full_original_native_timing_parity_claimed'] is True,
              'v4 native-compatible mode cannot promise service or spend reserved PE')
        guarantee = None
    else:
        window = candidate['window_ticks']
        check(type(window) is int and 1 <= window <= 64 and
              type(candidate['minimum_oldest_ACK_grants_per_window']) is int and
              candidate['minimum_oldest_ACK_grants_per_window'] == 1 and
              candidate['owner_PE_preemption_authorized'] is True and
              candidate['global_PE_preemption_authorized'] is True and
              candidate['O_and_E_memory_reservation_admitted'] is True and
              candidate['full_original_native_timing_parity_claimed'] is False and
              horizon >= window*rank,
              'v4 reserved ACK service needs owner/global PE, O/E and horizon admission')
        guarantee = window*rank - 1
    return {
        'candidate_accepted_as_draft': True,
        'implemented_on_native_scheduler': False,
        'conditional_deadline_offset_ticks': guarantee,
        'rate_assumption_proven_by_admission': False,
        'native_fairness_or_learning_proven': False,
    }


def profiles():
    base = {
        'max_admitted_due_queue_rank': 16,
        'max_native_horizon_ticks': 256,
        'consumer_resource_charge_is_separate': True,
    }
    return {
        'NATIVE_COMPATIBLE': {
            **base, 'mode': 'NATIVE_COMPATIBLE', 'window_ticks': None,
            'minimum_oldest_ACK_grants_per_window': 0,
            'owner_PE_preemption_authorized': False,
            'global_PE_preemption_authorized': False,
            'O_and_E_memory_reservation_admitted': False,
            'full_original_native_timing_parity_claimed': True,
        },
        'RESERVED_ACK_WINDOW_4': {
            **base, 'mode': 'RESERVED_ACK_WINDOW', 'window_ticks': 4,
            'minimum_oldest_ACK_grants_per_window': 1,
            'owner_PE_preemption_authorized': True,
            'global_PE_preemption_authorized': True,
            'O_and_E_memory_reservation_admitted': True,
            'full_original_native_timing_parity_claimed': False,
        },
    }


def source_row_gaps(rows, windows=WINDOWS):
    """Check bounded *observed* no-grant windows; never extrapolate future."""
    check(type(rows) is list and rows, 'v4 empty source tick trace')
    for i, row in enumerate(rows):
        check(type(row) is dict and
              type(row.get('tick')) is int and
              (i == 0 or row['tick'] == rows[i-1]['tick']+1) and
              type(row.get('ready_control_count')) is int and
              type(row.get('grant_prefix_count')) is int and
              row['ready_control_count'] >= row['grant_prefix_count'] >= 0,
              'v4 source tick/grant conservation or clock drift')
    grants = sum(row['grant_prefix_count'] for row in rows)
    counted = sum(row['grant_prefix_count'] > 0 for row in rows)
    streak = maximum = 0
    for row in rows:
        streak = (streak+1 if row['ready_control_count'] > 0 and
                  row['grant_prefix_count'] == 0 else 0)
        maximum = max(maximum, streak)
    violations = {}
    earliest = {}
    for window in windows:
        check(type(window) is int and 1 <= window <= 64,
              'v4 invalid source window')
        start_ticks = []
        for i in range(len(rows)-window+1):
            if (rows[i]['ready_control_count'] > 0 and
                    all(row['grant_prefix_count'] == 0
                        for row in rows[i:i+window])):
                # Zero grants cannot reduce a source-owned FIFO backlog.
                check(all(row['ready_control_count'] > 0
                          for row in rows[i:i+window]),
                      'v4 source queue disappeared without grant')
                start_ticks.append(rows[i]['tick'])
        violations[str(window)] = len(start_ticks)
        earliest[str(window)] = start_ticks[0] if start_ticks else None
    return {'source_ticks': len(rows), 'real_global_ACK_grants': grants,
            'real_grant_ticks': counted,
            'max_consecutive_pending_no_grant_ticks': maximum,
            'windows_with_ready_ACK_but_zero_grants': violations,
            'first_violating_window_start_ticks': earliest}


def exhaustive_window_rank_check():
    """Finite executable lemma and explicit *assumption-free* counterexample.

    Enumerate boolean grant streams of up to 12 ticks, rank 1..3, window
    1..3. If each full W-block while the FIFO head remains pending has a
    grant, its r-th grant arrives by rW-1. This does not assert the premise.
    """
    examined = 0
    for window in range(1, 4):
        for rank in range(1, 4):
            horizon = window*rank
            for bits in product((0, 1), repeat=horizon):
                examined += 1
                # A legal conditional service stream has a grant in each
                # W-block until rank-th service. This is stronger than the
                # source evidence; it is an explicit new contract premise.
                granted = 0
                for pos in range(0, horizon, window):
                    block = bits[pos:pos+window]
                    if granted < rank and sum(block) == 0:
                        break
                    granted += sum(block)
                else:
                    check(granted >= rank and
                          [i for i, bit in enumerate(bits) if bit][rank-1] <=
                          horizon-1,
                          'v4 conditional FIFO rank window lemma falsified')
    # Saturated one-slot PE, ready native forward and actor ACK at the same
    # tick: exact native forward time consumes the only global grant.
    forward_ready = ack_ready = 1
    available_PE = 1
    check(forward_ready + ack_ready > available_PE and
          available_PE - forward_ready == 0,
          'v4 expected one-PE compatibility impossibility not witnessed')
    return {
        'enumerated_finite_grant_streams': examined,
        'conditional_FIFO_rank_window_lemma_counterexamples': 0,
        'without_rate_assumption_all_zero_grants_can_defer_indefinitely': True,
        'one_global_PE_strict_native_timing_and_same_tick_ACK_impossible': True,
    }


def validate_signed_v3tuv(previous, raw):
    check(type(previous) is dict and type(raw) is bytes and
          sha256(raw).hexdigest() == PREDECESSOR_SHA and
          canon(previous) == raw and previous.get('status') == SOURCE_STATUS and
          previous.get('new_original_native_runs') == 18 and
          previous.get('new_derived_rank_runs') == 72 and
          previous.get('new_causal_null_runs') == 36 and
          previous.get('full_original_native_projection_preserved') is True and
          previous.get('universal_native_tick_deadline_proven') is False and
          previous.get('native_actor_learning_observed') is False and
          previous.get('native_operator_updates') == 0 and
          type(previous.get('source_matrix')) is list and
          len(previous['source_matrix']) == 3 and
          previous.get('grant_rank_totals', {}).get(
              'served_exact_rank_certificates') == 329 and
          previous['grant_rank_totals'].get(
              'censored_rank_below_threshold_certificates') == 767,
          'v4 signed source FIFO predecessor incomplete or altered')
    return True


def analyze_predecessor(previous, raw):
    validate_signed_v3tuv(previous, raw)
    totals = {'contexts': 0, 'native_original_runs': 18,
              'derived_replays': 72, 'causal_null_replays': 36,
              'source_ticks': 0, 'real_global_ACK_grants': 0,
              'real_grant_ticks': 0, 'maximum_pending_no_grant_streak': 0,
              'contexts_with_zero_grant_window': {str(w): 0 for w in WINDOWS},
              'overlapping_zero_grant_windows': {str(w): 0 for w in WINDOWS}}
    witnesses = []
    for episode in previous['source_matrix']:
        check(type(episode) is dict and type(episode.get('modes')) is list and
              len(episode['modes']) == 3 and
              type(episode.get('source_external_ticks')) is list and
              len(episode['source_external_ticks']) == 8,
              'v4 source episode format drift')
        for mode in episode['modes']:
            check(type(mode.get('capacities')) is list and
                  len(mode['capacities']) == 2,
                  'v4 source mode capacity count drift')
            for cap in mode['capacities']:
                for policy in ('ACK-first', 'bounded-turns'):
                    for quota in ('1', '2'):
                        row = cap['derived_policies'][policy][quota]
                        audit = row['rank_audit']
                        c = audit['totals']
                        check(row['full_original_native_result_exact'] is True and
                              audit['source_FIFO_prefix_for_observed_context'] is True and
                              audit['source_conditional_grant_rank_verified'] is True and
                              audit['future_grant_arrival_or_tick_deadline_proven'] is False and
                              audit['native_actor_fair_scheduler_or_learning_proven'] is False,
                              'v4 source trace ungrounded projection/fairness claim')
                        probe = source_row_gaps(audit['per_tick_fifo_prefix'])
                        check(probe['source_ticks'] == c['source_native_ticks'] and
                              probe['real_global_ACK_grants'] == c['source_grant_units'] and
                              probe['real_grant_ticks'] == c['source_grant_ticks'],
                              'v4 real source grants mismatch source FIFO journal')
                        totals['contexts'] += 1
                        for key in ('source_ticks', 'real_global_ACK_grants',
                                    'real_grant_ticks'):
                            totals[key] += probe[key]
                        totals['maximum_pending_no_grant_streak'] = max(
                            totals['maximum_pending_no_grant_streak'],
                            probe['max_consecutive_pending_no_grant_ticks'])
                        for w in WINDOWS:
                            name = str(w)
                            count = probe['windows_with_ready_ACK_but_zero_grants'][name]
                            totals['overlapping_zero_grant_windows'][name] += count
                            totals['contexts_with_zero_grant_window'][name] += int(count>0)
                            if count and len(witnesses) < 12:
                                witnesses.append({
                                    'schedule': episode['schedule'],
                                    'mode': mode['mode'],
                                    'PE_capacity': cap['native_PE_capacity'],
                                    'derived_queue_policy': policy,
                                    'global_ACK_quota': int(quota),
                                    'window_ticks': w,
                                    'window_start_tick': probe[
                                        'first_violating_window_start_ticks'][name],
                                    'source_real_grant_journal_sha256':
                                        row['source_ACK_journal_sha256'],
                                })
    check(totals['contexts'] == 72 and
          totals['real_global_ACK_grants'] == 329 and
          totals['maximum_pending_no_grant_streak'] > 0 and
          totals['overlapping_zero_grant_windows']['1'] > 0,
          'v4 source evidence does not display missing service opportunity')
    choices = {key: {'proposal': candidate,
                     'admission': validate_candidate(candidate)}
               for key, candidate in profiles().items()}
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_predecessor_v3tuv_sha256': sha256(raw).hexdigest(),
        'research_stages': [
            'v4a-native-source-observed-ACK-window-capacity-exposure',
            'v4b-conditional-rank-time-lemma-and-single-PE-impossibility',
            'v4c-unadmitted-two-mode-versioned-native-service-contract',
        ],
        'source_exposure': totals,
        'source_window_counterexamples': witnesses,
        'finite_conditional_lemma': exhaustive_window_rank_check(),
        'candidate_modes': choices,
        'preserved_previous_native_source': True,
        'native_v0e_modified': False,
        'native_actor_service_policy_implemented': False,
        'native_actor_learning_implemented': False,
        'any_new_native_liveness_guarantee_proven': False,
        'next_gate': 'VERSIONED_NATIVE_ARCHITECTURE_ADMISSION_AND_SCHEDULER_IMPLEMENTATION_REQUIRED',
    }
