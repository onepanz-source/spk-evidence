"""V5-T2f research-only: paid semantic *decision* custody for a logical island.

A's explicit decision witness is minted by the separate research host after an
actual frozen A1b execution, EVEN IF A EMITS NOTHING. It is not a native event.
C's sensor and closure are replayed on A1b, then a distinct, chargeable derived
control route C->B->A conveys positive/negative/abstain. No paid shadow operation
is asserted to run inside frozen BV v0e. No real sensor, signed issuer, or learner.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from spk_v5_research.island_objective_v5t1 import CANDIDATES, digest
from spk_v5_research.island_endogenous_demand_v5t2c import (
    DemandEpisode, ClosedReceipt, generate_corpus, observe_closed_episode,
    verify_closed_receipt,
)

SCHEMA = 'spk-v5-t2f-explicit-island-decision-reward-custody/research-v0'
STAGES = ('decision_commit', 'A_to_B', 'B_to_C', 'C_observe_close',
          'C_to_B', 'B_to_A', 'A_consume')
TRANSIT = frozenset(('A_to_B', 'B_to_C', 'C_to_B', 'B_to_A'))
STAGE_OFFSET = (2, 3, 4, 6, 7, 8, 9)
# PE charge at every stage; O/E transient memory is local to a stage, S at consumer.
MEM_CHARGE = (1, 2, 2, 2, 2, 2, 1)


class AdmissionError(ValueError):
    """Insufficient, invalid, or unowned shadow resources; no reward granted."""


@dataclass(frozen=True)
class ChargePlan:
    pe_units: int = 7
    memory_units: int = 12
    link_units: int = 4
    pe_per_tick: int = 1
    link_per_tick: int = 1
    lost_stage: str | None = None

    def __post_init__(self):
        if (any(type(n) is not int or n < 0 for n in
                (self.pe_units, self.memory_units, self.link_units,
                 self.pe_per_tick, self.link_per_tick)) or
                self.lost_stage not in (None, *TRANSIT)):
            raise AdmissionError('invalid shadow plan or drop stage')


@dataclass(frozen=True)
class DecisionWitness:
    episode_id: str
    action: str
    start_tick: int
    decision_tick: int
    has_A_spike: bool
    observed_C_forward_ticks: tuple[int, ...]
    c_closure_tick: int
    prefix_digest: str
    token: str
    # This proof is source-replayed, but NOT signed by the native A neuron.
    origin: str = 'external_shadow_host_not_frozen_A'


def witnessed_decision(record: DemandEpisode, action: str) -> tuple[DecisionWitness, ClosedReceipt]:
    if type(record) is not DemandEpisode or action not in CANDIDATES:
        raise AdmissionError('invalid episode or action')
    # Commit source action in a sensor-blind replay. No late C observation,
    # truth bit, task-label or reward is included in the token.
    prefix = observe_closed_episode(replace(record, demand=None), action)
    receipt = observe_closed_episode(record, action)  # separately executes A1b
    verify_closed_receipt(record, action, receipt)
    if prefix.c_forward_ticks != receipt.c_forward_ticks:
        raise AdmissionError('future sensor affected decision prefix')
    start = record.episode.inputs[0][0]
    if record.episode.inputs[-1][0] > start+2 or receipt.closure_tick != start+6:
        raise AdmissionError('decision timestamp would precede source or closure')
    fields = (record.episode.identity, action, start, start+2,
              bool(prefix.c_forward_ticks), prefix.c_forward_ticks,
              start+6, digest((record.episode.__dict__, action, prefix.c_forward_ticks)))
    witness = DecisionWitness(*fields, digest(fields))
    return witness, receipt


def verify_witness(record: DemandEpisode, action: str, claimed: DecisionWitness,
                   receipt: ClosedReceipt) -> None:
    if type(claimed) is not DecisionWitness or type(receipt) is not ClosedReceipt:
        raise AdmissionError('untyped or missing witness')
    expected, true_receipt = witnessed_decision(record, action)
    if claimed != expected or receipt != true_receipt:
        raise AdmissionError('unverifiable source action, receipt or replay')


def paid_control(record: DemandEpisode, action: str,
                 plan: ChargePlan = ChargePlan()) -> dict:
    """Charge a SEPARATE typed research route for both emitted and silent choices.

    Registers the chosen action BEFORE C demand/closure. A loss means no reward.
    Unknown C demand is an explicit abstention, never false/negative evidence.
    PE and memory are additional *modeled* shadow charges, not native PE grants.
    """
    if type(plan) is not ChargePlan:
        raise AdmissionError('untyped paid-control plan')
    witness, receipt = witnessed_decision(record, action)
    used_pe = used_mem = used_link = 0
    trace = []
    fail = False
    for stage, offset, mem in zip(STAGES, STAGE_OFFSET, MEM_CHARGE):
        # A missing decision or registration route cannot authorize an assessor.
        # A dropped return path cannot authorize consumption at A.
        if fail:
            break
        if (plan.pe_per_tick < 1 or (stage in TRANSIT and plan.link_per_tick < 1)
                or used_pe+1 > plan.pe_units or used_mem+mem > plan.memory_units
                or used_link+int(stage in TRANSIT) > plan.link_units):
            raise AdmissionError('no free shadow PE/memory/link admission')
        used_pe += 1
        used_mem += mem
        used_link += int(stage in TRANSIT)
        tick = witness.start_tick+offset
        row = {'stage':stage, 'tick':tick, 'PE':1, 'memory':mem,
               'link':int(stage in TRANSIT), 'delivered':stage!=plan.lost_stage}
        trace.append(row)
        if stage == plan.lost_stage:
            fail = True
    if fail:
        status, verdict, reward = 'transport_loss', None, None
    elif receipt.c_demand is None:
        status, verdict, reward = 'abstain_delivered', 'abstain', None
    else:
        status, verdict, reward = 'reward_delivered', receipt.verdict, receipt.local_reward
    if status == 'reward_delivered' and reward not in (-1,1):
        raise AssertionError('invalid source-observed task reward')
    if status == 'abstain_delivered' and receipt.verdict != 'abstain':
        raise AssertionError('abstention cannot be promoted')
    if status == 'reward_delivered' and trace[-1]['stage'] != 'A_consume':
        raise AssertionError('reward without consuming it')
    return {
        'schema':SCHEMA, 'episode_id':witness.episode_id, 'action':action,
        'decision_token':witness.token, 'shadow_origin':witness.origin,
        'A_spike':witness.has_A_spike, 'C_forward_ticks':list(witness.observed_C_forward_ticks),
        'C_closure_tick':witness.c_closure_tick,
        'decision_prefix_sha256':witness.prefix_digest,
        'C_observed_demand_if_delivered':receipt.c_demand if not fail else None,
        'status':status, 'verdict':verdict, 'reward':reward,
        'delivered_control':None if fail else {'decision_token':witness.token,
            'verdict':verdict, 'reward':reward, 'C_observed_demand':receipt.c_demand},
        'trace':trace, 'charged':{'PE':used_pe,'memory':used_mem,'link':used_link},
        'frozen_native_feedback_modified':False, 'native_learning':False,
    }


def verify_paid_control(record: DemandEpisode, action: str,
                        plan: ChargePlan, report: dict) -> None:
    """Independent deterministic source replay: recomputing the hash is insufficient."""
    if type(report) is not dict or report != paid_control(record,action,plan):
        raise AdmissionError('paid route/source forgery or noncanonical result')


class EpisodeLedger:
    """One selected trial per episode. Only verified delivered rewards enter credit.

    Uses an in-memory research ledger; NOT durable escrow or independent identity.
    """
    def __init__(self):
        self.episodes = set()
        self.tokens = set()
        self.reward_sum = Counter()
        self.rewards_received = Counter()
        self.abstentions = 0
        self.transport_losses = 0
        self.cost = Counter()

    def record(self, record: DemandEpisode, action: str, plan: ChargePlan, report: dict):
        if type(report) is not dict:
            raise AdmissionError('untyped custody report')
        if record.episode.identity in self.episodes or report.get('decision_token') in self.tokens:
            raise AdmissionError('episode or decision replay')
        verify_paid_control(record,action,plan,report)
        if report['status'] not in ('reward_delivered','abstain_delivered','transport_loss'):
            raise AdmissionError('invalid disposition')
        self.episodes.add(record.episode.identity)
        self.tokens.add(report['decision_token'])
        for k,v in report['charged'].items():
            self.cost[k] += v
        if report['status']=='reward_delivered':
            self.reward_sum[action] += report['reward']
            self.rewards_received[action] += 1
        elif report['status']=='abstain_delivered':
            self.abstentions += 1
        else:
            self.transport_losses += 1


def run_t2f() -> dict:
    """Finite matrix: same source-run cases, distinct reward transport and no learning."""
    source = generate_corpus(blocks=3,seed=37217,regime='aligned',train=False)
    corpus = tuple(replace(r,demand=(False,True,None)[i//7]) for i,r in enumerate(source))
    arms = ('overemit','silent','temporal')
    scenarios = {
        'paid':ChargePlan(),
        'lost_forward':ChargePlan(lost_stage='B_to_C'),
        'lost_reverse':ChargePlan(lost_stage='B_to_A'),
    }
    totals = {}
    evidence = []
    for name,plan in scenarios.items():
        ledger = EpisodeLedger()
        statuses = Counter()
        for idx,record in enumerate(corpus):
            action = arms[idx%len(arms)]
            # Independent single-arm episodes, no counterfactual actions for learning.
            report = paid_control(record,action,plan)
            ledger.record(record,action,plan,report)
            statuses[report['status']] += 1
            evidence.append({'scenario':name,'episode':record.episode.identity,
                             'demand_visible_only_to_C':record.demand,
                             'action':action,'result':report})
        totals[name] = {
            'episodes':len(corpus),'status_counts':dict(sorted(statuses.items())),
            'cost':dict(sorted(ledger.cost.items())),
            'rewards_received':dict(sorted(ledger.rewards_received.items())),
            'reward_sum':dict(sorted(ledger.reward_sum.items())),
            'negative_rewards':sum(int(x['result']['reward']==-1) for x in evidence if x['scenario']==name),
            'silent_rewards':sum(int(x['action']=='silent' and x['result']['reward'] in (-1,1)) for x in evidence if x['scenario']==name),
        }
    return {
        'schema':SCHEMA,'status':'T2F_SHADOW_DECISION_REWARD_ROUTE_MODELED_NOT_NATIVE_OR_BLIND',
        'source':'A1b executed unchanged; explicit shadow decision token sourced from actual selected candidate',
        'scope':'3 A/B/C nodes, 7 templates x 3 synthetic demand states x one assigned action, each of 3 route scenarios',
        'per_scenario':totals,'evidence_sha256':digest(evidence),
        'source_event_count':len(corpus)*len(scenarios),
        'forward_decision_control_is_native':False,
        'reverse_semantic_feedback_is_native':False,
        'costs_are_source_v0e_grants':False,
        'costs_are_shadow_modeled_and_explicit':True,
        'task_truth_is_independent':False,
        'native_learner_updates':0,
        'limitations':[
            'A silent decision exists ONLY as a host-minted source-replayed shadow witness, NOT as a native spike or operator',
            'Shadow PE/memory/link costs are explicit modeled additional units, NOT v0e-arbitrated source scheduler grants',
            'No automatic access to task oracle: C reads only the sensor from the synthetic environment; all_true/false independent truth unproven',
            'A receipt missing due to transport loss, closure failure or unknown C demand cannot count as negative credit',
            'All candidate registration and route tokens have research-host provenance, no independent cryptographic issuer',
            'No native state mutation, topology revision, hardware evidence, energy measurement or RL blind promotion',
        ],
    }
