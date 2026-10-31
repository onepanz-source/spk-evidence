"""V5-T2d. Two distinct ledgers: action-visible C sensor and audit-only world bit.

Real unmodified A1b execution, single selected arm per train episode, C closure.
Independent seeded *synthetic* sensor faults are NOT external truth or a blind set.
No native reverse BV traffic, cost accounting, policy adoption, or frozen edits.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from random import Random

from spk_v5_research.island_objective_v5t1 import CANDIDATES, digest
from spk_v5_research.island_endogenous_demand_v5t2c import (
    DemandEpisode, arm_plan, evaluate_candidate, generate_corpus,
    learn_single_arm, observe_closed_episode,
)

SCHEMA = 'spk-v5-t2d-island-sensor-observation-robustness/research-v0'


@dataclass(frozen=True)
class SensorFault:
    name: str
    flip_probability: float
    drop_if_true: float
    drop_if_false: float

    def __post_init__(self):
        if (type(self.name) is not str or not self.name or
                any(type(x) is not float or not 0.0 <= x <= 1.0
                    for x in (self.flip_probability, self.drop_if_true,
                              self.drop_if_false))):
            raise ValueError('invalid bounded sensor fault configuration')


FAULTS = (
    SensorFault('clean', 0.0, 0.0, 0.0),
    SensorFault('flip_10pct', .10, 0.0, 0.0),
    SensorFault('flip_35pct', .35, 0.0, 0.0),
    SensorFault('fully_inverted', 1.0, 0.0, 0.0),
    SensorFault('missing_at_random_30pct', 0.0, .30, .30),
    SensorFault('selective_missing_true_90pct', 0.0, .90, .05),
    SensorFault('all_missing', 0.0, 1.0, 1.0),
)


@dataclass(frozen=True)
class ObservationSplit:
    # The learner receives only `sensor`, never `world_truth`.
    sensor: tuple[DemandEpisode, ...]
    world_truth: tuple[tuple[str, bool], ...]
    world_sha256: str
    source_inputs_sha256: str
    fault: SensorFault


def corrupt_observation(world: tuple[DemandEpisode, ...], fault: SensorFault,
                        *, seed: int) -> ObservationSplit:
    """Pre-action, independently seeded corruption of C observation only.

    The original world bit is an AUDITOR input and never passed to the learner.
    Fault draws are stratified by true demand and NOT action-conditional.
    We do not treat missing C sensor as 'false' or missing closure as a negative.
    """
    if (type(world) is not tuple or not world or type(fault) is not SensorFault or
            type(seed) is not int or seed < 0 or
            any(type(r) is not DemandEpisode or type(r.demand) is not bool for r in world)):
        raise ValueError('fault injection requires typed, complete world')
    ids = [r.episode.identity for r in world]
    if len(set(ids)) != len(ids):
        raise ValueError('ambiguous duplicated world episode identifiers')
    random = Random(seed)
    sensor = []
    truth = []
    for r in world:
        truth.append((r.episode.identity, r.demand))
        missing = random.random() < (fault.drop_if_true if r.demand else fault.drop_if_false)
        flipped = random.random() < fault.flip_probability
        observed = None if missing else bool(r.demand ^ flipped)
        sensor.append(replace(r, demand=observed))
    return ObservationSplit(tuple(sensor), tuple(truth), digest(truth),
                            digest([(r.episode.identity,r.episode.inputs,r.template_id) for r in world]), fault)


def audit_observation(split: ObservationSplit) -> dict:
    """Audit only; statistics computed with sealed synthetic world bits.

    None of these data may be used by the learner, policy search or arm choice.
    """
    if type(split) is not ObservationSplit or type(split.fault) is not SensorFault:
        raise ValueError('invalid observation split')
    if (len(split.sensor) != len(split.world_truth) or
            digest(split.world_truth) != split.world_sha256 or
            digest([(r.episode.identity,r.episode.inputs,r.template_id) for r in split.sensor]) != split.source_inputs_sha256):
        raise ValueError('world custody drift')
    counts = Counter()
    for observed, (eid, actual) in zip(split.sensor, split.world_truth):
        if (observed.episode.identity != eid or type(actual) is not bool or
                observed.demand is not None and type(observed.demand) is not bool):
            raise ValueError('sensor/world identity or typing mismatch')
        counts['world_true' if actual else 'world_false'] += 1
        if observed.demand is None:
            counts['unknown'] += 1
            counts['unknown_world_true' if actual else 'unknown_world_false'] += 1
        else:
            counts['observed'] += 1
            counts['observed_true' if observed.demand else 'observed_false'] += 1
            if observed.demand != actual:
                counts['wrong_sensor_bit'] += 1
    if counts['observed'] + counts['unknown'] != len(split.sensor):
        raise AssertionError('nonconserving sensor census')
    return {key:counts[key] for key in (
        'world_true','world_false','observed','unknown','observed_true',
        'observed_false','wrong_sensor_bit','unknown_world_true','unknown_world_false')}


def one_episode_feedback(sample: DemandEpisode, candidate: str):
    """Visible arm reward only from actual A1b C closure and observed C sensor."""
    return observe_closed_episode(sample, candidate)


def audit_truth_risk(corpus: tuple[DemandEpisode, ...], choice: str) -> dict:
    """Synthetic *audit-only* world evaluation. Never called inside learner."""
    if choice not in CANDIDATES or any(type(r.demand) is not bool for r in corpus):
        raise ValueError('truth audit needs complete world without unknown labels')
    return evaluate_candidate(corpus, choice)


def run_t2d() -> dict:
    train_world = generate_corpus(blocks=24,seed=37217,regime='aligned',train=True)
    eval_world = generate_corpus(blocks=10,seed=91871,regime='aligned',train=False)
    shifted_world = generate_corpus(blocks=10,seed=91871,regime='inverted',train=False)
    action_schedule = arm_plan(train_world,seed=4482)
    assert len(train_world)==504 and len(eval_world)==70
    audit_aligned = {c:audit_truth_risk(eval_world,c) for c in CANDIDATES}
    audit_shifted = {c:audit_truth_risk(shifted_world,c) for c in CANDIDATES}
    result = {}
    for index, fault in enumerate(FAULTS):
        split = corrupt_observation(train_world,fault,seed=87300+index)
        learner = learn_single_arm(split.sensor,action_schedule)
        census = audit_observation(split)
        if sum(learner['observed_rewards'].values()) != census['observed']:
            raise AssertionError('observation/reward ledger drift')
        if sum(learner['abstentions'].values()) != census['unknown']:
            raise AssertionError('missing sensor was silently reclassified')
        placebo = []
        for j in range(16):
            permuted = list(r.demand for r in split.sensor)
            Random(41100+j).shuffle(permuted)
            shuffled_sensor = tuple(replace(r,demand=bit) for r,bit in zip(split.sensor,permuted))
            if Counter(permuted) != Counter(r.demand for r in split.sensor):
                raise AssertionError('placebo changed observed histogram')
            placebo.append(learn_single_arm(shuffled_sensor,action_schedule)['choice'])
        result[fault.name] = {
            'fault':fault.__dict__, 'sensor_census':census,
            'sensor_observation_sha256':digest([(r.episode.identity,r.demand) for r in split.sensor]),
            'synthetic_audit_world_sha256':split.world_sha256,
            'learner':learner,
            'placebo_choices':dict(sorted(Counter(placebo).items())),
            'aligned_truth_error':audit_aligned[learner['choice']]['error'],
            'inverted_shift_truth_error':audit_shifted[learner['choice']]['error'],
            'truth_audit_only':True,
        }
    return {
        'schema':SCHEMA,
        'status':'T2D_SENSOR_FAULT_DIAGNOSTIC_RESEARCH_ONLY_NO_INDEPENDENT_TRUTH_OR_T3_BLIND',
        'engine':'frozen SPK A1b real PE executor, through V5-T2c observed C batch and closure',
        'native_learning':False, 'native_reverse_bv_delivery':False,
        'research_candidate_program_adoptions':0,
        'world':'T2c synthetically correlated demand (aligned), independently seeded observation corruption, action-independent',
        'train_episode_count':len(train_world),
        'evaluation_episode_count':len(eval_world),
        'action_schedule_sha256':digest(action_schedule),
        'truth_audit_aligned':audit_aligned,
        'truth_audit_inverted_shift':audit_shifted,
        'scenarios':result,
        'limits':[
            'Synthetic world bits are sealed from learner by API separation, not external cryptographic custody or independent task ground truth',
            'The sensor is simulated using pre-action RNG; no physical sensors or authenticated issuer',
            'Closure and observation use real frozen A1b; no native reverse BV actor credit, PE/S/link charging or online frozen learning',
            'Observed reward may be incorrect even when the C receipt is causally valid; missingness may be not at random',
            'Inverted evaluation is deliberate out-of-distribution stress, not a blind real-world dataset',
            'No assertion of statistical significance, real RL multistage, source weights, topology or hardware',
        ],
    }
