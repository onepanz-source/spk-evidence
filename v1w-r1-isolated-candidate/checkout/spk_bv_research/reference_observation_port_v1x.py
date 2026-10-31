"""BV v1x: versioned source-owned REFERENCE port, not a native SPK hook.

The research executor invokes its own observation callback *during its own run*.
Input counts are seeded from a native run only AFTER that native call returned.
No native receiver, native clock, cryptographic identity, or independent coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.observation_seam_contract_v1w import (
    SCHEMA as W_SCHEMA, STATUS as W_STATUS, PORT_OBLIGATIONS,
    EXPECTED_PINS, EXPECTED_COMPUTE_AST, EXPECTED_PINS as PINS,
)

SCHEMA='spk-bv-versioned-reference-observation-port-conformance/v1x'
STATUS='VERSIONED_REFERENCE_PORT_NO_NATIVE_LIVE_OBSERVER'
PORT='spk-bv-observation-port/reference-v1x'
CASES=('no_listener','all_delivered','sender_report_lost','expectation_lost',
       'coverage_lost','decision_lost','channel_fault','queue_overflow',
       'forged','replayed','wrong_episode','wrong_receiver','late','raising_listener',
       'corrupt_count','cross_world')
NATIVE_LIMITS={
    'native_callback_connected':False,
    'native_observer_enabled_mode_executed':False,
    'native_receiver_B_received_control_messages':0,
    'native_coverage_certificates':0,
    'native_authenticated_producer_evidence':0,
    'native_scored_receiver_judgments':0,
    'native_operator_updates':0,
    'native_learning_proven':False,
}
CLAIMS_EXCLUDED=(
    'reference-executor-callback-before-reference-return-is-not-native-scheduler-callback',
    'native-baseline-repeatability-is-not-native-observer-on-off-noninterference',
    'reference-port-seeded-from-native-postreturn-counts-not-live-native-events',
    'python-object-seal-is-not-authentication-or-trust-anchor',
    'lab-close-is-not-independent-native-time-or-absence-certificate',
    'no-cross-world-event-identity-or-receiver-access-to-scheduler-result',
    'channel-drop-or-overflow-does-not-mean-sender-silence',
    'no-endogenous-criterion-causal-credit-or-learning',
    'no-frozen-core-network-compiler-architecture-modifications',
)


def check_predecessor(doc, raw):
    require(type(doc) is dict and type(raw) is bytes and canon(doc)==raw,
            'noncanonical predecessor')
    required={
        'schema':W_SCHEMA,'status':W_STATUS,
        'source_kind':'FROZEN_NATIVE_AST_READONLY_CANDIDATES_NO_EVENT_TAP',
        'native_source_readonly_bytes_rechecked_in_this_run':True,
        'inherited_native_v1v_recomputation_verified_in_this_run':True,
        'source_files_modified':False,
        'native_event_callback_invoked':False,
        'native_observation_message_delivered_to_B':False,
        'native_authenticated_absence_coverage':False,
        'native_receiver_scored_judgments':0,'native_operator_updates':0,
        'native_learning_proven':False,'new_native_scheduler_executions_in_this_module':0,
        'postreturn_trace_is_online_native_evidence':False,
        'static_candidate_is_runtime_event_hook':False,
        'design_port_name_only':'spk-bv-observation-port/v1-proposal',
        'integration_path_selection':'VERSIONED_ADDITIVE_SOURCE_OWNED_OBSERVER_PORT_REQUIRED_NOT_INSTALLED',
    }
    require(all(type(doc.get(k)) is type(v) and doc[k]==v for k,v in required.items()),
            'v1w authority or provenance mismatch')
    require(doc.get('proof_obligations_unmet')==[
        {'id':k,'requirement':v,'verified':False} for k,v in PORT_OBLIGATIONS],
        'native proof obligations improperly promoted')
    signature=doc.get('confirmed_frozen_scheduler_signature')
    require(type(signature) is dict and signature.get('name')=='execute_live_v0e' and
            signature.get('positional')==['case','fabric','tplan','pplan','mplan','lplan','bv'] and
            signature.get('keyword_only')==[] and
            signature.get('possible_callback_name_hints')==[] and
            signature.get('async_function') is False and signature.get('generator_body_has_yield') is False,
            'frozen scheduler signature mismatch')
    candidates=doc.get('source_pinned_static_candidate_inventory')
    require(type(candidates) is dict and
            candidates.get('candidate_extraction')=='STATIC_CALL_NAME_MATCHES_NOT_EXECUTION_OR_DATA_FLOW' and
            candidates.get('candidate_count_by_category')=={
                'back_validation':2,'forward_route':0,'receiver_ingress':2,
                'scheduler_batch':0,'sender_emission':0} and
            candidates.get('native_event_semantics_established') is False and
            candidates.get('native_listener_or_callback_installed') is False and
            candidates.get('source_file_sha256')==dict(sorted(EXPECTED_PINS.items())),
            'native AST inventory drift')
    for category,entries in candidates.get('bounded_callsite_examples',{}).items():
        require(category in ('back_validation','forward_route','receiver_ingress','scheduler_batch','sender_emission') and
                type(entries) is list and all(type(x) is dict and x.get('verified_hook') is False
                  for x in entries),'candidate incorrectly promoted')
    require(set(candidates['bounded_callsite_examples'])==set(candidates['candidate_count_by_category']) and
            all(len(candidates['bounded_callsite_examples'][k])==v for k,v in
                candidates['candidate_count_by_category'].items()),
            'bounded candidate inventory mismatch')
    require(doc.get('reference_v1v_sha256') and
            type(doc['reference_v1v_sha256']) is str and
            len(doc['reference_v1v_sha256'])==64,
            'missing predecessor SHA')
    return True


@dataclass(frozen=True,slots=True)
class Record:
    port_version: str
    episode: str
    receiver: str
    phase: str
    ordinal: int
    tick: int
    count: int
    seal: object


class Mailbox:
    """Only records delivered through this explicit lab route are B-visible."""
    def __init__(self, episode, cap, capacity=16):
        self.episode=episode
        self.cap=cap
        self.capacity=capacity
        self.records=[]
        self.dropped=False
        self.rejected=0
        self._seen=set()
        self._last=-1
        self._last_tick=-1
    def deliver(self, packet):
        if not isinstance(packet,Record) or packet.seal is not self.cap or \
           packet.port_version!=PORT or packet.episode!=self.episode or \
           packet.receiver!='B' or type(packet.tick) is not int or \
           type(packet.ordinal) is not int or type(packet.count) is not int or \
           packet.tick<0 or packet.ordinal<0 or packet.count<0 or \
           packet.phase not in ('expectation','decision','sender_count','sender_emission','sender_coverage','receiver_coverage') or \
           packet.ordinal in self._seen or packet.ordinal<=self._last or \
           packet.tick<=self._last_tick:
            self.rejected+=1
            return False
        if len(self.records)>=self.capacity:
            self.dropped=True
            return False
        self._seen.add(packet.ordinal)
        self._last=packet.ordinal
        self._last_tick=packet.tick
        self.records.append(packet)
        return True
    def view(self,ingress):
        counts={}
        for r in self.records:
            if r.phase=='sender_emission':
                continue
            if r.phase in counts:
                return {'classification':'DUPLICATE_LAB_EVIDENCE_UNKNOWN','received_kinds':sorted(counts)}
            counts[r.phase]=r.count
        phases=sorted({r.phase for r in self.records})
        if self.dropped:
            cls='CONTROL_OVERFLOW_UNKNOWN'
        elif not self.records or 'expectation' not in counts:
            cls='NO_DELIVERED_EXPECTATION_UNKNOWN'
        elif any(x not in counts for x in ('sender_count','sender_coverage','receiver_coverage')):
            cls='INCOMPLETE_LAB_EVIDENCE_UNKNOWN'
        elif counts['sender_coverage']!=1 or counts['receiver_coverage']!=1:
            cls='UNCOVERED_LAB_INTERVAL_UNKNOWN'
        elif counts['sender_count']<ingress:
            cls='CONFLICTING_LAB_COUNT_UNKNOWN'
        elif ingress:
            cls='LAB_INGRESS_OBSERVED'
        elif counts['sender_count']:
            cls='LAB_POSSIBLE_TRANSPORT_GAP'
        else:
            cls='LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY'
        return {'classification':cls,'received_kinds':phases,
                'receiver_ingress_count':ingress,'receiver_scored_judgment':False,
                'native_authority':False,'native_absence_certificate':False,
                'operator_update_committed':False}


def reference_execute(sender_count,ingress,port=None):
    """Research-owned source issues records in its OWN execution, never native.

    Return is independent of port, even if callback raises ordinary exceptions.
    """
    require(type(sender_count) is int and 0<=sender_count<=16 and
            type(ingress) is int and 0<=ingress<=sender_count,
            'invalid reference seed')
    emitted=0
    ordinal=0
    def offer(phase,tick,count):
        nonlocal ordinal
        if port is not None:
            try:port(phase,ordinal,tick,count)
            except Exception:pass
        ordinal+=1
    # These decisions and ticks belong to the REFERENCE executor, not to SPK.
    offer('expectation',0,2)
    offer('decision',1,1)
    for i in range(sender_count):
        emitted+=1
        offer('sender_emission',2+i,1)
    offer('sender_count',20,emitted)
    offer('sender_coverage',21,1)
    offer('receiver_coverage',22,1)
    return {'sender_count':emitted,'ingress_count':ingress,'reference_terminated':True}


def lab_episode(source_count,ingress,plan,episode='lab.v1x.original.off'):
    require(plan in CASES and type(episode) is str and len(episode)<=128 and
            episode.startswith('lab.v1x.'),'unsupported lab plan/episode')
    cap=object()
    maxsize=1 if plan=='queue_overflow' else 16
    box=Mailbox(episode,cap,maxsize)
    live_calls=[]
    def observer(phase,ordinal,tick,count):
        live_calls.append((phase,ordinal,tick,count))
        if plan=='raising_listener':raise RuntimeError('laboratory callback crash')
        if plan=='no_listener':return
        if plan=='sender_report_lost' and phase=='sender_count':return
        if plan=='expectation_lost' and phase=='expectation':return
        if plan=='coverage_lost' and phase.endswith('coverage'):return
        if plan=='decision_lost' and phase=='decision':return
        if plan=='channel_fault':return
        pkt=Record(PORT,episode,'B',phase,ordinal,tick,count,cap)
        if plan=='corrupt_count' and phase=='sender_count' and tick==20:
            pkt=replace(pkt,count=0)
        if plan=='forged' and ordinal==0:
            box.deliver(replace(pkt,seal=object()))
        if plan=='replayed' and ordinal==1:
            box.deliver(pkt)
        if plan=='wrong_episode' and ordinal==0:
            box.deliver(replace(pkt,episode='lab.v1x.foreign'))
        if plan=='wrong_receiver' and ordinal==0:
            box.deliver(replace(pkt,receiver='C'))
        if plan=='cross_world' and ordinal==0:
            box.deliver(replace(pkt,episode='lab.v1x.variant.on'))
        if plan=='late' and ordinal==2:
            box.deliver(replace(pkt,tick=-1))
        box.deliver(pkt)
    reference=reference_execute(source_count,ingress,observer)
    baseline=reference_execute(source_count,ingress,None)
    require(canon(reference)==canon(baseline),'observer altered reference result')
    view=box.view(ingress)
    return {'plan':plan,'episode':episode,'reference_result_sha256':sha256(canon(reference)).hexdigest(),
            'reference_callback_calls':len(live_calls),
            'source_owned_during_reference_execution':True,
            'native_scheduler_callback_calls':0,
            'receiver_view':view,
            'lab_rejected_packets':box.rejected,'lab_overflow':box.dropped,
            'lab_clock_is_native':False,'reference_noninterference_equal_bytes':True}


def analyze(w,wb,*,native_reference=None,source_rechecked=False):
    check_predecessor(w,wb)
    require(type(source_rechecked) is bool,'invalid source pin flag')
    require(native_reference is None or (type(native_reference) is dict and
            set(native_reference)=={'original','variant'} and
            all(set(m)=={'off','on'} for m in native_reference.values())),
            'invalid native reference matrix')
    if native_reference is None:
        # An offline audit is allowed to use only the *established* v1p/v1m
        # counts as LAB seeds, never pretending to execute the scheduler.
        seeds={'original':{'off':(2,2),'on':(2,2)},
               'variant':{'off':(0,0),'on':(0,0)}}
    else:
        require(source_rechecked,'native baseline requires source SHA recheck')
        seeds={arm:{} for arm in ('original','variant')}
        for arm in seeds:
            for mode in ('off','on'):
                item=native_reference[arm][mode]
                require(type(item) is dict and set(item)=={'sender','ingress','result_sha256',
                                                            'repeatability_identical'} and
                        item['repeatability_identical'] is True and
                        type(item['sender']) is int and type(item['ingress']) is int and
                        type(item['result_sha256']) is str and len(item['result_sha256'])==64 and
                        all(c in '0123456789abcdef' for c in item['result_sha256']),
                        'invalid native frozen baseline evidence')
                seeds[arm][mode]=(item['sender'],item['ingress'])
        require(seeds=={'original':{'off':(2,2),'on':(2,2)},
                        'variant':{'off':(0,0),'on':(0,0)}},
                'native fixture results drift from pinned reference')
    cases=[]
    for arm in ('original','variant'):
        for mode in ('off','on'):
            for plan in CASES:
                cases.append({'arm':arm,'mode':mode,
                              **lab_episode(*seeds[arm][mode],plan,
                                  f'lab.v1x.{arm}.{mode}')})
    require(len(cases)==4*len(CASES),'missing reference lab cases')
    return {'schema':SCHEMA,'status':STATUS,
            'source_kind':'FROZEN_NATIVE_REPEATED_BASELINE_PLUS_SEPARATE_REFERENCE_PORT' if native_reference is not None
                          else 'PREDECESSOR_BOUND_REFERENCE_PORT_ONLY',
            'reference_v1w_sha256':sha256(wb).hexdigest(),
            'reference_v1v_sha256':w['reference_v1v_sha256'],
            'reference_port_version':PORT,
            'reference_port_executed_during_reference_runtime':True,
            'reference_port_is_native_scheduled_event_tap':False,
            'native_results_repeated_without_observer':native_reference is not None,
            'native_source_readonly_bytes_rechecked_in_this_run':source_rechecked,
            'native_run_reference_matrix':native_reference,
            'native_scheduler_executions_in_this_module':8 if native_reference is not None else 0,
            'inherited_native_v1w_recomputation_verified_in_this_run':False,
            'reference_lab_session_count':len(cases),
            'reference_lab_sessions':cases,
            'native_proof_obligations_unmet':[{'id':k,'verified':False} for k,_ in PORT_OBLIGATIONS],
            'native_baseline_equal_bytes_not_observer_on_off_proof':True,
            'source_files_modified':False,
            **NATIVE_LIMITS,
            'claims_excluded':list(CLAIMS_EXCLUDED)}
