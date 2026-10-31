"""Research v2f vertical slice: source-owned tick batches and receiver-local feedback.

NEW finite research semantics. Not frozen CMP, not a native scheduler port, not
cryptographic authority or independently attested feedback. Forward execution
never reads the observer or a mailbox. BV feedback uses separate queued events.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from heapq import heappush, heappop
from collections import defaultdict
from typing import Callable

from spk_backvalidation_v2.observed_scheduler_v2a import (
    ObserverV2a, ObservationV2a, PORT_VERSION, check,
)

VERSION = 'spk-bv-batched-feedback-executor/research-v2f'
NODES = ('A', 'B', 'C')
OPERATORS = ('relay', 'block', 'pair')
MAX_TICK = 256
MAX_INPUTS = 16
MAX_CONTROL_CAPACITY = 128

@dataclass(frozen=True, slots=True)
class BatchCaseV2f:
    episode: str
    recipe: tuple[tuple[int, int], ...]  # (template index, arrival tick)
    operators: tuple[str, str, str] = ('relay','relay','relay')
    hop_delay: int = 1

@dataclass(frozen=True, slots=True)
class FeedbackV2f:
    issuer: str
    recipient: str
    source_emission: str
    receiving_decision: str
    response: int
    created_tick: int
    arrival_tick: int

class MailboxV2f:
    """Receiver's local copy of messages actually delivered, not observer telemetry.

    Loss/overflow are explicit. No absence judgment from a missing packet.
    """
    def __init__(self, capacity: int = MAX_CONTROL_CAPACITY,
                 accept: Callable[[FeedbackV2f], bool] | None = None):
        check(type(capacity) is int and 1 <= capacity <= MAX_CONTROL_CAPACITY,
              'invalid feedback capacity')
        check(accept is None or callable(accept), 'invalid loss policy')
        self.capacity, self.accept = capacity, accept
        self._received: dict[str, list[FeedbackV2f]] = {n: [] for n in NODES}
        self.overflow = False
        self.lost = 0
        self._seen: set[tuple[str,str,str]] = set()

    def _deliver(self, record: FeedbackV2f, *, issued: dict[str, tuple[str,str]]):
        check(type(record) is FeedbackV2f, 'untyped control')
        check(record.issuer in NODES and record.recipient in NODES and
              type(record.source_emission) is str and
              type(record.receiving_decision) is str and
              type(record.response) is int and record.response in (-1,1) and
              type(record.created_tick) is int and type(record.arrival_tick) is int and
              record.created_tick < record.arrival_tick,
              'invalid feedback shape')
        src = issued.get(record.source_emission)
        check(src is not None and src == (record.recipient,record.issuer),
              'invalid causal feedback source')
        key = (record.source_emission,record.issuer,record.receiving_decision)
        check(key not in self._seen, 'duplicate feedback replay')
        self._seen.add(key)
        if self.accept is not None:
            try:
                if self.accept(record) is not True:
                    self.lost += 1
                    return 'LOST'
            except Exception:
                self.lost += 1
                return 'FAULT_LOST'
        if sum(len(x) for x in self._received.values()) >= self.capacity:
            self.overflow = True
            return 'OVERFLOW_UNKNOWN'
        self._received[record.recipient].append(record)
        return 'DELIVERED'

    def view(self, actor):
        check(actor in NODES, 'unknown mailbox actor')
        return tuple(self._received[actor])

    def summary(self):
        return {'research_delivered_by_recipient':{
                    n:len(self._received[n]) for n in NODES},
                'research_delivered_total':sum(map(len,self._received.values())),
                'research_lost':self.lost,'research_overflow':self.overflow,
                'absence_certificates':0,'authentication_verified':False,
                'native_control_messages':0}


def validate_case(case):
    check(type(case) is BatchCaseV2f and type(case.episode) is str and
          1<=len(case.episode)<=64 and all(c.isascii() and
          (c.isalnum() or c in '._-') for c in case.episode),
          'invalid research case')
    check(type(case.recipe) is tuple and 1<=len(case.recipe)<=MAX_INPUTS and
          all(type(x) is tuple and len(x)==2 and type(x[0]) is int and x[0] in (0,1)
              and type(x[1]) is int and 1<=x[1]<=MAX_TICK-24
              for x in case.recipe) and
          tuple(t for _,t in case.recipe)==tuple(sorted(t for _,t in case.recipe)),
          'invalid input recipe')
    check(type(case.operators) is tuple and len(case.operators)==3 and
          all(type(o) is str and o in OPERATORS for o in case.operators) and
          type(case.hop_delay) is int and 1<=case.hop_delay<=8,
          'invalid operators or hop delay')
    return True


def execute_batch_v2f(case: BatchCaseV2f, *, observe: ObserverV2a | None = None,
                       feedback: bool = False, mailbox: MailboxV2f | None = None):
    """Execute online events in tick batches with separate recipient feedback.

    A decision is produced per (actor,tick) batch. `pair` selects every second
    batch at that actor; no assertion that this implements native CMP. Each
    receiver independently judges a *real admitted parent* using its own
    selected/not-selected forward decision, then sends an asynchronous control
    item to the parent's emitting actor. This is RESEARCH actor delivery only.
    """
    validate_case(case)
    check(type(feedback) is bool and (observe is None or type(observe) is ObserverV2a)
          and (mailbox is None or type(mailbox) is MailboxV2f), 'invalid executor controls')
    check(feedback or mailbox is None, 'mailbox without feedback mode')
    if feedback:
        check(mailbox is not None, 'feedback mode requires new mailbox')
    if observe is not None:
        observe._attach()
    heap = []
    serial = 0
    for i, (_,tick) in enumerate(case.recipe):
        heappush(heap,(tick,serial,'FORWARD','A',f'env.{i}'))
        serial += 1
    batch_count = {n:0 for n in NODES}
    emissions = {n:0 for n in NODES}
    routes = {'A->B':0,'B->C':0}
    emission_ticks = {n:[] for n in NODES}
    emitted_to: dict[str,tuple[str,str]] = {}
    decisions=[]
    terminal=[]
    research_judgments=[]
    ordinal=0
    processed_forward_events=0
    processed_batches=0
    current_tick=0

    def notify(phase, actor, target, decision_id, parent, token):
        nonlocal ordinal
        if observe is not None:
            observe._publish(ObservationV2a(PORT_VERSION,case.episode,ordinal,
                current_tick,phase,actor,target,decision_id,parent,token))
        ordinal+=1

    try:
        while heap:
            tick, seq, kind, actor, parent = heappop(heap)
            check(tick>=current_tick and tick<=MAX_TICK,'nonmonotone research clock')
            current_tick=tick
            if kind=='CONTROL':
                check(feedback and type(parent) is FeedbackV2f and
                      actor==parent.recipient and tick==parent.arrival_tick,
                      'invalid feedback transport')
                mailbox._deliver(parent,issued=emitted_to)
                continue
            check(kind=='FORWARD' and actor in NODES, 'unsupported queue item')
            arrivals=[parent]
            # Same actor and same logical tick are admitted *as one batch*.
            # Other actors at the tick are unaffected by aggregation.
            other=[]
            while heap and heap[0][0]==tick:
                x=heappop(heap)
                if x[2]=='FORWARD' and x[3]==actor:
                    arrivals.append(x[4])
                else:
                    other.append(x)
            for x in other:
                heappush(heap,x)
            check(len(set(arrivals))==len(arrivals), 'duplicate admitted parent')
            for source_token in arrivals:
                if actor!='A':
                    check(source_token in emitted_to and
                          emitted_to[source_token][1]==actor,
                          'orphan or wrong-target forward input')
                    notify('receiver_ingress',actor,NODES[NODES.index(actor)-1],
                           '',source_token,source_token)
                processed_forward_events+=1
            processed_batches+=1
            batch_count[actor]+=1
            node_ix=NODES.index(actor)
            target=NODES[node_ix+1] if node_ix<2 else 'TERMINAL'
            did=f'{case.episode}.{actor}.d{batch_count[actor]}'
            op=case.operators[node_ix]
            selected=op=='relay' or (op=='pair' and batch_count[actor]%2==0)
            notify('predecision_expectation',actor,target,did,arrivals[0],'')
            notify('decision',actor,target,did,arrivals[0],'')
            decisions.append({'id':did,'actor':actor,'tick':tick,
                              'parents':tuple(arrivals),'selected':selected,
                              'operator':op})
            # Causal feedback is scored by the actual *receiving* actor's decision.
            # Distinct control queue. No scoring from posthoc counts or telemetry.
            if feedback and actor!='A':
                prior_actor=NODES[node_ix-1]
                for token in arrivals:
                    check(emitted_to[token]==(prior_actor,actor),
                          'causal issuer/recipient mismatch')
                    pkt=FeedbackV2f(actor,prior_actor,token,did,
                                    1 if selected else -1,tick,tick+1)
                    research_judgments.append(pkt)
                    heappush(heap,(tick+1,serial,'CONTROL',prior_actor,pkt))
                    serial+=1
            if not selected:
                continue
            emissions[actor]+=1
            token=f'{case.episode}.{actor}.e{emissions[actor]}'
            check(token not in emitted_to, 'duplicate source-owned emission')
            emitted_to[token]=(actor,target)
            notify('sender_port_emission',actor,target,did,arrivals[0],token)
            emission_ticks[actor].append(tick)
            if target=='TERMINAL':
                terminal.append(token)
            else:
                routes[f'{actor}->{target}']+=1
                check(tick+case.hop_delay<MAX_TICK,'forward event beyond horizon')
                heappush(heap,(tick+case.hop_delay,serial,'FORWARD',target,token))
                serial+=1
        current_tick+=1
        check(current_tick<=MAX_TICK,'invalid close tick')
        notify('interval_coverage_close','SCHEDULER','OBSERVER',
               case.episode+'.close','','')
        return {
            'executor_version':VERSION, 'episode':case.episode,
            'input_ticks':[t for _,t in case.recipe],
            'input_template_indices':[i for i,_ in case.recipe],
            'operator_program':list(case.operators),
            'batch_admissions':batch_count,
            'processed_batches':processed_batches,
            'processed_forward_events':processed_forward_events,
            'forward_emissions':emissions,'forward_routes':routes,
            'forward_terminal_count':len(terminal),
            'forward_terminal_tokens':terminal,
            'emission_ticks':emission_ticks,
            'decisions':decisions, 'observer_records_offered':ordinal,
            'feedback_enabled':feedback,
            'research_receiver_local_judgments':len(research_judgments),
            'research_feedback_delivered':mailbox.summary() if feedback else None,
            'research_score_by_sender':(
                {n:sum(p.response for p in mailbox.view(n)) for n in NODES}
                if feedback else None),
            'native_B_control_packets':0,'native_operator_updates':0,
            'native_learning_proven':False,
        }
    finally:
        if observe is not None:
            observe._detach()


def forward_projection(result):
    """Only the forward fields: remove research observer and BV control effects."""
    return {k:result[k] for k in (
        'input_ticks','input_template_indices','operator_program',
        'batch_admissions','processed_batches','processed_forward_events',
        'forward_emissions','forward_routes','forward_terminal_count',
        'forward_terminal_tokens','emission_ticks','decisions')}
