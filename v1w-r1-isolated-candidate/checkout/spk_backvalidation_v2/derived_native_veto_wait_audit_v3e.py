"""v3e-v3g: source-probe overlap accounting for ACK due-to-service waits.

Classification is retrospective on a finite, fully replayed derived trace.
It does NOT attribute counterfactual causality to an individual blocked tick,
nor promise an ACK service deadline or alter frozen native arbitration.
"""
from __future__ import annotations

from spk_backvalidation_v2.derived_native_fork_v2g import guard
from spk_backvalidation_v2.derived_ack_wait_audit_v3b import (
    audit_source_acks_and_paid_receipts,
)

SCHEMA = 'spk-bv-native-guard-overlap-and-ACK-wait-partition/v3e-v3g'
CLASSES = ('joint_native_veto', 'forward_only_veto',
           'feedback_only_veto', 'unblocked_native_tick',
           'post_native_tail_tick')


def audit_native_wait_overlap(ACKs, paid, probes, burst, *, policy,
                              protect_forward, protect_feedback):
    """Classify each *observed wait tick* exactly once; no liveness inference."""
    guard(type(protect_forward) is bool and type(protect_feedback) is bool and
          type(probes) is list and bool(probes) and
          all(type(p) is dict for p in probes),
          'v3e untyped native-guard policy or missing source probes')
    previous = audit_source_acks_and_paid_receipts(ACKs, paid, burst, policy)
    by_tick = {p.get('tick'): p for p in probes}
    first, last = probes[0].get('tick'), probes[-1].get('tick')
    guard(type(first) is int and type(last) is int and first >= 1 and
          last >= first and len(by_tick) == len(probes) == last-first+1 and
          sorted(by_tick) == list(range(first, last+1)),
          'v3e source native tick replay is not contiguous or unique')
    observed = dict.fromkeys(CLASSES, 0)
    probe_classes = dict.fromkeys(CLASSES[:4], 0)
    actual_authorized_pregrants = 0
    ready_ACK_unblocked_ticks = 0
    for tick, p in by_tick.items():
        forward = p.get('ready_forward_before')
        feedback = p.get('ready_native_feedback_before')
        ready = p.get('ready_ACKs_before')
        pregrant = p.get('pre_forward_ACK_grants')
        guard(all(type(x) is int and x >= 0 for x in
                  (forward, feedback, ready, pregrant)),
              'v3e source-backed native inventory or grant invalid')
        f = bool(forward) and protect_forward
        b = bool(feedback) and protect_feedback
        veto = f or b
        guard(p.get('native_source_priority_veto') is veto and
              (not veto or p.get('selected') == 'native-ready' and pregrant == 0),
              'v3e native priority veto or derived real resource charge drift')
        label = ('joint_native_veto' if f and b else
                 'forward_only_veto' if f else
                 'feedback_only_veto' if b else 'unblocked_native_tick')
        probe_classes[label] += 1
        actual_authorized_pregrants += pregrant
        ready_ACK_unblocked_ticks += int(not veto and ready > 0)
    for ack in ACKs:
        due, service = ack['due_tick'], ack['serviced_tick']
        guard(type(due) is int and type(service) is int and
              first <= due <= service and service <= last+128,
              'v3e ACK custody beyond finite source/tail window')
        for tick in range(due, service):
            if tick > last:
                observed['post_native_tail_tick'] += 1
            else:
                p = by_tick[tick]
                f = bool(p['ready_forward_before']) and protect_forward
                b = bool(p['ready_native_feedback_before']) and protect_feedback
                label = ('joint_native_veto' if f and b else
                         'forward_only_veto' if f else
                         'feedback_only_veto' if b else 'unblocked_native_tick')
                observed[label] += 1
    guard(sum(observed.values()) == previous[
              'total_ACK_due_to_service_wait_ticks'],
          'v3e lost or double-counted source-derived ACK wait tick')
    return {
        'schema': SCHEMA,
        'source_native_last_tick': last,
        'native_probe_tick_partition': probe_classes,
        'ACK_wait_tick_overlap_partition': observed,
        'ACK_wait_total_ticks': sum(observed.values()),
        'ACK_wait_max_ticks': previous['max_ACK_due_to_service_wait_ticks'],
        'source_ACKs': previous['source_ACKs'],
        'paid_consumer_receipts': previous['independently_paid_consumer_receipts'],
        'ready_ACK_unblocked_native_ticks': ready_ACK_unblocked_ticks,
        'actually_resource_charged_pre_forward_ACK_grants':
            actual_authorized_pregrants,
        'finite_trace_accounted': True,
        'global_ACK_service_deadline_proven': False,
        'causal_effect_of_each_individual_wait_tick_identified': False,
    }
