"""V5 bounded island T1/T2: independent expected outcomes and fail-closed controls."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from spk_v5_research.island_objective_v5t1 import (
    Episode, CANDIDATES, CHANNELS, PROGRAMS, episodes, execute_episode,
    make_case, run_pilot, select_by_feedback, task_label,
)

ROOT = Path(__file__).resolve().parents[1]


class TestV5T1IslandResearch(unittest.TestCase):
    def test_native_three_node_admission_and_routing(self):
        ep = Episode('positive', ((0, 0), (1, 2)))
        case = make_case(ep, 'temporal')
        self.assertEqual(tuple(n.node_id for n in case.nodes), ('A', 'B', 'C'))
        self.assertEqual([(e.source_node, e.target_node, e.delay_ticks)
                          for e in case.edges], [('A', 'B', 1), ('B', 'C', 1)])

    def test_expected_six_temporal_challenges(self):
        truth = [
            (((0, 0), (1, 2)), 1), (((0, 1), (1, 2)), 0),
            (((0, 2), (1, 0)), 0), (((0, 0), (1, 0)), 0),
            (((0, 2), (1, 2)), 0), (((0, 0), (3, 2)), 0),
            (((0, 2),), 0), (((0, 0),), 0),
        ]
        for i, (trace, expected) in enumerate(truth):
            with self.subTest(i=i):
                ep = Episode(f'case{i}', trace)
                self.assertEqual(task_label(ep), expected)
                self.assertEqual(execute_episode(ep, 'temporal')['output'], expected)

    def test_live_A1b_batch_timing_makes_correct_A_B_C_path(self):
        ep = Episode('positive', ((0, 0), (1, 2)))
        r = execute_episode(ep, 'temporal', 'spread')
        self.assertEqual(r['terminal_ticks'], [3])
        self.assertEqual(r['local_ack'], 1)
        self.assertEqual(r['emitted_A'], 1)
        self.assertEqual(r['processed_batches'], 4)

    def test_placement_single_split_spread_same_semantics(self):
        for ep in episodes(0, (1, 2)):
            for cand in CANDIDATES:
                outputs = [execute_episode(ep, cand, scheme)['output']
                           for scheme in ('single', 'split', 'spread')]
                self.assertEqual(outputs, outputs[:1]*3)

    def test_shift_vs_no_shift_is_temporally_distinguishable(self):
        short = Episode('short', ((0, 0), (1, 2)))
        long = Episode('long', ((0, 0), (2, 2)))
        self.assertEqual((execute_episode(short,'temporal')['output'],
                          execute_episode(long,'temporal')['output']), (1, 0))

    def test_timestamp_translation_equivariance_with_initial_raw_zero(self):
        for start in (0, 3, 7, 11):
            ep = Episode('shift', ((start, 0), (start+1, 2)))
            self.assertEqual(execute_episode(ep, 'temporal')['terminal_ticks'], [start+3])

    def test_overemitting_baseline_generates_positive_ACK_for_wrong_task(self):
        ep = Episode('wrong', ((0, 2), (1, 0)))
        self.assertEqual(task_label(ep), 0)
        wrong = execute_episode(ep, 'overemit')
        self.assertEqual((wrong['output'], wrong['local_ack']), (1, 1))

    def test_B_ACK_is_output_count_not_island_ground_truth(self):
        good = Episode('good', ((0, 0), (1, 2)))
        bad = Episode('bad', ((0, 1), (1, 2)))
        self.assertNotEqual(task_label(good), task_label(bad))
        self.assertEqual(execute_episode(good,'overemit')['local_ack'],
                         execute_episode(bad,'overemit')['local_ack'])
        self.assertEqual(execute_episode(good,'overemit')['local_ack'], 1)

    def test_train_and_evaluation_are_separate_nonblind_synthetic_corpora(self):
        train = episodes(0,(1,2))
        evals = episodes(5,(1,2,3))
        self.assertTrue(all(min(t for t,_ in e.inputs) == 0 for e in train))
        self.assertTrue(all(min(t for t,_ in e.inputs) == 5 for e in evals))
        self.assertEqual((len(train),len(evals)), (21,30))
        self.assertEqual(sum(task_label(x) for x in evals),1)

    def test_shadow_candidate_choices_are_frozen_and_whitelisted(self):
        self.assertEqual(set(PROGRAMS), set(CANDIDATES))
        for key in CANDIDATES:
            self.assertEqual(make_case(Episode('x', ((0,2),)),key).nodes[0].instructions,
                             PROGRAMS[key])
        with self.assertRaises(ValueError):
            make_case(Episode('x', ((0,2),)), 'learned_native')

    def test_invalid_episode_types_and_same_tick_rejected(self):
        for trace in ((), ((0,0),(0,2)), ((True,0),), ((0,9),),
                      ((1,0),(0,2)), ((0,0),(1,2),(2,0))):
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                Episode('bad', trace)

    def test_select_by_feedback_cannot_read_task_labels(self):
        local = {k:(1,1,1) for k in CANDIDATES}
        self.assertEqual(select_by_feedback(local), 'overemit')
        for bad in ({}, {'overemit':(1,)}, {k: (True,) for k in CANDIDATES}):
            with self.assertRaises(ValueError):
                select_by_feedback(bad)

    def test_placebo_preserves_acks_but_does_not_provide_semantics(self):
        result = run_pilot()
        self.assertEqual(result['local_feedback_selected'], 'overemit')
        self.assertEqual(result['matched_placebo_selected'], 'overemit')
        self.assertGreater(result['false_positive_local_ACKs_train'], 0)

    def test_positive_control_exists_but_is_not_learned(self):
        result = run_pilot()
        self.assertEqual(result['supervised_oracle_upper_bound_loss_NOT_LEARNED'], 0)
        self.assertEqual(result['frozen_baseline_loss'], 15)
        self.assertEqual(result['pilot_local_feedback_loss'], 15)
        self.assertEqual(result['pilot_placebo_loss'], 15)
        self.assertFalse(result['native_learning'])

    def test_hypothesis_counterexample_identical_B_observation_different_objective(self):
        ep = Episode('ambiguous', ((0,0),(1,2)))
        execution = execute_episode(ep,'temporal')
        task1_label = task_label(ep)
        task2_label = 1 - task1_label
        self.assertEqual(execution['local_ack'], 1)
        self.assertNotEqual(int(execution['output'] != task1_label),
                            int(execution['output'] != task2_label))

    def test_result_deterministic_and_has_explicit_no_go(self):
        a,b = run_pilot(),run_pilot()
        self.assertEqual(a,b)
        self.assertEqual(a['status'], 'V5_T1_CAPABILITY_PASS_T2_ACK_IDENTIFIABILITY_FAIL_T3_NO_GO')
        self.assertFalse(a['native_backvalidation_reward_proven'])
        self.assertFalse(a['architecture_modified'])

    def test_cli_is_create_only_and_refuses_repository_output(self):
        script = ROOT/'search/spk_v5_t1_island_gate.py'
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'report.json'
            cmd = [sys.executable,str(script),str(target)]
            first = subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(target.read_text()),run_pilot())
            second = subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            nested = Path(folder)/'unsafe.json'
            bad = subprocess.run([sys.executable,str(script),str(nested)],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)


if __name__ == '__main__':
    unittest.main()
