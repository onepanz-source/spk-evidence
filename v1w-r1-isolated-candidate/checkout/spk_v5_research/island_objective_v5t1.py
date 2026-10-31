"""V5-T1/T2 bounded island objective, source-actual A1b execution.

Research-only logical island. The B output is a proxy for local processed-spike
feedback, NOT a truth/reward oracle and NOT the frozen Back Validation credit.
No native program is ever modified: every candidate is a fresh case.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json

from search.spk_24n_independent_oracle_v0 import CaseV0, EdgeV0, EventV0, NodeV0
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.pe_fabric_v1a import plan_v1a

SCHEMA = 'spk-v5-island-objective-t1t2/research-v0'
CHANNELS = {'C0': 0, 'C1': 1, 'P': 2}
CANDIDATES = ('overemit', 'silent', 'temporal')
RELAY = (('ACC', (1, 0)), ('CMP', 1), ('EMIT', 7), ('RESET', 0))
# Start of episode A: SHIFT before channel additions is essential.
TEMPORAL = (('SHIFT', 1), ('ACC', (2, 0)), ('ACC', (4, 2)),
            ('CMP', 5), ('EMIT', 7), ('CMP', 4), ('RESET', 0))
OVEREMIT = (('ACC', (1, 2)), ('CMP', 1), ('EMIT', 7), ('RESET', 0))
SILENT = (('CMP', 255), ('EMIT', 7))
PROGRAMS = {'overemit': OVEREMIT, 'silent': SILENT, 'temporal': TEMPORAL}


@dataclass(frozen=True)
class Episode:
    identity: str
    inputs: tuple[tuple[int, int], ...]  # (tick, channel), never a task label

    def __post_init__(self):
        if not self.identity or not self.inputs:
            raise ValueError('identity and bounded inputs required')
        if (len(self.inputs) > 2 or any(type(t) is not int or type(c) is not int
            or t < 0 or c not in CHANNELS.values() for t, c in self.inputs)
            or list(self.inputs) != sorted(self.inputs)
            or len({t for t, _ in self.inputs}) != len(self.inputs)):
            raise ValueError('invalid independent-episode event sequence')


def task_label(episode: Episode) -> int:
    """Externally declared TASK, deliberately not visible to select_by_feedback."""
    return int(len(episode.inputs) == 2
               and episode.inputs[0][1] == CHANNELS['C0']
               and episode.inputs[1][1] == CHANNELS['P']
               and episode.inputs[1][0] - episode.inputs[0][0] == 1)


def make_case(episode: Episode, program: str) -> CaseV0:
    if program not in PROGRAMS:
        raise ValueError('candidate outside frozen research list')
    nodes = tuple(NodeV0(name, 8, 0, 0, instructions)
                  for name, instructions in zip('ABC', (PROGRAMS[program], RELAY, RELAY)))
    edges = (EdgeV0('A', 7, 'B', 0, 1), EdgeV0('B', 7, 'C', 0, 1))
    events = tuple(EventV0(t, 'A', ch) for t, ch in episode.inputs)
    return CaseV0(nodes, edges, events)


def execute_episode(episode: Episode, program: str, scheme: str = 'spread') -> dict:
    """Use the unchanged A1b PE executor, not a handwritten replica."""
    case = make_case(episode, program)
    result = execute_on_pes_v1b(case, plan_v1a(case, scheme))['result']
    a = [e for e in result['emissions'] if e['node_id'] == 'A']
    b = [e for e in result['emissions'] if e['node_id'] == 'B']
    terminal = [e for e in result['terminal_outputs'] if e['node_id'] == 'C']
    if len(a) != len(b) or len(b) != len(terminal):
        raise AssertionError('causal relay conservation violated')
    if any(eb['timestamp'] != ea['timestamp'] + 1 for ea, eb in zip(a, b)):
        raise AssertionError('A-to-B causal delay violated')
    if any(ec['timestamp'] != eb['timestamp'] + 1 for eb, ec in zip(b, terminal)):
        raise AssertionError('B-to-C causal delay violated')
    return {'output': int(bool(terminal)), 'local_ack': len(b),
            'emitted_A': len(a), 'terminal_ticks': [e['timestamp'] for e in terminal],
            'processed_batches': result['processed_batches'],
            'processed_events': result['processed_events']}


def episodes(shift: int, gaps: tuple[int, ...]) -> tuple[Episode, ...]:
    """Finite factorial input-only corpus, separate episode state every time."""
    if type(shift) is not int or shift < 0 or not gaps or any(type(g) is not int or g < 1 for g in gaps):
        raise ValueError('invalid episode corpus bounds')
    if len(set(gaps)) != len(gaps):
        raise ValueError('duplicate gaps')
    ret = []
    for gap in gaps:
        for first in CHANNELS.values():
            for second in CHANNELS.values():
                ret.append(Episode(f'g{gap}-{first}-{second}',
                                   ((shift, first), (shift + gap, second))))
    for ch in CHANNELS.values():
        ret.append(Episode(f'single-{ch}', ((shift, ch),)))
    return tuple(ret)


def select_by_feedback(feedback: dict[str, tuple[int, ...]]) -> str:
    """Decision sees local ACK counts ONLY; no episode IDs, task labels or loss.

    Ties are preregistered to overemit (frozen baseline). This is a diagnostic
    of identifiability rather than a complete RL algorithm.
    """
    if set(feedback) != set(CANDIDATES) or not all(
            type(v) is tuple and v and all(type(x) is int and x >= 0 for x in v)
            for v in feedback.values()):
        raise ValueError('invalid bounded local feedback')
    return max(CANDIDATES, key=lambda name: (sum(feedback[name]), -CANDIDATES.index(name)))


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True).encode()).hexdigest()


def run_pilot() -> dict:
    # Preregistered fixed train/evaluation domains; evaluation labels never enter
    # feedback-based selection. These synthetic evaluations are NOT blind data.
    train = episodes(shift=0, gaps=(1, 2))
    evaluation = episodes(shift=5, gaps=(1, 2, 3))
    evidence = {}
    positives = sum(task_label(ep) for ep in evaluation)
    negatives = len(evaluation) - positives
    if not positives or not negatives:
        raise AssertionError('evaluation lacks a task class')
    for program in CANDIDATES:
        tr = [execute_episode(ep, program) for ep in train]
        ev = [execute_episode(ep, program) for ep in evaluation]
        labels = [task_label(ep) for ep in evaluation]
        fp = sum(int(x['output'] == 1 and y == 0) for x, y in zip(ev, labels))
        fn = sum(int(x['output'] == 0 and y == 1) for x, y in zip(ev, labels))
        evidence[program] = {
            'train_local_ack': [x['local_ack'] for x in tr],
            'holdout_loss': sum(int(x['output'] != y) for x, y in zip(ev, labels)),
            'holdout_false_positive': fp,
            'holdout_false_negative': fn,
            'holdout_balanced_error': (fp / negatives + fn / positives) / 2,
            'holdout_outputs': [x['output'] for x in ev],
        }
    local = {key: tuple(evidence[key]['train_local_ack']) for key in CANDIDATES}
    actual = select_by_feedback(local)
    # Placebo preserves each candidate's number/cost of ACKs; shuffles the
    # temporal association only. All ACKs are positive, so this test isolates
    # the missing semantics rather than pretending to provide negative rewards.
    placebo = select_by_feedback({k: tuple(reversed(v)) for k, v in local.items()})
    target = [task_label(ep) for ep in evaluation]
    if sum(target) == 0:
        raise AssertionError('no positive task outcomes')
    wrong_acks = sum(execute_episode(ep, 'overemit')['local_ack']
                     for ep in train if task_label(ep) == 0)
    return {
        'schema': SCHEMA,
        'status': 'V5_T1_CAPABILITY_PASS_T2_ACK_IDENTIFIABILITY_FAIL_T3_NO_GO',
        'architecture_modified': False, 'native_learning': False,
        'native_backvalidation_reward_proven': False,
        'task_definition': 'C0 then P exactly one tick apart; independent from B ACK',
        'train_episode_count': len(train),
        'evaluation_episode_count': len(evaluation),
        'evaluation_target_positives': sum(target),
        'evaluation_target_negatives': len(target)-sum(target),
        'class_imbalance_warning': 'one positive of thirty; no statistical or blind claim',
        'original_frozen_baseline': 'overemit',
        'local_feedback_selected': actual,
        'matched_placebo_selected': placebo,
        'pilot_local_feedback_loss': evidence[actual]['holdout_loss'],
        'pilot_placebo_loss': evidence[placebo]['holdout_loss'],
        'frozen_baseline_loss': evidence['overemit']['holdout_loss'],
        'supervised_oracle_upper_bound_loss_NOT_LEARNED': evidence['temporal']['holdout_loss'],
        'false_positive_local_ACKs_train': wrong_acks,
        'candidates': evidence,
        'holdout_input_digest': digest([e.__dict__ for e in evaluation]),
        'holdout_target_digest': digest(target),
        'limits': [
            'No semantic causal reward established by B output',
            'No real RL policy/credit update, only diagnostic candidate selection',
            'Synthetic holdout not independent external task truth',
            'No native BV scheduling, paid ACK/consumer or learning implementation in this pilot',
            'No modification to Core Network Compiler Architecture or frozen scheduler',
        ],
    }
