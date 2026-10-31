"""SPK BV v1u: bounded incremental *lab* sidecar, with native POSTHOC seeds.

A research-owned event clock and B-local mailbox, not instrumentation of the
frozen scheduler. No independent witness, native authentication, valuation,
causal credit or learning is manufactured from native trace counts.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from hashlib import sha256
from collections import Counter

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_trace_mailbox_adapter_v1t import (
    SCHEMA as T_SCHEMA, STATUS as T_STATUS, EDGE,
)

SCHEMA='spk-bv-bounded-incremental-shadow-control-channel/v1u'
STATUS='SOURCE_BOUND_SHADOW_INCREMENTAL_DELIVERY_NO_NATIVE_RUNTIME_HOOK'
PLANS=('all_disclosed','ingress_only','source_lost','expectation_lost',
       'sender_coverage_lost','receiver_coverage_lost','decision_lost',
       'control_loss','forged','replayed','wrong_episode','late',
       'out_of_order','bounded_queue_overflow','contradictory_source')
ROLES={'expectation':'plan','sender_count':'producer_trace',
       'sender_coverage':'lab_coverage','receiver_coverage':'lab_coverage',
       'decision':'experimenter'}
EXCLUDED=[
 'clock-and-coverage-belong-to-isolated-lab-not-frozen-native-runtime',
 'posthoc-trace-count-seeds-are-not-live-native-event-callbacks',
 'identity-seals-are-python-object-capabilities-not-native-authentication',
 'B-local-mailbox-cannot-read-experimenter-posthoc-counts',
 'no-runtime-independent-absence-certificate-or-producer-witness',
 'bounded-queue-overflow-or-control-loss-forces-unknown-not-silence',
 'shadow-decision-label-is-not-sender-internal-causal-proof',
 'no-native-value-criterion-or-scored-feedback-or-updates-or-learning',
 'not-a-frozen-core-network-compiler-architecture-promotion',
]


def validate_source(t:dict,raw:bytes):
    require(type(t) is dict and type(raw) is bytes and canon(t)==raw,
            'noncanonical or invalid predecessor v1t')
    required={
        'schema':T_SCHEMA,'status':T_STATUS,
        'source_kind':'POSTHOC_NATIVE_V1M_TRACE_PLUS_ISOLATED_V1S_STYLE_MAILBOX',
        'inherited_native_v1s_recomputation_verified_in_this_run':True,
        'new_native_scheduler_runs_in_this_module':0,
        'source_native_scheduler_runs_in_v1m':4,
        'shadow_lab_session_count':58,
        'native_receiver_received_control_packets':0,
        'native_independent_absence_certificates':0,
        'native_authenticated_producer_evidence':0,
        'native_decision_records_to_receiver':0,
        'native_scored_receiver_judgments':0,
        'native_operator_updates':0,
        'native_learning_proven':False,
        'source_authenticated_to_receiver':False,
        'posthoc_producer_and_ingress_share_same_scheduler_trace':True,
        'injected_control_packets_are_shadow_only':True,
        'lab_control_loss_fails_closed':True,
        'counterfactual_episode_ids_not_shared_across_worlds':True,
        'declared_criterion_or_utility_identified':False,
    }
    require(all(t.get(k)==v and type(t.get(k)) is type(v) for k,v in required.items()),
            'v1t trust boundary or lineage mismatch')
    for k in ('reference_v1s_sha256','reference_v1m_sha256','reference_v1r_sha256',
              'native_fixture_sha256'):
        h=t.get(k)
        require(type(h) is str and len(h)==64 and
                all(c in '0123456789abcdef' for c in h),
                'v1t malformed digest: '+k)
    frozen=t.get('frozen_native_sources')
    require(type(frozen) is dict and type(frozen.get('frozen_producer_sha256')) is dict and
            len(frozen['frozen_producer_sha256'])==3 and
            frozen.get('compute_function_name')=='_compute_local',
            'missing frozen source inventory')
    rows=t.get('shadow_lab_sessions')
    require(type(rows) is list and len(rows)==58,'incomplete v1t lab inventory')
    grouped={}
    for row in rows:
        require(type(row) is dict and set(row)>={'arm','mode','plan','receiver_view',
                'experimenter_posthoc_counts_not_receiver_visible',
                'received_packets_native','ingress_derived_from_posthoc_trace_not_live_B',
                'episode_id_is_shadow_label_only'},'malformed v1t session')
        arm,mode,plan=row['arm'],row['mode'],row['plan']
        require(arm in ('original','variant') and mode in ('off','on') and
                type(plan) is str and plan and
                row['episode_id_is_shadow_label_only']==f'shadow.native-trace.{arm}.{mode}' and
                row['received_packets_native']==0 and
                row['ingress_derived_from_posthoc_trace_not_live_B'] is True,
                'unbound session or unauthorized native ingress')
        v=row['receiver_view']; counts=row['experimenter_posthoc_counts_not_receiver_visible']
        require(type(v) is dict and type(counts) is dict and
                v.get('native_authority') is False and
                v.get('receiver_scored_judgment') is False and
                v.get('sender_decision_cause_known') is False and
                v.get('independent_absence_certificate') is False and
                type(v.get('received_kinds')) is list and
                set(counts)=={'sender','ingress','consumed','occurrence_count'} and
                all(type(x) is int for x in counts.values()) and
                len(set(counts.values()))==1 and
                next(iter(counts.values()))==(2 if arm=='original' else 0) and
                v.get('receiver_ingress_count')==counts['ingress'],
                'v1t source projection not restricted')
        key=(arm,mode,plan)
        require(key not in grouped,'duplicate v1t source session')
        grouped[key]=row
    require(len(grouped)==58,'duplicate or missing v1t source sessions')
    seeds={}
    for arm in ('original','variant'):
        for mode in ('off','on'):
            full=grouped.get((arm,mode,'all_disclosed'))
            empty=grouped.get((arm,mode,'ingress_only'))
            require(type(full) is dict and type(empty) is dict and
                    empty['receiver_view']['received_kinds']==[] and
                    len(full['receiver_view']['received_kinds'])==5 and
                    full['receiver_view']['classification']==(
                      'INGRESS_OBSERVED_FROM_POSTHOC_PROJECTION' if arm=='original'
                      else 'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY'),
                    'missing native-bound full/empty negative controls')
            seeds[(arm,mode)]={'sender':full['experimenter_posthoc_counts_not_receiver_visible']['sender'],
                               'ingress':full['receiver_view']['receiver_ingress_count']}
    require(all(seeds[(a,'on')]==seeds[(a,'off')] for a in ('original','variant')),
            'BV off/on perturbed native forward seeds')
    return seeds


@dataclass(frozen=True,slots=True)
class LabEnvelope:
    kind:str
    issuer:str
    episode:str
    edge:str
    sequence:int
    generated_tick:int
    delivered_tick:int
    value:int | str
    capability:object


class LabChannel:
    """Bounded transport. Actor capabilities confined to one lab instance."""
    def __init__(self,episode:str,capacity:int=6):
        require(type(episode) is str and episode and type(capacity) is int and
                1<=capacity<=6,'invalid channel configuration')
        self.episode=episode;self.capacity=capacity;self.seals={v:object() for v in ROLES.values()}
        self._sequence=0;self.pending=[];self.failed=False

    def mint(self,kind:str,value:int | str,created:int,deliver:int):
        require(kind in ROLES and type(created) is int and type(deliver) is int and
                0<=created<=deliver<=12 and type(value) in (int,str),
                'invalid research packet')
        self._sequence+=1
        role=ROLES[kind]
        return LabEnvelope(kind,role,self.episode,EDGE,self._sequence,
                           created,deliver,value,self.seals[role])

    def enqueue(self,p:LabEnvelope):
        require(type(p) is LabEnvelope and p.episode==self.episode and
                type(p.sequence) is int and p.sequence>0 and
                not self.failed,'invalid queued evidence')
        if len(self.pending)>=self.capacity:
            self.failed=True;self.pending.clear();return False
        self.pending.append(p)
        return True

    def flush(self,now:int,receiver:'BReceiver'):
        require(type(now) is int and 0<=now<=12,'invalid tick')
        ready=[p for p in self.pending if p.delivered_tick<=now]
        self.pending=[p for p in self.pending if p.delivered_tick>now]
        for p in sorted(ready,key=lambda x:(x.delivered_tick,x.sequence)):
            receiver.accept(p,now)


class BReceiver:
    """Sealed B-local projection: ingress events and delivered control ONLY."""
    def __init__(self,channel:LabChannel):
        require(type(channel) is LabChannel,'bad lab mailbox')
        self._channel=channel;self.episode=channel.episode
        self.tick=0;self.ingress=0;self.messages={};self.sequence_seen=set()
        self.closed=False;self.compromised=False

    def advance(self,tick:int):
        require(not self.closed and type(tick) is int and 0<=tick<=12 and tick>=self.tick,
                'nonmonotonic or closed receiver clock')
        self.tick=tick

    def ingest(self,tick:int):
        self.advance(tick)
        require(tick in (4,5) and self.ingress<2,'invalid or duplicate lab ingress')
        self.ingress+=1

    def accept(self,p:LabEnvelope,now:int):
        require(not self.closed and type(p) is LabEnvelope and
                type(now) is int and now>=self.tick and now<=10 and
                p.kind in ROLES and p.issuer==ROLES[p.kind] and
                p.capability is self._channel.seals[p.issuer] and
                p.episode==self.episode and p.edge==EDGE and
                type(p.sequence) is int and p.sequence>0 and
                p.sequence not in self.sequence_seen and p.kind not in self.messages and
                type(p.generated_tick) is int and type(p.delivered_tick) is int and
                0<=p.generated_tick<=p.delivered_tick<=now and
                type(p.value) in (str,int),'invalid/forged/replayed/out-of-epoch message')
        require((p.kind=='expectation' and p.value=='declared:up-to-two' and
                 p.generated_tick==0 and p.delivered_tick<=1) or
                (p.kind=='decision' and p.value in ('experimenter:CMP1','experimenter:CMP2')
                 and p.generated_tick==3 and 3<=p.delivered_tick<=8) or
                (p.kind=='sender_count' and type(p.value) is int and 0<=p.value<=2 and
                 p.generated_tick==7 and p.delivered_tick in (8,9)) or
                (p.kind in ('sender_coverage','receiver_coverage') and
                 p.value=='lab-window-0-6' and p.generated_tick==7 and
                 p.delivered_tick in (8,9)),
                'invalid packet temporal/content protocol')
        self.advance(now)
        self.messages[p.kind]=p.value
        self.sequence_seen.add(p.sequence)

    def close(self,now:int):
        self.advance(now)
        require(now>=9,'premature episode close: cannot infer absence')
        self.closed=True

    def view(self):
        require(self.closed,'no verdict before explicitly closed lab interval')
        x=self.messages
        if self.compromised or self._channel.failed:
            classification='CONTROL_FAULT_UNKNOWN'
        elif 'sender_count' in x and self.ingress>x['sender_count']:
            classification='CONFLICTING_EVIDENCE_UNKNOWN'
        elif self.ingress>0:
            classification='LAB_INGRESS_OBSERVED'
        elif 'expectation' not in x:
            classification='NO_RECEIVED_EXPECTATION_UNKNOWN'
        elif 'sender_count' not in x:
            classification='NO_SENDER_REPORT_UNKNOWN'
        elif 'sender_coverage' not in x or 'receiver_coverage' not in x:
            classification='UNCOVERED_INTERVAL_UNKNOWN'
        elif x['sender_count']==0:
            classification='LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY'
        else:
            classification='LAB_POSSIBLE_TRANSPORT_GAP_CONDITIONAL_ONLY'
        return {
            'classification':classification,
            'receiver_ingress_count':self.ingress,
            'received_kinds':sorted(x),
            'shadow_decision_visible':'decision' in x,
            'native_receiver':False,'native_authority':False,
            'native_absence_certificate':False,'sender_decision_causal_role_known':False,
            'receiver_scored_judgment':False,'operator_update_committed':False,
        }


def run_lab(arm:str,mode:str,plan:str,counts:dict):
    require(arm in ('original','variant') and mode in ('off','on') and plan in PLANS,
            'unrecognized control scenario')
    expected=2 if arm=='original' else 0
    require(type(counts) is dict and counts=={'sender':expected,'ingress':expected},
            'unexpected source-bound counts')
    episode=f'lab.incremental.{arm}.{mode}'
    channel=LabChannel(episode)
    receiver=BReceiver(channel)
    # Research clock, NOT the real scheduler's clock. Expectation precedes
    # the source's simulated decision and future ingress observations.
    specs=[('expectation','declared:up-to-two',0,1),
           ('decision','experimenter:CMP1' if arm=='original' else 'experimenter:CMP2',3,3),
           ('sender_count',0 if plan=='contradictory_source' else expected,7,8),
           ('sender_coverage','lab-window-0-6',7,8),
           ('receiver_coverage','lab-window-0-6',7,8)]
    excluded={
       'ingress_only':set(ROLES),'source_lost':{'sender_count'},
       'expectation_lost':{'expectation'},'sender_coverage_lost':{'sender_coverage'},
       'receiver_coverage_lost':{'receiver_coverage'},'decision_lost':{'decision'},
       'control_loss':{'sender_count'},
    }.get(plan,set())
    # Packets must be CREATED at their source tick. Nothing is pre-queued
    # from a future producer step, even inside this deliberately synthetic lab.
    due={tick:[] for tick in range(10)}
    for kind,value,created,delivered in specs:
        if kind not in excluded:due[created].append((kind,value,delivered))
    accepted_attack=0;rejected_attack=0
    for tick in range(10):
        receiver.advance(tick)
        # This time step is the ONLY point when producer/observer packets
        # may be minted. The driver does not enqueue certificates in advance.
        for kind,value,delivered in due[tick]:
            require(channel.enqueue(channel.mint(kind,value,tick,delivered)),
                    'unexpected queue overflow in ordinary scenario')
        if tick in (4,5) and tick-4<expected:receiver.ingest(tick)
        channel.flush(tick,receiver)
        if tick==8:
            # Injection after legitimate packets; no chance to pre-empt delivery.
            if plan in ('forged','replayed','wrong_episode','late','out_of_order'):
                msg=channel.mint('sender_count',expected,7,8)
                if plan=='forged':msg=replace(msg,capability=object())
                elif plan=='replayed':msg=replace(msg,sequence=3)
                elif plan=='wrong_episode':msg=replace(msg,episode='lab.incremental.other')
                elif plan=='late':msg=replace(msg,delivered_tick=11)
                elif plan=='out_of_order':msg=replace(msg,generated_tick=9)
                try:receiver.accept(msg,8)
                except (ValueError,AssertionError,TypeError):rejected_attack+=1
                else:accepted_attack+=1
            if plan=='bounded_queue_overflow':
                for i in range(7):
                    packet=channel.mint('decision','experimenter:CMP1',3,8)
                    if not channel.enqueue(packet):break
                require(channel.failed,'overflow should fail closed')
            if plan=='control_loss':receiver.compromised=True
        # The channel delivered this tick before any adversarial injection.
    receiver.close(10)
    out=receiver.view()
    require(accepted_attack==0 and (rejected_attack==1)==(
            plan in ('forged','replayed','wrong_episode','late','out_of_order')),
            'adversarial delivery accepted or silently ignored')
    return {'arm':arm,'mode':mode,'plan':plan,
            'lab_episode':episode,'lab_clock_not_native':True,
            'seed_origin':'POSTHOC_V1T_PRODUCER_COUNTS_ONLY',
            'research_simulated_ingress_events':expected,
            'experimenter_source_counts_not_in_B_view':dict(counts),
            'receiver_view':out,'rejected_attack_packets':rejected_attack,
            'native_stream_messages_delivered':0,
            'lab_backpressure_tripped':channel.failed}


def analyze(t:dict,raw:bytes):
    seeds=validate_source(t,raw)
    sessions=[run_lab(arm,mode,plan,seeds[(arm,mode)])
              for arm in ('original','variant') for mode in ('off','on')
              for plan in PLANS if not (plan=='contradictory_source' and arm=='variant')]
    require(len(sessions)==58, 'unexpected number of finite streamed scenarios')
    s={(r['arm'],r['mode'],r['plan']):r for r in sessions}
    for mode in ('off','on'):
        all_=s['variant',mode,'all_disclosed']['receiver_view']
        loss=s['variant',mode,'source_lost']['receiver_view']
        empty=s['variant',mode,'ingress_only']['receiver_view']
        require(all_['classification']=='LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY' and
                loss['classification']=='NO_SENDER_REPORT_UNKNOWN' and
                empty['classification']=='NO_RECEIVED_EXPECTATION_UNKNOWN' and
                s['variant',mode,'control_loss']['receiver_view']['classification']=='CONTROL_FAULT_UNKNOWN' and
                s['variant',mode,'bounded_queue_overflow']['receiver_view']['classification']=='CONTROL_FAULT_UNKNOWN' and
                s['original',mode,'all_disclosed']['receiver_view']['classification']=='LAB_INGRESS_OBSERVED' and
                s['original',mode,'contradictory_source']['receiver_view']['classification']=='CONFLICTING_EVIDENCE_UNKNOWN',
                'incremental knowledge/control-loss regression')
    require(all(not row['receiver_view']['native_authority'] and
                not row['receiver_view']['receiver_scored_judgment'] and
                not row['receiver_view']['native_absence_certificate'] and
                row['native_stream_messages_delivered']==0 and
                row['lab_clock_not_native'] for row in sessions),
            'lab shadow signal promoted to native')
    return {
        'schema':SCHEMA,'status':STATUS,
        'source_kind':'ATTESTED_NATIVE_V1T_PLUS_RESEARCH_OWNED_INCREMENTAL_CLOCK',
        'reference_v1t_sha256':sha256(raw).hexdigest(),
        'reference_v1m_sha256':t['reference_v1m_sha256'],
        'reference_v1s_sha256':t['reference_v1s_sha256'],
        'native_fixture_sha256':t['native_fixture_sha256'],
        'frozen_native_sources':t['frozen_native_sources'],
        'inherited_native_v1t_recomputation_verified_in_this_run':False,
        'new_native_scheduler_runs_in_this_module':0,
        'native_scheduler_callback_connected':False,
        'native_receiver_received_live_control_packets':0,
        'native_authenticated_source_evidence':0,
        'native_independent_absence_certificates':0,
        'native_scored_receiver_judgments':0,
        'native_operator_updates':0,'native_learning_proven':False,
        'lab_incremental_session_count':len(sessions),
        'lab_incremental_sessions':sessions,
        'lab_ingress_is_simulated_from_posthoc_count':True,
        'lab_tick_is_simulated_not_native':True,
        'lab_control_loss_fails_closed':True,
        'lab_queue_overflow_fails_closed':True,
        'no_cross_world_event_pairing':True,
        'producer_posthoc_counts_withheld_from_receiver':True,
        'claims_excluded':list(EXCLUDED),
    }
