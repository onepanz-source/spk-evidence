"""BV v1t: sender/receiver native *posthoc* counts to an isolated B mailbox.

NO frozen-runtime changes, NO genuine independent taps, NO native receiver
messages. The two counterfactual branches have distinct SHADOW episode labels,
not cross-world event identities. Every possible knowledge conclusion is
conditional on the (non-native) laboratory transport of simulator evidence.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from hashlib import sha256

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.receiver_disclosure_channel_v1s import SCHEMA as S_SCHEMA, STATUS as S_STATUS

SCHEMA='spk-bv-source-bound-native-trace-to-isolated-mailbox/v1t'
STATUS='POSTHOC_NATIVE_TRACE_BRIDGE_SHADOW_RECEIPTS_ONLY'
M_SCHEMA='spk-bv-native-passive-two-port-trace-projection/v1m'
EDGE='A->B:7->0'
KINDS={'expectation':'plan','sender_count':'producer_trace',
       'sender_coverage':'lab_coverage','receiver_coverage':'lab_coverage',
       'decision':'experimenter'}
PLANS=('ingress_only','sender_only','all_disclosed','sender_lost',
       'sender_coverage_lost','receiver_coverage_lost','expectation_lost',
       'decision_lost','packet_forged','packet_replayed','packet_late',
       'packet_wrong_edge','packet_wrong_episode','packet_wrong_role',
       'contradictory_source_count')
EXCLUDED=[
 'native-traces-are-scheduler-owned-not-independent-physical-sensors',
 'posthoc-ingress-projection-is-not-native-receiver-mailbox-access',
 'shadow-packets-are-not-transmitted-to-neuron-B-in-native-SPK',
 'role-object-seals-are-process-local-assumptions-not-real-authentication',
 'lab-coverage-is-not-a-native-interval-or-absence-certificate',
 'no-native-decision-disclosure-or-causal-identification',
 'separate-experimenter-episodes-are-not-cross-world-event-pairings',
 'no-native-value-criterion-or-scored-feedback-or-learning',
 'no-frozen-source-or-architecture-or-hardware-promotion',
]


def validate_inputs(s:dict,sraw:bytes,m:dict,mraw:bytes):
    """Strict source-bound read; does not claim that JSON authenticates producer."""
    require(type(s) is dict and type(m) is dict and type(sraw) is bytes and
            type(mraw) is bytes and canon(s)==sraw and canon(m)==mraw,
            'predecessor bytes not canonical')
    require(s.get('schema')==S_SCHEMA and s.get('status')==S_STATUS and
            s.get('source_kind')=='SOURCE_BOUND_V1R_PLUS_ISOLATED_IN_PROCESS_CHANNEL_LAB' and
            s.get('inherited_native_v1r_recomputation_verified_in_this_run') is True and
            s.get('lab_case_count')==20 and len(s.get('lab_cases',[]))==20 and
            s.get('lab_control_loss_fails_closed') is True and
            s.get('native_separate_disclosure_channel_installed') is False and
            s.get('native_receiver_judgments')==0 and
            s.get('native_receiver_authorized_absence_witnesses')==0 and
            s.get('native_operator_updates')==0 and
            s.get('native_learning_proven') is False and
            s.get('lab_authentication_assumption')=='PYTHON_OBJECT_IDENTITY_ONLY_NOT_NATIVE_AUTHENTICATION',
            'untrusted v1s boundary flags')
    require(m.get('schema')==M_SCHEMA and
            m.get('status')=='NATIVE_POSTHOC_ENDPOINT_TRACES_NOT_INDEPENDENT_OBSERVER' and
            m.get('source_kind')=='FROZEN_NATIVE_SCHEDULER_POSTHOC_TRACES' and
            m.get('full_native_scheduler_runs_recomputed_in_this_run')==4 and
            m.get('inherited_native_v1l_recomputation_verified_in_this_run') is True and
            m.get('native_two_port_independent_observer_installed') is False and
            m.get('recipient_access_to_sender_trace_demonstrated') is False and
            m.get('endogenous_receiver_judgments')==0 and
            m.get('native_coverage_certificates')==0 and
            m.get('sender_operator_updates')==0 and
            m.get('native_learning_proven') is False and
            m.get('native_fixture_sha256')==s.get('native_fixture_sha256') and
            m.get('frozen_native_sources')==s.get('frozen_native_sources'),
            'untrusted v1m posthoc/native custody')
    require(all(type(s.get(k)) is str and len(s[k])==64 and
                all(c in '0123456789abcdef' for c in s[k])
                for k in ('reference_v1r_sha256','reference_v1q_sha256')) and
            type(m.get('frozen_native_sources')) is dict and
            bool(m['frozen_native_sources']) and
            type(m.get('native_fixture_sha256')) is str and
            len(m['native_fixture_sha256'])==64 and
            all(c in '0123456789abcdef' for c in m['native_fixture_sha256']) and
            m.get('native_trace_source_emission_count_original_vs_variant')==
              {'A':[2,0],'B':[2,0]},
            'upstream custody mismatch')
    trace=m.get('native_trace_projection')
    require(type(trace) is dict and set(trace)=={'original','variant'},
            'native arms incomplete')
    extracted={}
    for arm in ('original','variant'):
        extracted[arm]={}
        for mode in ('off','on'):
            record=trace[arm][mode]
            require(type(record) is dict and record.get('posthoc_simulator_trace_reader_only') is True and
                    record.get('native_external_observer_present') is False and
                    record.get('native_absence_certificate_count')==0 and
                    record.get('native_full_scheduler_executed') is True,
                    'native trace trust boundary violated')
            edges=record.get('edge_projections')
            require(type(edges) is list and len(edges)==2 and
                    {e['edge'] for e in edges}=={EDGE,'B->C:7->0'},
                    'edge inventory mismatch')
            link=next(e for e in edges if e['edge']==EDGE)
            down=next(e for e in edges if e['edge']=='B->C:7->0')
            require((down.get('sender'),down.get('receiver'),down.get('sender_channel'),
                     down.get('receiver_channel'))==('B','C',7,0) and
                    down.get('independent_two_port_coverage_certificate') is False and
                    down.get('receiver_native_received_sender_port_attestation') is False and
                    down.get('sender_trace_emission_count')==(2 if arm=='original' else 0) and
                    down.get('receiver_ingress_occurrence_count')==(2 if arm=='original' else 0),
                    'wrong downstream causal edge or source count')
            require((link.get('sender'),link.get('receiver'),
                    link.get('sender_channel'),link.get('receiver_channel'))==
                    ('A','B',7,0) and
                    link.get('independent_two_port_coverage_certificate') is False and
                    link.get('receiver_native_received_sender_port_attestation') is False,
                    'A->B edge authority mismatch')
            sent=link.get('sender_trace_emission_count')
            ingress=link.get('receiver_ingress_occurrence_count')
            consumed=link.get('receiver_consumed_occurrence_count')
            ids=link.get('ingress_occurrence_ids')
            times=link.get('sender_emission_timestamps')
            expect=2 if arm=='original' else 0
            require(all(type(n) is int and n>=0 for n in (sent,ingress,consumed)) and
                    (sent,ingress,consumed)==(expect,expect,expect) and
                    type(ids) is list and len(ids)==expect and
                    len(set(ids))==len(ids) and all(type(x) is str and x for x in ids) and
                    type(times) is list and len(times)==expect and
                    all(type(t) is int and t>=0 for t in times) and
                    times==sorted(times) and
                    link.get('posthoc_trace_classification')==(
                        'ROUTED_EVENTS_IN_COMPLETE_RUN_TRACE' if expect else
                        'NO_SOURCE_CHANNEL_EVENT_IN_BOUNDED_RUN_TRACE'),
                    'unreconciled A->B source/ingress/consumption counts')
            extracted[arm][mode]={'sender':sent,'ingress':ingress,
                                  'consumed':consumed,'occurrence_count':len(ids)}
        require(extracted[arm]['off']==extracted[arm]['on'],
                'BV on/off changed frozen forward projection')
    require(extracted['original']['off']['sender']==2 and
            extracted['variant']['off']['sender']==0,
            'fixture native contrast mismatch')
    return extracted


@dataclass(frozen=True)
class LabPacket:
    kind:str
    issuer:str
    episode:str
    link:str
    created_at:int
    delivered_at:int
    datum:int | str
    seal:object


class TraceLabBus:
    def __init__(self):
        self._seals={actor:object() for actor in set(KINDS.values())}

    def mint(self,kind:str,episode:str,datum:int | str,*,created_at:int,delivered_at:int):
        require(kind in KINDS and type(episode) is str and episode and
                type(created_at) is int and type(delivered_at) is int and
                0<=created_at<=delivered_at and type(datum) in (int,str),
                'invalid lab packet')
        issuer=KINDS[kind]
        return LabPacket(kind,issuer,episode,EDGE,created_at,delivered_at,datum,
                         self._seals[issuer])


class BShadowMailbox:
    """Only delivered packets plus a projected ingress count. No source trace ref."""
    def __init__(self,bus:TraceLabBus,episode:str,ingress:int,verdict_at:int=10):
        require(type(bus) is TraceLabBus and type(episode) is str and episode and
                type(ingress) is int and 0<=ingress<=2 and
                type(verdict_at) is int and verdict_at>=9,
                'invalid shadow receiver configuration')
        self._bus=bus; self.episode=episode;self.ingress=ingress
        self.received={};self.verdict_at=verdict_at

    def deliver(self,p:LabPacket):
        require(type(p) is LabPacket and p.kind in KINDS and
                p.issuer==KINDS[p.kind] and
                p.seal is self._bus._seals[p.issuer] and
                p.episode==self.episode and p.link==EDGE and
                type(p.created_at) is int and type(p.delivered_at) is int and
                0<=p.created_at<=p.delivered_at<=self.verdict_at and
                p.kind not in self.received,
                'invalid/forged/replayed/out-of-scope lab evidence')
        valid={
            'expectation':p.datum=='declared:up-to-two' and p.created_at==0 and p.delivered_at<=2,
            'sender_count':type(p.datum) is int and 0<=p.datum<=2 and p.created_at==7 and p.delivered_at>=7,
            'sender_coverage':p.datum=='lab-window-0-6' and p.created_at==7 and p.delivered_at>=7,
            'receiver_coverage':p.datum=='lab-window-0-6' and p.created_at==7 and p.delivered_at>=7,
            'decision':p.datum in ('experimenter:CMP1','experimenter:CMP2') and p.created_at==3 and p.delivered_at>=3,
        }
        require(valid[p.kind], 'invalid lab temporal/content envelope')
        self.received[p.kind]=p

    def classify(self):
        received=self.received
        source=received.get('sender_count')
        if source is not None and self.ingress>source.datum:
            verdict='CONFLICTING_EVIDENCE_UNKNOWN'
        elif self.ingress>0:
            verdict='INGRESS_OBSERVED_FROM_POSTHOC_PROJECTION'
        elif 'expectation' not in received:
            verdict='NO_PREDECLARED_EXPECTATION_RECEIVED'
        elif source is None:
            verdict='NO_SENDER_DISCLOSURE_UNKNOWN'
        elif 'sender_coverage' not in received or 'receiver_coverage' not in received:
            verdict='NO_LAB_COVERAGE_UNKNOWN'
        elif source.datum==0:
            verdict='LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY'
        else:
            verdict='LAB_DISCLOSED_TRANSPORT_GAP_NO_NATIVE_AUTHORITY'
        return {
            'classification':verdict,'receiver_ingress_count':self.ingress,
            'received_kinds':sorted(received),
            'decision_declared_to_shadow_B':'decision' in received,
            'native_authority':False,'sender_decision_cause_known':False,
            'independent_absence_certificate':False,
            'receiver_scored_judgment':False,
        }


def session(arm:str,mode:str,plan:str,values:dict):
    require(arm in ('original','variant') and mode in ('off','on') and plan in PLANS,
            'invalid requested finite session')
    episode=f'shadow.native-trace.{arm}.{mode}'
    bus=TraceLabBus()
    box=BShadowMailbox(bus,episode,values['ingress'])
    packet_specs={
        'expectation':('declared:up-to-two',0,1),
        'sender_count':(values['sender'],7,8),
        'sender_coverage':('lab-window-0-6',7,8),
        'receiver_coverage':('lab-window-0-6',7,8),
        'decision':('experimenter:CMP1' if arm=='original' else 'experimenter:CMP2',3,4),
    }
    excluded={
        'ingress_only':set(packet_specs),
        'sender_only':{'expectation','sender_coverage','receiver_coverage','decision'},
        'sender_lost':{'sender_count'},
        'sender_coverage_lost':{'sender_coverage'},
        'receiver_coverage_lost':{'receiver_coverage'},
        'expectation_lost':{'expectation'},
        'decision_lost':{'decision'},
    }.get(plan,set())
    for kind,(value,t0,t1) in packet_specs.items():
        if kind not in excluded:box.deliver(bus.mint(kind,episode,value,created_at=t0,delivered_at=t1))
    invalid_attempts=0
    if plan.startswith('packet_'):
        p=bus.mint('sender_count',episode,values['sender'],created_at=7,delivered_at=8)
        if plan=='packet_forged':p=replace(p,seal=object())
        elif plan=='packet_replayed':p=box.received['sender_count']
        elif plan=='packet_late':p=replace(p,delivered_at=11)
        elif plan=='packet_wrong_edge':p=replace(p,link='B->C:7->0')
        elif plan=='packet_wrong_episode':p=replace(p,episode='shadow.native-trace.other')
        elif plan=='packet_wrong_role':p=replace(p,issuer='plan')
        try:box.deliver(p)
        except (ValueError,TypeError,AttributeError,AssertionError):invalid_attempts+=1
        else:raise AssertionError('malicious evidence accepted')
    if plan=='contradictory_source_count':
        # Deliberate observable contradiction with the local ingress projection.
        # On variant (ingress 0) source > ingress is not a logical contradiction:
        # it could instead indicate loss in transport. Only testing original.
        require(arm=='original','contradiction only meaningful with ingress>0')
        # Re-create with conflicting sealed packet, NOT a source audit assertion.
        bus=TraceLabBus();box=BShadowMailbox(bus,episode,values['ingress'])
        for k,(v,t0,t1) in packet_specs.items():
            box.deliver(bus.mint(k,episode,0 if k=='sender_count' else v,
                                 created_at=t0,delivered_at=t1))
    obj=box.classify()
    return {'arm':arm,'mode':mode,'plan':plan,
            'episode_id_is_shadow_label_only':episode,
            'experimenter_posthoc_counts_not_receiver_visible':values,
            'receiver_view':obj,
            'ingress_derived_from_posthoc_trace_not_live_B':True,
            'received_packets_native':0,
            'malicious_attempts_rejected':invalid_attempts}


def analyze(s:dict,sraw:bytes,m:dict,mraw:bytes):
    values=validate_inputs(s,sraw,m,mraw)
    data=[]
    for arm in ('original','variant'):
        for mode in ('off','on'):
            for plan in PLANS:
                if plan=='contradictory_source_count' and arm=='variant':continue
                data.append(session(arm,mode,plan,values[arm][mode]))
    bykey={(r['arm'],r['mode'],r['plan']):r for r in data}
    for mode in ('off','on'):
        for arm in ('original','variant'):
            b=lambda p:bykey[(arm,mode,p)]
            require(b('all_disclosed')['receiver_view']['native_authority'] is False and
                    b('ingress_only')['receiver_view']['received_kinds']==[] and
                    b('sender_lost')['receiver_view']['classification']!=
                       'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY' and
                    b('sender_coverage_lost')['receiver_view']['classification']!=
                       'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY' and
                    b('receiver_coverage_lost')['receiver_view']['classification']!=
                       'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY',
                    'invalid native/lab knowledge partition')
        require(bykey[('variant',mode,'all_disclosed')]['receiver_view']['classification']==
                'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY' and
                bykey[('variant',mode,'ingress_only')]['receiver_view']['classification']==
                'NO_PREDECLARED_EXPECTATION_RECEIVED' and
                bykey[('original',mode,'all_disclosed')]['receiver_view']['classification']==
                'INGRESS_OBSERVED_FROM_POSTHOC_PROJECTION' and
                bykey[('original',mode,'contradictory_source_count')]['receiver_view']['classification']==
                'CONFLICTING_EVIDENCE_UNKNOWN',
                'source-bound shadow session unexpected')
    require(all(x['receiver_view']['native_authority'] is False and x['received_packets_native']==0 and
                x['receiver_view']['independent_absence_certificate'] is False and
                x['receiver_view']['receiver_scored_judgment'] is False and
                x['receiver_view']['sender_decision_cause_known'] is False for x in data),
            'shadow bridge promoted to native authority')
    return {
      'schema':SCHEMA,'status':STATUS,
      'source_kind':'POSTHOC_NATIVE_V1M_TRACE_PLUS_ISOLATED_V1S_STYLE_MAILBOX',
      'reference_v1s_sha256':sha256(sraw).hexdigest(),
      'reference_v1m_sha256':sha256(mraw).hexdigest(),
      'reference_v1r_sha256':s['reference_v1r_sha256'],
      'native_fixture_sha256':m['native_fixture_sha256'],
      'frozen_native_sources':m['frozen_native_sources'],
      'inherited_native_v1s_recomputation_verified_in_this_run':False,
      'new_native_scheduler_runs_in_this_module':0,
      'source_native_scheduler_runs_in_v1m':4,
      'shadow_lab_sessions':data,'shadow_lab_session_count':len(data),
      'native_receiver_received_control_packets':0,
      'native_independent_absence_certificates':0,
      'native_authenticated_producer_evidence':0,
      'native_decision_records_to_receiver':0,
      'native_scored_receiver_judgments':0,
      'native_operator_updates':0,'native_learning_proven':False,
      'posthoc_producer_and_ingress_share_same_scheduler_trace':True,
      'injected_control_packets_are_shadow_only':True,
      'counterfactual_episode_ids_not_shared_across_worlds':True,
      'lab_control_loss_fails_closed':True,
      'declared_criterion_or_utility_identified':False,
      'source_authenticated_to_receiver':False,
      'claims_excluded':EXCLUDED,
    }
