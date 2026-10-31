"""BV v1s: closed-world, receiver-readable *separate* evidence channel.

This is a stateful capability-labelled process simulation. Python object-identity
capabilities are ONLY a laboratory assumption, NOT transport authentication,
cryptography, a native SPK proof, or evidence of a neuron-originated judgment.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import (
    SCHEMA as R_SCHEMA, STATUS as R_STATUS, canon,
)

SCHEMA='spk-bv-separated-receiver-disclosure-channel-shadow/v1s'
STATUS='SOURCE_BOUND_SHADOW_CHANNEL_NO_NATIVE_RECEIVER_AUTHORITY'
DIRECT_EDGE='A->B:7->0'
EPISODE='lab.future.episode'
EVENT='lab.future.A.to.B.expected.1'
KINDS={'expectation':'planner', 'sender_port':'sender_tap',
       'sender_coverage':'sender_tap', 'receiver_coverage':'receiver_tap',
       'decision':'sender_decision'}
EXCLUDED=[
    'lab-object-capabilities-are-not-cryptographic-or-native-authentication',
    'separate-shadow-channel-not-connected-to-frozen-native-neurons',
    'lab-closed-coverage-not-independent-native-absence-certificate',
    'decision-disclosure-does-not-prove-causal-role-of-decision',
    'source-bound-v1r-counterfactuals-never-shared-with-receiver',
    'transport-failure-must-not-be-promoted-to-sender-silence',
    'two-logical-lab-taps-not-independent-native-attestation',
    'no-receiver-value-criterion-or-scored-feedback-or-operator-update',
    'no-learning-or-certified-algebra-architecture-promotion',
]


@dataclass(frozen=True)
class Packet:
    kind: str
    issuer: str
    episode: str
    event_id: str
    source: str
    receiver: str
    source_channel: int
    receiver_channel: int
    created_at: int
    delivered_at: int
    data: str
    seal: object  # intentionally opaque process-local capability, not serializable trust


class IsolatedBus:
    """Deterministic toy bus. Only this object mints process-local role seals."""
    def __init__(self):
        self._caps={role:object() for role in set(KINDS.values())}

    def mint(self,kind:str,data:str,*,created_at:int,delivered_at:int,
             episode:str=EPISODE,event_id:str=EVENT,source:str='A',
             receiver:str='B',source_channel:int=7,receiver_channel:int=0):
        require(kind in KINDS and type(data) is str and data and
                type(created_at) is int and type(delivered_at) is int and
                created_at>=0 and delivered_at>=created_at,
                'invalid laboratory channel packet')
        return Packet(kind,KINDS[kind],episode,event_id,source,receiver,
                      source_channel,receiver_channel,created_at,delivered_at,
                      data,self._caps[KINDS[kind]])


class ReceiverMailbox:
    """B has only local ingress and packets actually *delivered* to this mailbox."""
    def __init__(self,bus:IsolatedBus,*,ingress:int,verdict_at:int=9):
        require(type(bus) is IsolatedBus and type(ingress) is int and
                ingress>=0 and type(verdict_at) is int and verdict_at>=7,
                'invalid mailbox configuration')
        self._bus=bus
        self.ingress=ingress
        self.verdict_at=verdict_at
        self.received={}

    def deliver(self,p:Packet):
        require(type(p) is Packet and p.kind in KINDS and
                p.issuer==KINDS[p.kind] and
                p.seal is self._bus._caps[p.issuer] and
                (p.episode,p.event_id,p.source,p.receiver,p.source_channel,p.receiver_channel)==
                (EPISODE,EVENT,'A','B',7,0) and
                type(p.created_at) is int and type(p.delivered_at) is int and
                0<=p.created_at<=p.delivered_at<=self.verdict_at and
                p.kind not in self.received and type(p.data) is str,
                'unauthorized, replayed, wrong-scope or late disclosure')
        temporal={
            'expectation':p.created_at==0 and p.delivered_at<=2 and p.data=='expect:1',
            'sender_port':p.created_at>=7 and p.data in ('emitted:0','emitted:1'),
            'sender_coverage':p.created_at>=7 and p.data=='covered:0..6',
            'receiver_coverage':p.created_at>=7 and p.data=='covered:0..6',
            'decision':p.created_at==3 and p.delivered_at>=3 and
                       p.data in ('selected:CMP1','selected:CMP2'),
        }
        require(temporal[p.kind], 'invalid disclosure content or temporal authority')
        self.received[p.kind]=p

    def classify(self):
        """No world-state access; no utility judgment, no inference of internal cause."""
        decision=self.received.get('decision')
        visible=decision is not None
        # Ingress observation is local. For positive ingress, event identity and
        # causal origin are NOT independently authenticated by this count.
        sender_port=self.received.get('sender_port')
        if self.ingress and sender_port is not None and (
                self.ingress>int(sender_port.data.partition(':')[2])):
            status='CONFLICTING_LAB_PORT_DISCLOSURES_UNKNOWN'
        elif self.ingress:
            status='LOCAL_INGRESS_OBSERVED_NO_CAUSAL_JUDGMENT'
        elif 'expectation' not in self.received:
            status='NO_RECEIVED_PREDECISION_EXPECTATION'
        elif 'sender_port' not in self.received:
            status='SENDER_PORT_INFORMATION_UNAVAILABLE'
        elif ('sender_coverage' not in self.received or
              'receiver_coverage' not in self.received):
            status='COVERAGE_INFORMATION_UNAVAILABLE'
        elif self.received['sender_port'].data=='emitted:0':
            status='LAB_SENDER_PORT_SILENCE_WITH_BOTH_COVERAGES'
        else:
            status='LAB_POSSIBLE_TRANSPORT_GAP_WITH_BOTH_COVERAGES'
        return {'classification':status,
                'receiver_ingress_count':self.ingress,
                'received_evidence_kinds':sorted(self.received),
                'receiver_received_decision_record':visible,
                'sender_internal_cause_identified':False,
                'native_authority':False,
                'receiver_scored_judgment':False}


def replay_lab(name:str):
    """Finite adversarial toy worlds. None are native SPK runtime executions."""
    require(name in CASES,'unknown lab scenario')
    config=CASES[name];bus=IsolatedBus()
    box=ReceiverMailbox(bus,ingress=config.get('ingress',0))
    rejected=0
    kinds=['expectation','sender_port','sender_coverage','receiver_coverage','decision']
    packets={
        'expectation':lambda:bus.mint('expectation','expect:1',created_at=0,delivered_at=1),
        'sender_port':lambda:bus.mint('sender_port','emitted:'+str(config.get('emitted',0)),created_at=7,delivered_at=8),
        'sender_coverage':lambda:bus.mint('sender_coverage','covered:0..6',created_at=7,delivered_at=8),
        'receiver_coverage':lambda:bus.mint('receiver_coverage','covered:0..6',created_at=7,delivered_at=8),
        'decision':lambda:bus.mint('decision','selected:CMP2',created_at=3,delivered_at=4),
    }
    omission=set(config.get('omit',()))
    require(omission<=set(kinds),'invalid scenario omit list')
    for k in kinds:
        if k not in omission:box.deliver(packets[k]())
    malicious=config.get('malicious')
    if malicious:
        from dataclasses import replace
        base=packets['sender_port']()
        if malicious=='duplicate':base=box.received['sender_port']
        elif malicious=='forgery':base=replace(base,seal=object())
        elif malicious=='wrong_receiver':base=replace(base,receiver='C')
        elif malicious=='wrong_event':base=replace(base,event_id='other.event')
        elif malicious=='late':base=replace(base,delivered_at=10)
        elif malicious=='changed_data':base=replace(base,data='emitted:100')
        elif malicious=='wrong_issuer':base=replace(base,issuer='planner')
        elif malicious=='wrong_episode':base=replace(base,episode='other.episode')
        elif malicious=='dict_payload':base={'kind':'sender_port','data':'emitted:0'}
        else:raise ValueError('unrecognized malicious packet')
        try:box.deliver(base)
        except (ValueError,TypeError,AttributeError,AssertionError):rejected+=1
        else:raise AssertionError('adversarial packet was incorrectly accepted')
    return {**box.classify(), 'scenario':name,'rejected_untrusted_packets':rejected,
            'shadow_only':True}


CASES={
    'delivered':{'ingress':1,'emitted':1},
    'contradictory_ingress':{'ingress':1,'emitted':0},
    'port_silence':{'ingress':0,'emitted':0},
    'transport_gap':{'ingress':0,'emitted':1},
    'no_expectation':{'ingress':0,'emitted':0,'omit':('expectation',)},
    'control_lost':{'ingress':0,'emitted':1,'omit':('sender_port',)},
    'sender_tap_lost':{'ingress':0,'emitted':0,'omit':('sender_coverage',)},
    'receiver_tap_lost':{'ingress':0,'emitted':1,'omit':('receiver_coverage',)},
    'decision_not_disclosed':{'ingress':0,'emitted':0,'omit':('decision',)},
    'only_ingress':{'ingress':0,'emitted':0,'omit':tuple(KINDS)},
    'only_ingress_alternate_world':{'ingress':0,'emitted':1,'omit':tuple(KINDS)},
    'untrusted_duplicate':{'ingress':0,'emitted':0,'malicious':'duplicate'},
    'untrusted_forgery':{'ingress':0,'emitted':0,'malicious':'forgery'},
    'wrong_receiver_C':{'ingress':0,'emitted':0,'malicious':'wrong_receiver'},
    'wrong_event':{'ingress':0,'emitted':0,'malicious':'wrong_event'},
    'stale_receipt':{'ingress':0,'emitted':0,'malicious':'late'},
    'altered_payload':{'ingress':0,'emitted':0,'malicious':'changed_data'},
    'incorrect_issuer':{'ingress':0,'emitted':0,'malicious':'wrong_issuer'},
    'wrong_episode':{'ingress':0,'emitted':0,'malicious':'wrong_episode'},
    'untrusted_json':{'ingress':0,'emitted':0,'malicious':'dict_payload'},
}


def validate_r(r,raw):
    """Read-only source-bound validation; CLI additionally replays v1r in full."""
    require(type(r) is dict and type(raw) is bytes and raw==canon(r) and
            r.get('schema')==R_SCHEMA and r.get('status')==R_STATUS and
            r.get('source_kind')=='SOURCE_BOUND_NATIVE_FACTORIAL_POSTHOC_ONLY' and
            r.get('native_v1q_recomputation_verified_in_this_run') is True and
            r.get('new_native_scheduler_runs_in_this_module')==0 and
            r.get('factored_native_matrix_runs_in_source')==16 and
            r.get('allocation_order_variability_present') is True and
            r.get('receiver_exposed_to_allocation') is False and
            r.get('native_scored_receiver_judgments')==0 and
            r.get('native_operator_updates')==0 and
            r.get('native_learning_proven') is False and
            r.get('causal_credit_or_utility_identified') is False and
            type(r.get('posthoc_rational_allocation')) is dict and
            type(r['posthoc_rational_allocation'].get('off')) is dict and
            type(r['posthoc_rational_allocation']['off'].get('terminal')) is dict and
            type(r['posthoc_rational_allocation']['off']['terminal'].get('suppress_activity')) is dict and
            r['posthoc_rational_allocation']['off']['terminal']['suppress_activity'].get('equal_permutation_average')==
               {'A':'1','B':'1/2','C':'1/2'} and
            r.get('nonadditivity_diagnostics',{}).get('off',{}).get('terminal',{}).get('nonadditive_correction')==2,
            'untrusted or inconsistent v1r source authority/accounting')
    from spk_bv_research.native_factorial_interaction_v1q import METRICS
    from spk_bv_research.native_allocation_boundary_v1r import allocate
    from fractions import Fraction
    for mode in ('off','on'):
        alloc=r['posthoc_rational_allocation'].get(mode)
        require(type(alloc) is dict and set(alloc)==set(METRICS),
                'incomplete metric allocation inventory')
        for metric in METRICS:
            p=alloc[metric]
            require(type(p) is dict and set(p)=={'preserve_activity','suppress_activity'} and
                    all(type(p[k]) is dict for k in p),
                    'incomplete v1r allocation policies')
            for sign,polarity in [('preserve_activity',1),('suppress_activity',-1)]:
                data=p[sign]
                # Source matrix isn't duplicated in v1r. Enforce cross-policy
                # sign identities and the known fixture totals; full byte replay
                # in CLI remains the authoritative predecessor validation.
                require(type(data) is dict and
                        data.get('equal_permutation_average_is_a_convention_not_credit') is True and
                        set(data.get('equal_permutation_average',{}))=={'A','B','C'} and
                        all(type(v) is str for v in data['equal_permutation_average'].values()),
                        'invalid v1r descriptive allocation')
            require(all(Fraction(p['preserve_activity']['equal_permutation_average'][n])==
                        -Fraction(p['suppress_activity']['equal_permutation_average'][n])
                        for n in ('A','B','C')),
                    'v1r polarity mismatch')
    pins=('reference_v1q_sha256','native_fixture_sha256')
    require(all(type(r.get(k)) is str and len(r[k])==64 and
                all(c in '0123456789abcdef' for c in r[k]) for k in pins) and
            type(r.get('frozen_native_sources')) is dict and bool(r['frozen_native_sources']),
            'missing v1r custody pins')
    return True


def analyze(r,raw):
    validate_r(r,raw)
    cases=[replay_lab(name) for name in CASES]
    lookup={a['scenario']:a for a in cases}
    require(lookup['only_ingress']['classification']==
            lookup['only_ingress_alternate_world']['classification'] and
            lookup['only_ingress']['received_evidence_kinds']==
            lookup['only_ingress_alternate_world']['received_evidence_kinds'],
            'ingress-only noninterference failed')
    require(lookup['port_silence']['classification']!=
            lookup['transport_gap']['classification'] and
            lookup['control_lost']['classification']=='SENDER_PORT_INFORMATION_UNAVAILABLE',
            'separate-channel loss/silence partition failed')
    require(all(not a['native_authority'] and not a['receiver_scored_judgment'] and
                not a['sender_internal_cause_identified'] for a in cases),
            'laboratory result promoted to native credit')
    return {
        'schema':SCHEMA,'status':STATUS,
        'source_kind':'SOURCE_BOUND_V1R_PLUS_ISOLATED_IN_PROCESS_CHANNEL_LAB',
        'reference_v1r_sha256':sha256(raw).hexdigest(),
        'reference_v1q_sha256':r['reference_v1q_sha256'],
        'native_fixture_sha256':r['native_fixture_sha256'],
        'frozen_native_sources':r['frozen_native_sources'],
        'inherited_native_v1r_recomputation_verified_in_this_run':False,
        'lab_actor_model':'B_LOCAL_MAILBOX_PLUS_ROLE_SEALED_SEPARATE_CONTROL_DELIVERY',
        'lab_authentication_assumption':'PYTHON_OBJECT_IDENTITY_ONLY_NOT_NATIVE_AUTHENTICATION',
        'native_separate_disclosure_channel_installed':False,
        'native_receiver_authorized_absence_witnesses':0,
        'native_receiver_judgments':0,
        'native_operator_updates':0,'native_learning_proven':False,
        'native_producer_matrix_shared_with_receiver':False,
        'lab_cases':cases,'lab_case_count':len(cases),
        'lab_ingress_only_worlds_indistinguishable':True,
        'lab_separate_channel_can_distinguish_port_silence_from_transport_gap':True,
        'lab_control_loss_fails_closed':True,
        'sender_decision_causality_identified':False,
        'network_utility_identified':False,
        'claims_excluded':EXCLUDED,
    }
