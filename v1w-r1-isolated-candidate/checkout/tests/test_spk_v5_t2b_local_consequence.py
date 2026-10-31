"""T2b: engineered positive control and negative identifiability counterexamples."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from spk_v5_research.island_objective_v5t1 import CANDIDATES, Episode, execute_episode, task_label
from spk_v5_research.island_local_consequence_v5t2 import (
    C_RECEIVER, MODES, Receipt, case_with_witness, execute_consequence,
    focused_corpus, run_experiment, select_shadow, verify_receipts,
)

ROOT = Path(__file__).resolve().parents[1]
P = Episode('positive', ((0,0),(1,2)))
N = Episode('negative', ((0,1),(1,2)))


class TestV5T2b(unittest.TestCase):
    def test_three_real_PE_nodes_and_two_declared_forward_edges(self):
        c=case_with_witness(P,'overemit','aligned')
        self.assertEqual([n.node_id for n in c.nodes],['A','B','C'])
        self.assertEqual([(e.source_node,e.target_node,e.delay_ticks) for e in c.edges],
                         [('A','B',1),('B','C',1)])
        self.assertEqual(c.nodes[2].instructions,C_RECEIVER)

    def test_context_witness_external_at_tick_two_without_task_label(self):
        c=case_with_witness(P,'overemit','aligned')
        self.assertEqual([(e.node_id,e.timestamp,e.channel) for e in c.events if e.node_id=='C'], [('C',2,0)])
        c=case_with_witness(N,'overemit','aligned')
        self.assertEqual([e for e in c.events if e.node_id=='C'],[])

    def test_source_reward_functions_cannot_access_evaluation_label(self):
        with patch('spk_v5_research.island_local_consequence_v5t2.task_label', side_effect=AssertionError('leak')):
            self.assertEqual(execute_consequence(P,'overemit','aligned')['local_reward'],1)
            self.assertEqual(execute_consequence(N,'overemit','aligned')['local_reward'],-1)

    def test_positive_has_real_two_hop_causal_batch_and_nonapplication_indicator(self):
        x=execute_consequence(P,'overemit','aligned')
        self.assertEqual((x['terminal_ticks'],x['confirmation_ticks']),((3,),(3,)))
        self.assertEqual((x['output'],x['positive_receipts'],x['negative_receipts']), (1,1,0))
        r=x['receipts'][0]
        self.assertEqual((r.emission_tick,r.b_tick,r.c_tick,r.verdict),(1,2,3,'positive'))
        verify_receipts(P,'overemit','aligned',x['receipts'])

    def test_wrong_emit_reaches_C_but_C_explicitly_denies_local_corrob(self):
        x=execute_consequence(N,'overemit','aligned')
        self.assertEqual((x['output'],x['confirmation_ticks'],x['local_reward']), (1,(),-1))
        self.assertEqual(x['receipts'][0].verdict,'negative')
        verify_receipts(N,'overemit','aligned',x['receipts'])

    def test_negative_not_inferred_from_unprocessed_or_lost_spike(self):
        x=execute_consequence(N,'silent','aligned')
        self.assertEqual((x['receipts'],x['local_reward'],x['negative_receipts']), ((),0,0))
        self.assertEqual(x['output'],0)

    def test_unavailable_C_sensor_abstains_even_when_spike_processed(self):
        x=execute_consequence(P,'overemit','absent')
        self.assertEqual((x['output'],x['local_ack'],x['local_reward'],x['abstained_receipts']), (1,1,0,1))
        self.assertEqual(x['receipts'][0].verdict,'abstain')
        verify_receipts(P,'overemit','absent',x['receipts'])

    def test_misaligned_witness_reverses_consequence_not_task_truth(self):
        self.assertEqual(task_label(P),1)
        self.assertEqual(execute_consequence(P,'overemit','inverted')['local_reward'],-1)
        self.assertEqual(execute_consequence(N,'overemit','inverted')['local_reward'],1)

    def test_C_witness_does_not_change_real_island_output_channel_seven(self):
        for ep in focused_corpus((0,3)):
            for candidate in CANDIDATES:
                native=execute_episode(ep,candidate)
                for mode in MODES:
                    x=execute_consequence(ep,candidate,mode)
                    self.assertEqual(x['output'],native['output'],(ep.identity,candidate,mode))
                    self.assertEqual(x['local_ack'],native['local_ack'])

    def test_three_PE_placements_same_judgments_and_outputs(self):
        for ep in focused_corpus((0,)):
            for candidate in CANDIDATES:
                for mode in MODES:
                    values=[(v['output'],v['receipts'],v['local_reward']) for s in
                            ('single','split','spread') if (v:=execute_consequence(ep,candidate,mode,s))]
                    self.assertEqual(values,values[:1]*3)

    def test_reverse_stale_double_and_single_adversarial(self):
        cases = focused_corpus((0,))
        actual=[execute_consequence(ep,'overemit','aligned') for ep in cases]
        self.assertEqual([task_label(ep) for ep in cases],[1,0,0,0,0,0,0])
        self.assertEqual([x['local_reward'] for x in actual], [1,-1,-2,-1,-1,-1,0])

    def test_sparse_temporal_solution_has_positive_receipts_only_in_aligned(self):
        for ep in focused_corpus((0,3)):
            x=execute_consequence(ep,'temporal','aligned')
            if task_label(ep):
                self.assertEqual((x['local_reward'],x['output']), (1,1))
            else:
                self.assertEqual((x['local_reward'],x['output']), (0,0))

    def test_receipt_forged_positive_denied(self):
        rows=execute_consequence(N,'overemit','aligned')['receipts']
        with self.assertRaises(ValueError):
            verify_receipts(N,'overemit','aligned',(replace(rows[0],local_reward=1,verdict='positive'),))

    def test_receipt_replay_denied(self):
        rows=execute_consequence(P,'overemit','aligned')['receipts']
        with self.assertRaises(ValueError): verify_receipts(P,'overemit','aligned',rows+rows)

    def test_receipt_wrong_emitter_and_early_time_denied(self):
        rows=execute_consequence(P,'overemit','aligned')['receipts']
        for forged in (replace(rows[0],candidate='temporal'), replace(rows[0],c_tick=1),
                       replace(rows[0],episode='unrelated'),replace(rows[0],c_processed=False)):
            with self.subTest(forged=forged),self.assertRaises(ValueError):
                verify_receipts(P,'overemit','aligned',(forged,))

    def test_absent_sensor_never_authorizes_false_negative(self):
        rows=execute_consequence(P,'overemit','absent')['receipts']
        with self.assertRaises(ValueError):
            verify_receipts(P,'overemit','absent',(replace(rows[0],verdict='negative',local_reward=-1),))

    def test_empty_receipts_not_negative_credit_for_silent(self):
        verify_receipts(P,'silent','aligned',())
        with self.assertRaises(ValueError): verify_receipts(P,'overemit','aligned',())

    def test_invalid_sensor_mode_or_unapproved_program_rejected(self):
        for cand,mode in (('native_reprogram','aligned'),('overemit','label_oracle'),('overemit',None)):
            with self.assertRaises(ValueError):case_with_witness(P,cand,mode)

    def test_bounded_corpus_rejects_bad_timestamps(self):
        for bad in ((),(True,),(0,0),(-1,),(0,0.5)):
            with self.assertRaises(ValueError):focused_corpus(bad)

    def test_offline_selector_rejects_forged_or_noninteger_credits(self):
        for bad in ({},{c:(True,) for c in CANDIDATES},
                    {c:(9,) for c in CANDIDATES},{'overemit':(1,)}):
            with self.assertRaises(ValueError):select_shadow(bad)
        self.assertEqual(select_shadow({c:(0,) for c in CANDIDATES}),'overemit')

    def test_observations_are_deterministic_without_random_PE(self):
        self.assertEqual(run_experiment(),run_experiment())

    def test_aligned_reward_selects_temporal_but_controls_expose_alignment(self):
        report=run_experiment()
        self.assertEqual(report['regimes']['aligned']['shadow_choice'],'temporal')
        self.assertEqual(report['regimes']['inverted']['shadow_choice'],'silent')
        self.assertEqual(report['regimes']['absent']['shadow_choice'],'overemit')
        self.assertEqual(report['regimes']['aligned']['placebo_choices'],{'silent':32})
        self.assertEqual(report['regimes']['absent']['train_abstain_by_candidate']['overemit'],56)

    def test_island_outcome_independent_of_sensor_mode(self):
        r=run_experiment()
        self.assertEqual(r['candidate_objective_evaluation']['overemit']['loss'],30)
        self.assertEqual(r['candidate_objective_evaluation']['silent']['loss'],6)
        self.assertEqual(r['candidate_objective_evaluation']['temporal']['loss'],0)
        self.assertEqual(r['regimes']['aligned']['shadow_evaluation_loss'],0)
        self.assertEqual(r['regimes']['inverted']['shadow_evaluation_loss'],6)
        self.assertEqual(r['regimes']['absent']['shadow_evaluation_loss'],30)

    def test_no_frozen_source_native_learning_or_blind_claim(self):
        r=run_experiment()
        self.assertTrue(r['engineered_witness_not_independent_task_oracle'])
        self.assertFalse(r['native_learning'])
        self.assertFalse(r['native_BV_credit_delivered'])
        self.assertFalse(r['frozen_sources_modified'])
        self.assertIn('T3_BLIND_BLOCKED',r['status'])

    def test_cli_create_only_and_no_overwrite(self):
        script=ROOT/'search/spk_v5_t2b_local_consequence.py'
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'result.json'
            one=subprocess.run([sys.executable,str(script),str(dest)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(one.returncode,0,one.stderr)
            self.assertEqual(json.loads(dest.read_text()),run_experiment())
            two=subprocess.run([sys.executable,str(script),str(dest)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(two.returncode,0)

    def test_cli_refuses_repository_target_and_symlink(self):
        script=ROOT/'search/spk_v5_t2b_local_consequence.py'
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            target=Path(folder)/'report.json'
            result=subprocess.run([sys.executable,str(script),str(target)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
        with tempfile.TemporaryDirectory() as folder:
            linked=Path(folder)/'link.json'
            linked.symlink_to(Path(folder)/'nowhere')
            result=subprocess.run([sys.executable,str(script),str(linked)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)


if __name__ == '__main__':
    unittest.main()
