"""SPK V5-T2b: engineered downstream consequence as a LOCAL reward control.

A1b source executor remains frozen. C sees an exogenous first-context witness;
C always forwards A's candidate response on output channel 7, and emits local
channel 8 only if it also recognizes the witness in its own PE memory.
A->B->C is executed unchanged; a SHADOW observer turns actual C batch outcomes
into explicit, causally paired B judgments. There is no native reverse edge.

The C witness is DESIGNED to correlate with the island objective. It is not an
independent oracle and is never supplied to the policy selector as task truth.
All holdouts are synthetic and visible. No native reinforcement learning claim.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from random import Random

from search.spk_24n_independent_oracle_v0 import CaseV0, EdgeV0, EventV0, NodeV0
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_v5_research.island_objective_v5t1 import (
    CHANNELS, CANDIDATES, PROGRAMS, RELAY, Episode, digest, task_label,
)

SCHEMA = 'spk-v5-island-local-consequence-t2b/research-v0'
MODES = ('aligned', 'inverted', 'absent')
# With channel 0 witness, channel 2 actual B forwarded stimulus:
# 7 is the island's unguarded response, 8 is an *additional* local C indicator.
# NOTE the order: before RESET, both comparisons use the same accumulated state.
C_RECEIVER = (('SHIFT', 1), ('ACC', (2, 0)), ('ACC', (4, 2)),
              ('CMP', 4), ('EMIT', 7), ('CMP', 5), ('EMIT', 8),
              ('CMP', 4), ('RESET', 0))


@dataclass(frozen=True)
class Receipt:
    episode: str
    candidate: str
    emission_tick: int
    b_tick: int
    c_tick: int
    c_processed: bool
    c_confirmed: bool
    local_reward: int  # +1/-1/0; unavailable C witness forces abstention
    verdict: str


def case_with_witness(episode: Episode, candidate: str, mode: str) -> CaseV0:
    if candidate not in PROGRAMS or mode not in MODES:
        raise ValueError('unadmitted candidate or witness regime')
    nodes = tuple(NodeV0(n, 8, 0, 0, ins) for n, ins in
                  zip('ABC', (PROGRAMS[candidate], RELAY, C_RECEIVER)))
    edges = (EdgeV0('A', 7, 'B', 0, 1), EdgeV0('B', 7, 'C', 2, 1))
    external = [EventV0(t, 'A', ch) for t, ch in episode.inputs]
    # An additional sensor, independently delivered to C, observes ONLY the
    # first context. It cannot see A's candidate, decision, or the task label.
    # This is deliberately engineered redundant observation, NOT task truth.
    if mode != 'absent':
        first_t, first_ch = episode.inputs[0]
        witness_ch = CHANNELS['C0'] if mode == 'aligned' else CHANNELS['C1']
        if first_ch == witness_ch:
            external.append(EventV0(first_t + 2, 'C', 0))
    return CaseV0(nodes, edges, tuple(external))


def execute_consequence(episode: Episode, candidate: str, mode: str,
                        scheme: str = 'spread') -> dict:
    case = case_with_witness(episode, candidate, mode)
    r = execute_on_pes_v1b(case, plan_v1a(case, scheme))['result']
    emissions = r['emissions']
    a_ticks = [e['timestamp'] for e in emissions if e['node_id'] == 'A' and e['channel'] == 7]
    b_ticks = [e['timestamp'] for e in emissions if e['node_id'] == 'B' and e['channel'] == 7]
    terminals = [e['timestamp'] for e in emissions if e['node_id'] == 'C' and e['channel'] == 7]
    confirms = [e['timestamp'] for e in emissions if e['node_id'] == 'C' and e['channel'] == 8]
    c_batches = [b for b in r['observations']['batches'] if b['node_id'] == 'C'
                 and 2 in b['channels']]
    if len(a_ticks) != len(b_ticks) or len(b_ticks) != len(terminals) or len(c_batches) != len(a_ticks):
        raise AssertionError('C causal processed receipt conservation failed')
    if any(b != a + 1 or c != b + 1 for a,b,c in zip(a_ticks,b_ticks,terminals)):
        raise AssertionError('C causal two-hop times violated')
    if any(b['timestamp'] != c or b['channels'].count(2) != 1 or 7 not in b['output_channels']
           for b,c in zip(c_batches,terminals)):
        raise AssertionError('C receipt batch not explicitly observed')
    if confirms != [b['timestamp'] for b in c_batches if 8 in b['output_channels']]:
        raise AssertionError('C witness confirmation cannot be forged')
    receipts = tuple(Receipt(episode.identity, candidate, a,b,c, True,
                             8 in batch['output_channels'],
                             0 if mode == 'absent' else (1 if 8 in batch['output_channels'] else -1),
                             'abstain' if mode == 'absent' else
                             ('positive' if 8 in batch['output_channels'] else 'negative'))
                     for a,b,c,batch in zip(a_ticks,b_ticks,terminals,c_batches))
    return {'output': int(bool(terminals)), 'output_count': len(terminals),
            'local_ack': len(b_ticks), 'local_reward': sum(x.local_reward for x in receipts),
            'positive_receipts': sum(x.c_confirmed for x in receipts),
            'negative_receipts': sum(x.verdict == 'negative' for x in receipts),
            'abstained_receipts': sum(x.verdict == 'abstain' for x in receipts),
            'receipts': receipts, 'terminal_ticks': tuple(terminals),
            'confirmation_ticks': tuple(confirms), 'processed_batches': r['processed_batches']}



def verify_receipts(episode: Episode, candidate: str, mode: str,
                    presented: tuple[Receipt, ...], scheme: str = 'spread') -> None:
    """Same-engine recomputation against source A1b, not a signature or issuer.
    Reject missing/extra/replayed, reattributed, time-travel or forged verdicts.
    """
    if type(presented) is not tuple or not all(type(x) is Receipt for x in presented):
        raise ValueError('invalid typed receipt')
    expected = execute_consequence(episode, candidate, mode, scheme)['receipts']
    if presented != expected:
        raise ValueError('receipt chain differs from independently rerun C observation')
    if any(x.c_tick != x.emission_tick+2 or x.b_tick != x.emission_tick+1
           or x.c_processed is not True for x in presented):
        raise ValueError('unbounded or unprocessed C judgment')
    if any((x.local_reward, x.verdict) not in
           ((1,'positive'),(-1,'negative'),(0,'abstain')) for x in presented):
        raise ValueError('illegal sign or verdict')
    if mode == 'absent' and any(x.verdict != 'abstain' for x in presented):
        raise ValueError('sensor-unavailable may not produce signed semantic judgment')
    if len({(x.episode,x.candidate,x.emission_tick,x.c_tick) for x in presented}) != len(presented):
        raise ValueError('replayed emission credit')

def focused_corpus(starts: tuple[int, ...]) -> tuple[Episode, ...]:
    """Synthetic paired challenges; different starts are NOT independent subjects."""
    if not starts or any(type(t) is not int or t < 0 for t in starts) or len(set(starts)) != len(starts):
        raise ValueError('distinct nonnegative starts required')
    return tuple(Episode(f's{start}-{ix}',tuple((start + dt, ch) for dt,ch in sequence))
                 for start in starts for ix, sequence in enumerate((
                     ((0,0),(1,2)),  # true C0 -> P
                     ((0,1),(1,2)),  # wrong context
                     ((0,2),(1,2)),  # double P, two negative receipts
                     ((0,0),(2,2)),  # stale C0 -> P
                     ((0,2),),       # P only
                     ((0,2),(1,0)),  # reverse
                     ((0,0),(1,0)),  # C0, C0
                 )))


def select_shadow(scores: dict[str, tuple[int, ...]]) -> str:
    """Conservative finite program choice. Candidate-level training observations
    are fully replayed; this is an offline shadow proxy, NOT a bandit or RL.
    """
    if set(scores) != set(CANDIDATES) or not all(type(v) is tuple and v and
        all(type(x) is int and -2 <= x <= 2 for x in v) for v in scores.values()):
        raise ValueError('invalid explicit local credit')
    return max(CANDIDATES, key=lambda c: (sum(scores[c]), -CANDIDATES.index(c)))


def run_experiment() -> dict:
    train = focused_corpus((0,4,8,12,16,20,24,28))
    evaluation = focused_corpus((36,40,44,48,52,56))
    truths = tuple(task_label(e) for e in evaluation)  # ONLY evaluator uses labels
    assert sum(truths) == 6 and len(truths) == 42
    info = {}
    for mode in MODES:
        vectors = {}
        # preserve individual signed receipt for all matched placebo timings
        per_receipt = {}
        per_emission_index = []
        for candidate in CANDIDATES:
            executions = [execute_consequence(ep,candidate,mode) for ep in train]
            vectors[candidate] = tuple(x['local_reward'] for x in executions)
            per_receipt[candidate] = tuple(x['receipts'] for x in executions)
            per_emission_index.extend((candidate,i,j,r.local_reward)
                for i,x in enumerate(executions) for j,r in enumerate(x['receipts']))
        chosen = select_shadow(vectors)
        # Source-exact permutation, globally preserves all receipt sign counts.
        vals = [x[-1] for x in per_emission_index]
        placebo_selections = []
        for seed in range(32):
            shifted = list(vals)
            Random(seed+1701).shuffle(shifted)
            randomized = {c: [0]*len(train) for c in CANDIDATES}
            for (c,idx,_,_),value in zip(per_emission_index,shifted):
                randomized[c][idx] += value
            # Guard random permutation preserves count and sign histogram.
            assert Counter(shifted) == Counter(vals)
            placebo_selections.append(select_shadow({c: tuple(v) for c,v in randomized.items()}))
        info[mode] = {
            'shadow_choice':chosen,
            'placebo_choices':dict(sorted(Counter(placebo_selections).items())),
            'train_receipts_by_candidate':{c: sum(len(t) for t in per_receipt[c]) for c in CANDIDATES},
            'train_positive_by_candidate':{c:sum(r.local_reward == 1 for rows in per_receipt[c] for r in rows) for c in CANDIDATES},
            'train_negative_by_candidate':{c:sum(r.local_reward == -1 for rows in per_receipt[c] for r in rows) for c in CANDIDATES},
            'train_abstain_by_candidate':{c:sum(r.local_reward == 0 for rows in per_receipt[c] for r in rows) for c in CANDIDATES},
            'train_score_by_candidate':{c:sum(vectors[c]) for c in CANDIDATES},
        }
    objective = {}
    for candidate in CANDIDATES:
        records = [execute_consequence(ep,candidate,'aligned') for ep in evaluation]
        predictions = [r['output'] for r in records]
        fp = sum(p==1 and y==0 for p,y in zip(predictions,truths))
        fn = sum(p==0 and y==1 for p,y in zip(predictions,truths))
        objective[candidate] = {
            'loss':fp+fn, 'false_positive':fp, 'false_negative':fn,
            'balanced_error':(fp/36+fn/6)/2,
            'island_output_count':sum(r['output_count'] for r in records)}
    for mode, row in info.items():
        row['shadow_evaluation_loss'] = objective[row['shadow_choice']]['loss']
        row['placebo_evaluation_losses'] = {str(k):v for k,v in sorted(Counter(
            objective[c]['loss'] for c, count in row['placebo_choices'].items()
            for _ in range(count)).items())}
    return {
        'schema':SCHEMA,
        'status':'T2_ENGINEERED_CONSEQUENCE_INFORMATION_POSITIVE_CONTROL_ONLY_T3_BLIND_BLOCKED',
        'train_episodes':len(train), 'evaluation_episodes':len(evaluation),
        'evaluation_positives':sum(truths), 'evaluation_negatives':len(truths)-sum(truths),
        'train_input_sha256':digest([e.__dict__ for e in train]),
        'evaluation_input_sha256':digest([e.__dict__ for e in evaluation]),
        'candidate_objective_evaluation':objective,
        'frozen_baseline_loss':objective['overemit']['loss'],
        'regimes':info,
        'causal_scope':'C output-channel 8 witness is from same A1b execution; B judgment is SHADOW via explicit C batch',
        'engineered_witness_not_independent_task_oracle':True,
        'native_BV_credit_delivered':False,
        'native_learning':False,
        'frozen_sources_modified':False,
        'limitations':[
            'Engineered C witness is selected to align with this same known synthetic task',
            'No blind independent task labels, no statistical inference, temporal shifts are not independent subjects',
            'B receives C batch result only via offline shadow observer, not native reverse BV scheduling',
            'Negative judgments require explicit processed C batches and available C witness, never absence of an ACK',
            'Offline full-information candidate scoring is not contextual bandit or real RL',
            'Placebo shuffles signs globally preserving emission-level volume, not full PE/memory paid costs',
            'C corroboration channel 8 is local modeled consequence, not independently verified truth',
            'No native candidate adoption, P/S/E changes, or proof of general source-weight learning',
        ],
    }
