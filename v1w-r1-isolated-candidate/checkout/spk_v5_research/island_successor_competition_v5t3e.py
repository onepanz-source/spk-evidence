"""V5-T3e source-A1b four-state truth-table and original-UCI temporal-vs-static audit.

Research-only, original UCI photo label is an EXTERNAL post-action oracle.
Public prior periods have already been inspected (T3b-d), so no blind claim.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from typing import Any

from search.spk_24n_independent_oracle_v0 import CaseV0, EdgeV0, EventV0, NodeV0
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_v5_research.island_external_task_v5t3a import DatasetRow
from spk_v5_research.island_objective_v5t1 import Episode, RELAY, execute_episode
from spk_v5_research.island_real_transition_v5t3d import (
    validated_pairs, ALLOWED_GAPS_SECONDS, LIGHT_THRESHOLD_LUX,
)

SCHEMA = 'spk-v5-t3e-real-successor-competitor/research-v0'
# RESEARCH ONLY new program, never touches frozen PROGRAMS, Core, or BV.
PERSIST = (('SHIFT', 1), ('ACC', (2, 1)), ('ACC', (4, 2)),
           ('CMP', 5), ('EMIT', 7), ('CMP', 4), ('RESET', 0))
CANDIDATES = ('current', 'persist')


def episode_from_bits(previous_bright: bool, current_bright: bool, identity: str) -> Episode:
    if type(previous_bright) is not bool or type(current_bright) is not bool:
        raise ValueError('binary sensor bits required')
    events = ((10, 1 if previous_bright else 0),)
    if current_bright:
        events += ((11, 2),)
    return Episode(identity, events)


def persist_native(ep: Episode) -> dict:
    """Invoke frozen Architecture A1b executor for research-only new A program."""
    nodes = (NodeV0('A', 8, 0, 0, PERSIST),
             NodeV0('B', 8, 0, 0, RELAY),
             NodeV0('C', 8, 0, 0, RELAY))
    edges = (EdgeV0('A', 7, 'B', 0, 1), EdgeV0('B', 7, 'C', 0, 1))
    events = tuple(EventV0(t, 'A', ch) for t, ch in ep.inputs)
    case = CaseV0(nodes, edges, events)
    actual = execute_on_pes_v1b(case, plan_v1a(case, 'spread'))['result']
    emissions = actual['emissions']
    relay = actual['terminal_outputs']
    if len(emissions) != len(relay) * 3:
        raise AssertionError('new A1b program lacks A/B/C emission conservation')
    return {'output': bool(relay), 'forward_spikes_A':sum(x['node_id']=='A' for x in emissions)}


def native_boolean_truth_table() -> dict:
    """All physically encoded input classes are covered by real A1b calls."""
    out = {}
    for previous in (False, True):
        for current in (False, True):
            ep = episode_from_bits(previous, current, f'bounded-{int(previous)}-{int(current)}')
            actual = {'silent': bool(execute_episode(ep, 'silent')['output']),
                      'current': bool(execute_episode(ep, 'overemit')['output']),
                      'rise': bool(execute_episode(ep, 'temporal')['output']),
                      'persist': persist_native(ep)['output']}
            expected = {'silent': False, 'current': current,
                        'rise': (not previous) and current,
                        'persist': previous and current}
            if actual != expected:
                raise AssertionError('native A1b physical two-reading truth table drift')
            out[f'{int(previous)}{int(current)}'] = actual
    return out


def metrics(outputs: list[bool], labels: list[bool]) -> dict:
    if (not outputs or len(outputs) != len(labels) or
        any(type(v) is not bool for v in outputs + labels)):
        raise ValueError('invalid paired outcomes')
    tp = sum(x and y for x, y in zip(outputs, labels))
    fp = sum(x and not y for x, y in zip(outputs, labels))
    fn = sum(not x and y for x, y in zip(outputs, labels))
    tn = len(labels) - tp - fp - fn
    p, n = tp+fn, tn+fp
    return {'n':len(labels), 'positive':p, 'negative':n, 'tp':tp, 'fp':fp,
            'fn':fn, 'tn':tn, 'errors':fp+fn,
            'error_rate':round((fp+fn)/len(labels), 8),
            'balanced_accuracy':round((tp/p+tn/n)/2, 8) if p and n else None}


def audit_partition(rows: tuple[DatasetRow, ...], name: str, truth: dict) -> dict:
    if name not in ('datatraining.txt','datatest.txt','datatest2.txt'):
        raise ValueError('unexpected UCI partition name')
    if len(truth) != 4 or any(set(v) != {'silent','current','rise','persist'} for v in truth.values()):
        raise ValueError('bounded source-A1b truth table required')
    preds = {k:[] for k in ('silent','current','rise','persist')}
    labels = []
    day = defaultdict(lambda:{'labels':[],'current':[],'persist':[]})
    class_counts = defaultdict(int)
    seconds = defaultdict(int)
    skipped = 0
    # Photo labels are retained by host, never included in the Episode and
    # never passed to execute_on_pes_v1b.
    for _,before,after,delta in validated_pairs(rows):
        seconds[str(delta)] += 1
        if delta not in ALLOWED_GAPS_SECONDS:
            skipped += 1
            continue
        previous = before.light >= LIGHT_THRESHOLD_LUX
        current = after.light >= LIGHT_THRESHOLD_LUX
        pattern = f'{int(previous)}{int(current)}'
        class_counts[pattern] += 1
        decision = truth[pattern]
        for k in preds:
            preds[k].append(decision[k])
        label = after.occupied
        labels.append(label)
        d=day[after.stamp[:10]]
        d['labels'].append(label)
        for k in CANDIDATES:
            d[k].append(decision[k])
    if not labels:
        raise ValueError('no admitted real successor measurements')
    # Explicit paired disagreement between time-aware and current-only rule.
    persist_wins = sum((p==y) and (c!=y) for p,c,y in zip(preds['persist'],preds['current'],labels))
    current_wins = sum((c==y) and (p!=y) for p,c,y in zip(preds['persist'],preds['current'],labels))
    per_day = [{'date':key, 'n':len(v['labels']),
                'positive':sum(v['labels']),
                'current':metrics(v['current'],v['labels']),
                'persist':metrics(v['persist'],v['labels'])}
               for key,v in sorted(day.items())]
    scores = {k:metrics(preds[k],labels) for k in preds}
    assert scores['current']['errors']-scores['persist']['errors'] == persist_wins-current_wins
    assert sum(class_counts.values())+skipped == len(rows)-1
    assert sum(v['n'] for v in per_day) == len(labels)
    return {'dataset':name,'rows':len(rows), 'admitted_successor_pairs':len(labels),
            'rejected_irregular_seconds':skipped,
            'observed_gap_seconds':dict(sorted(seconds.items())),
            'physical_state_pattern_counts':dict(sorted(class_counts.items())),
            'target':'photo-derived OCCUPANCY STATE at current reading; NOT onset',
            'candidate_metrics':scores,
            'paired_persistence_correct_current_wrong':persist_wins,
            'paired_current_correct_persistence_wrong':current_wins,
            'calendar_day_NOT_INDEPENDENT':per_day}


def training_only_choice(train: dict) -> str:
    if not isinstance(train,dict) or 'candidate_metrics' not in train:
        raise ValueError('training evidence required')
    c = train['candidate_metrics']
    if set(CANDIDATES) - set(c):
        raise ValueError('missing training candidate')
    # All training labels are allowed for host-supervised candidate choice.
    # Tie breaks toward the simpler one-reading baseline.
    values = [c[k]['balanced_accuracy'] for k in CANDIDATES]
    if any(v is None or not isinstance(v,(int,float)) for v in values):
        raise ValueError('pilot needs both target classes')
    return max(CANDIDATES,key=lambda k:(c[k]['balanced_accuracy'], -CANDIDATES.index(k)))


def aggregate(train:tuple[DatasetRow,...], train_sha:str, early:tuple[DatasetRow,...], early_sha:str,
              late:tuple[DatasetRow,...], late_sha:str, predecessor:dict,
              predecessor_sha:str) -> dict:
    src={'datatraining.txt':train_sha,'datatest.txt':early_sha,'datatest2.txt':late_sha}
    if (type(predecessor) is not dict or predecessor.get('schema') !=
            'spk-v5-t3d-physical-successor-occupancy-onset/research-v0' or
            predecessor.get('status') != 'REAL_SUCCESSOR_TEMPORAL_CAPABILITY_PASS_OCCUPANCY_ONSET_RL_NO_GO' or
            predecessor.get('source_sha256_original_bytes') != src or
            predecessor.get('interpretation',{}).get('native_program_updates') != 0):
        raise ValueError('wrong predecessor T3d scientific boundary or source custody')
    t = lambda row:datetime.strptime(row.stamp,'%Y-%m-%d %H:%M:%S')
    if not (t(early[-1]) < t(train[0]) and t(train[-1]) < t(late[0])):
        raise ValueError('public temporal partitions do not order early/train/late')
    table = native_boolean_truth_table()
    # train only is evaluated and selected BEFORE calculating public comparisons.
    pilot=audit_partition(train,'datatraining.txt',table)
    selected=training_only_choice(pilot)
    holdout_early=audit_partition(early,'datatest.txt',table)
    holdout_late=audit_partition(late,'datatest2.txt',table)
    return {'schema':SCHEMA,'status':'REAL_SUCCESSOR_A1B_PERSISTENCE_COMPARISON_PUBLIC_NOT_BLIND_NO_RL',
        'phase':'TRAIN_SELECTED_POSTHOC_PUBLIC_COMPARISON',
        'raw_original_file_sha256':src,
        't3d_report_sha256':predecessor_sha,
        'native_A1b_four_pattern_truth_table':table,
        'new_research_program_PERSIST_in_A1b':True,
        'candidate_selection':{'training_only_labels_for_host_feedback':True,
            'chosen':selected,'candidates':list(CANDIDATES),
            'method':'maximize training balanced accuracy; tie -> current-only',
            'candidate_program_frozen_before_public_comparison':True,
            'public_tests_already_examined_previously_NOT_BLIND':True},
        'cohorts':{'train':pilot,'early_public_prior_to_training':holdout_early,
                   'later_public_after_training':holdout_late},
        'scientific_boundary':{
           'physical_temporal_inputs':True,
           'label_never_sent_to_neuron':True,
           'exhaustive_four_input_A1b_truth_table':True,
           'source_rows_scored_via_verified_A1b_truth_table_NOT_per_row_reexecution':True,
           'real_temporal_order_dependence':True,
           'equivalent_simple_two_reading_boolean_rule':True,
           'independent_blind_holdout':False,
           'no_frozen_core_compiler_architecture_BV_changes':True,
           'native_learning':False,
           'endogenous_local_BV_reward':False,
           'comparisons_exploratory_after_previous_public_test_inspection':True,
           'observations_autocorrelated_and_per_day_not_independent':True},
        'limits':['The threshold 200 lux and task were previously explored on PUBLIC UCI data',
                  'This is supervised host arm-choice, NOT local endogenous neuronal learning',
                  'Strong static comparator current_light is a source A1b program, not a strawman',
                  'No independent holdout, causal learning claim, significance, or native update',
                  'Any persistence advantage can be matched by a two-reading Python Boolean rule',
                  'Physical sampling ~60s does not establish native real-time tick latency']}
