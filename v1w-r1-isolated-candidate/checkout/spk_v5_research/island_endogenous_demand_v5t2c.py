"""SPK V5-T2c: observed downstream demand, closed episodes and one-arm bandit.

The exogenous C demand is drawn by a *simulated* environment independently of
which A program is chosen. This is a constructed sensor-grounded task, NOT a
real-world independently verified task oracle. One A1b run observes ONE chosen
arm; C actually processes demand/no-demand and a separate closure pulse.

Reverse feedback, policy selection and credit remain in an isolated research
observer. No frozen SPK contracts, PE state or native learner are modified.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from random import Random

from search.spk_24n_independent_oracle_v0 import CaseV0, EdgeV0, EventV0, NodeV0
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_v5_research.island_objective_v5t1 import (
    CANDIDATES, PROGRAMS, RELAY, Episode, digest,
)

SCHEMA = 'spk-v5-t2c-exogenous-demand-closed-bandit/research-v0'
REGIMES = ('aligned', 'inverted', 'decoupled', 'absent')
# At C, separately process: forwarded spike / actual demand / no demand / closure.
# RESET is conditional on the immediately preceding CMP. Different pulses are
# not allowed to masquerade as other output channels.
C_PROGRAM = tuple(ins for in_ch, out_ch in ((2, 7), (4, 8), (5, 10), (6, 9))
                  for ins in (('ACC', (1, in_ch)), ('CMP', 1),
                              ('EMIT', out_ch), ('RESET', 0)))
TEMPLATES = (
    ((0, 0), (1, 2)),  # A source input pattern associated with higher demand
    ((0, 1), (1, 2)),
    ((0, 2), (1, 2)),
    ((0, 0), (2, 2)),
    ((0, 2),),
    ((0, 2), (1, 0)),
    ((0, 0), (1, 0)),
)


@dataclass(frozen=True)
class DemandEpisode:
    episode: Episode
    demand: bool | None  # environment's independent-of-A-choice exogenous bit
    template_id: int


@dataclass(frozen=True)
class ClosedReceipt:
    episode_id: str
    candidate: str
    closure_tick: int
    c_forward_ticks: tuple[int, ...]
    c_sensor_tick: int | None
    c_demand: bool | None
    verdict: str  # positive, negative, abstain
    local_reward: int | None


def generate_corpus(*, blocks: int, seed: int, regime: str, train: bool) -> tuple[DemandEpisode, ...]:
    """Independent deterministic world RNG, with candidate-agnostic outcomes.

    'aligned'/'inverted' are openly ENGINEERED conditional distributions; this
    is not empirical causality and not a blind third-party dataset.
    """
    if (type(blocks) is not int or not 1 <= blocks <= 200 or
            type(seed) is not int or seed < 0 or regime not in REGIMES or
            type(train) is not bool):
        raise ValueError('invalid world generation parameters')
    random = Random(seed)
    result = []
    for block in range(blocks):
        for template_id, template in enumerate(TEMPLATES):
            for repetition in range(3 if train else 1):
                # The correlation is an explicit world assumption, not a reward
                # read from task_label() and not access to the chosen candidate.
                p = ({'aligned':(.86 if template_id == 0 else .12),
                      'inverted':(.14 if template_id == 0 else .88),
                      'decoupled':.5, 'absent':.5}[regime])
                demand = None if regime == 'absent' else random.random() < p
                start = 10 * (block * len(TEMPLATES) + template_id) + repetition
                events = tuple((start + t, channel) for t,channel in template)
                eid = f'{"tr" if train else "ev"}-{block}-{template_id}-{repetition}'
                result.append(DemandEpisode(Episode(eid, events), demand, template_id))
    return tuple(result)


def make_case(record: DemandEpisode, candidate: str) -> CaseV0:
    if type(record) is not DemandEpisode or candidate not in CANDIDATES:
        raise ValueError('unadmitted environment episode/program')
    ep = record.episode
    start = ep.inputs[0][0]
    nodes = tuple(NodeV0(n, 8, 0, 0, ins)
                  for n,ins in zip('ABC', (PROGRAMS[candidate], RELAY, C_PROGRAM)))
    edges = (EdgeV0('A', 7, 'B', 0, 1), EdgeV0('B', 7, 'C', 2, 1))
    external = [EventV0(t, 'A', ch) for t,ch in ep.inputs]
    if record.demand is not None:
        if type(record.demand) is not bool:
            raise ValueError('untyped environment outcome')
        external.append(EventV0(start + 5, 'C', 4 if record.demand else 5))
    external.append(EventV0(start + 6, 'C', 6))
    return CaseV0(nodes, edges, tuple(external))


def observe_closed_episode(record: DemandEpisode, candidate: str,
                           *, scheme: str = 'spread') -> ClosedReceipt:
    """One physically executed A1b candidate; evidence ONLY from C batches.

    No access to task_label, no lookup of a candidate's counterfactual reward.
    Silence can be assessed ONLY after explicit closure and an observed demand
    state. Transport timeout or a missing demand sensor means abstain.
    """
    case = make_case(record, candidate)
    result = execute_on_pes_v1b(case, plan_v1a(case, scheme))['result']
    emissions = result['emissions']
    c_batches = sorted((b for b in result['observations']['batches'] if b['node_id'] == 'C'),
                       key=lambda b:b['timestamp'])
    forward = [b for b in c_batches if b['channels'] == [2]]
    clocks = [b for b in c_batches if b['channels'] == [6]]
    demand_on = [b for b in c_batches if b['channels'] == [4]]
    demand_off = [b for b in c_batches if b['channels'] == [5]]
    if len(clocks) != 1 or clocks[0]['output_channels'] != [9]:
        raise AssertionError('C closure not independently processed')
    start = record.episode.inputs[0][0]
    if clocks[0]['timestamp'] != start + 6:
        raise AssertionError('C closure tick mismatch')
    if (any(b['output_channels'] != [7] or b['timestamp'] >= start + 5 for b in forward)
            or any(b['output_channels'] != [8] or b['timestamp'] != start+5 for b in demand_on)
            or any(b['output_channels'] != [10] or b['timestamp'] != start+5 for b in demand_off)
            or len(demand_on) + len(demand_off) > 1):
        raise AssertionError('source-engine C pulse custody mismatch')
    a = [e['timestamp'] for e in emissions if e['node_id'] == 'A' and e['channel'] == 7]
    b = [e['timestamp'] for e in emissions if e['node_id'] == 'B' and e['channel'] == 7]
    c = [item['timestamp'] for item in forward]
    if (len(a) != len(b) or len(b) != len(c)
            or any(y != x+1 for x,y in zip(a,b))
            or any(z != y+1 for y,z in zip(b,c))):
        raise AssertionError('A-B-C propagation is not causal')
    if sum(e['node_id'] == 'C' and e['channel'] == 9 for e in emissions) != 1:
        raise AssertionError('C closure emission not observed')
    sensor = True if demand_on else False if demand_off else None
    if sensor is None:
        verdict, reward = 'abstain', None
    else:
        match = bool(forward) == sensor
        verdict, reward = ('positive', 1) if match else ('negative', -1)
    return ClosedReceipt(record.episode.identity, candidate, start + 6,
                         tuple(c), start + 5 if sensor is not None else None,
                         sensor, verdict, reward)


def verify_closed_receipt(record: DemandEpisode, candidate: str,
                          receipt: ClosedReceipt, scheme: str = 'spread') -> None:
    if type(receipt) is not ClosedReceipt or receipt != observe_closed_episode(record,candidate,scheme=scheme):
        raise ValueError('unattributable, forged or replayed local C closure')
    if (receipt.local_reward,receipt.verdict) not in ((1,'positive'),(-1,'negative'),(None,'abstain')):
        raise ValueError('invalid reward contract')


def arm_plan(corpus: tuple[DemandEpisode, ...], *, seed: int) -> tuple[str, ...]:
    """Balanced randomized exploration: one chosen arm per episode, no replay.

    Every source pattern appears once for each candidate per training block;
    experimental action does not depend on C's unseen future demand bit.
    """
    if type(seed) is not int or seed < 0 or len(corpus) % (3*len(TEMPLATES)):
        raise ValueError('invalid balanced bandit horizon')
    random = Random(seed)
    plan = []
    for index in range(0,len(corpus),3):
        if tuple(x.template_id for x in corpus[index:index+3]) != (corpus[index].template_id,)*3:
            raise ValueError('unbalanced input stratum')
        actions = list(CANDIDATES)
        random.shuffle(actions)
        plan.extend(actions)
    return tuple(plan)


def learn_single_arm(corpus: tuple[DemandEpisode, ...], plan: tuple[str,...]) -> dict:
    """Explore-then-commit bandit shadow estimator, NOT native RL.

    A real C sensor result is observed only under chosen action. A silent
    action receives a reward only if the independent demand and closure were
    processed. Unknown signals never silently become losses.
    """
    if len(corpus) != len(plan) or not corpus:
        raise ValueError('mismatched action/evidence horizon')
    totals = Counter({c:0 for c in CANDIDATES})
    counts = Counter({c:0 for c in CANDIDATES})
    abstentions = Counter({c:0 for c in CANDIDATES})
    forward = Counter({c:0 for c in CANDIDATES})
    for record, candidate in zip(corpus,plan):
        if candidate not in CANDIDATES:
            raise ValueError('invalid candidate action')
        receipt = observe_closed_episode(record,candidate)
        forward[candidate] += len(receipt.c_forward_ticks)
        if receipt.local_reward is None:
            abstentions[candidate] += 1
        else:
            counts[candidate] += 1
            totals[candidate] += receipt.local_reward
    # Without information, no unearned program upgrade; retain baseline.
    winner = ('overemit' if not all(counts.values())
              else max(CANDIDATES,key=lambda c:(totals[c]/counts[c],-CANDIDATES.index(c))))
    return {
        'choice':winner,
        'reward_sums':dict(totals),
        'observed_rewards':dict(counts),
        'abstentions':dict(abstentions),
        'forward_spike_counts':dict(forward),
        'chosen_actions':dict(Counter(plan)),
        'policy_changes_native':0,
    }


def evaluate_candidate(corpus: tuple[DemandEpisode, ...], candidate: str) -> dict:
    if candidate not in CANDIDATES:
        raise ValueError('unadmitted candidate')
    fp = fn = correct = forward = missing = 0
    for record in corpus:
        receipt = observe_closed_episode(record, candidate)
        if receipt.c_demand is None:
            missing += 1
            continue
        observed = bool(receipt.c_forward_ticks)
        correct += observed == receipt.c_demand
        fp += observed and not receipt.c_demand
        fn += not observed and receipt.c_demand
        forward += len(receipt.c_forward_ticks)
    return {'correct':correct,'error':fp+fn,'false_positive':fp,
            'false_negative':fn, 'forward_spikes':forward,
            'missing_sensor':missing}


def run_t2c() -> dict:
    regimes = {}
    for mode in REGIMES:
        train = generate_corpus(blocks=24,seed=37217,regime=mode,train=True)
        evaluation = generate_corpus(blocks=10,seed=91871,regime=mode,train=False)
        actions = arm_plan(train,seed=4482)
        learned = learn_single_arm(train,actions)
        # Matched randomization: preserve the full multiset of true/false/unknown
        # C sensor pulses and the exact A action schedule. Break ONLY their
        # association with the input episodes. Still a synthetic control.
        placebo_choices = []
        for seed in range(32):
            assigned = [x.demand for x in train]
            Random(9801+seed).shuffle(assigned)
            assert Counter(assigned) == Counter(x.demand for x in train)
            randomized = tuple(replace(x,demand=d) for x,d in zip(train,assigned))
            placebo_choices.append(learn_single_arm(randomized,actions)['choice'])
        # Counterfactual labels are not fed to the learner; evaluator can replay
        # each candidate only AFTER selection, purely to audit the benchmark.
        benchmark = {c:evaluate_candidate(evaluation,c) for c in CANDIDATES}
        regimes[mode] = {
            'train_episodes':len(train), 'evaluation_episodes':len(evaluation),
            'train_exogenous_demand_present':sum(x.demand is True for x in train),
            'train_exogenous_demand_absent':sum(x.demand is False for x in train),
            'train_unknown_demand':sum(x.demand is None for x in train),
            'train_inputs_sha256':digest([x.episode.__dict__ for x in train]),
            'evaluation_environment_sha256':digest([(x.episode.__dict__,x.demand) for x in evaluation]),
            'actions_sha256':digest(actions),
            'learner':learned,
            'matched_demand_shuffle_placebo_choices':dict(sorted(Counter(placebo_choices).items())),
            'matched_demand_shuffle_placebo_losses':dict(sorted((str(k),v) for k,v in Counter(benchmark[c]['error'] for c in placebo_choices).items())),
            'evaluation':benchmark,
            'selected_evaluation':benchmark[learned['choice']],
        }
    aligned = regimes['aligned']
    absent = regimes['absent']
    return {
        'schema':SCHEMA,
        'status':'T2C_SIMULATED_EXOGENOUS_DEMAND_SHADOW_BANDIT_CONTROL_ONLY_T3_BLIND_BLOCKED',
        'world_construction':'Exogenous C demand drawn BEFORE candidate selection; correlation with A inputs specified synthetically by experimenter',
        'native_engine':'A1b real three-neuron PE execution, no source changes',
        'runtime_reverse_BV_delivery':False,
        'native_learning':False,
        'island_objective':'Match actual independently scheduled C demand at episode closure; one binary response per episode',
        'missing_response_semantics':'C closure + valid demand sensor necessary to penalize silence; missing sensor always abstains',
        'regimes':regimes,
        'limitations':[
            'Synthetic world demand correlation is engineered, not demonstrated or independently sourced physical task truth',
            'C demand pulse and closure arrive through A1b input fixtures; no production sensor identities or authenticated custody',
            'Reverse C outcome is collected by shadow observer, not routed over frozen BV v0e',
            'Explore-then-commit single-arm bandit is research policy selection, not online native program self-modification',
            'Evaluation fixture seeds are public; not blind or preregistered statistical validation',
            'PE transport in A1b is ideal, and bandit feedback processing does not charge BV PE/S memory/link costs',
            'No source identity weights, firmware/hardware claims, island deployment or native learner',
        ],
    }
