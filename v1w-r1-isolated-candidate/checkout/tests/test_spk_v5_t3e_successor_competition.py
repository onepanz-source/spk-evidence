"""Adversarial T3e source-native truth table, chronology and no-leakage tests."""
from __future__ import annotations
import copy
from datetime import datetime,timedelta
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from spk_v5_research.island_external_task_v5t3a import DatasetRow,canonical
from spk_v5_research.island_successor_competition_v5t3e import (
    CANDIDATES, SCHEMA, PERSIST, aggregate, audit_partition,
    episode_from_bits, metrics, native_boolean_truth_table,persist_native,
    training_only_choice,
)
from search.spk_v5_t3e_successor_competition import t3e_pins_ok,audit_inputs
from search.spk_v5_t3d_real_transition import t3d_pins_ok


def rows(start='2015-02-05 10:00:00'):
    t=datetime.strptime(start,'%Y-%m-%d %H:%M:%S')
    light=(0,230,240,0,220,230,0,240,240,0,0,220,250,0,0,240)
    occ=(False,True,True,False,True,True,False,True,True,False,False,True,True,False,False,True)
    return tuple(DatasetRow((t+timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),float(x),700.,y)
                 for i,(x,y) in enumerate(zip(light,occ)))


def pred(s='a'*64):
    return {'schema':'spk-v5-t3d-physical-successor-occupancy-onset/research-v0',
            'status':'REAL_SUCCESSOR_TEMPORAL_CAPABILITY_PASS_OCCUPANCY_ONSET_RL_NO_GO',
            'source_sha256_original_bytes':{'datatraining.txt':s,'datatest.txt':'b'*64,'datatest2.txt':'c'*64},
            'interpretation':{'native_program_updates':0}}

class TestNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.truth=native_boolean_truth_table()

    def test_a1b_four_original_input_classes(self):
        self.assertEqual(len(self.truth),4)
        self.assertEqual(self.truth['00'],dict.fromkeys(('silent','current','rise','persist'),False))
        self.assertFalse(self.truth['01']['persist']);self.assertTrue(self.truth['01']['rise'])
        self.assertTrue(self.truth['11']['persist']);self.assertFalse(self.truth['11']['rise'])
        self.assertFalse(self.truth['10']['persist'])

    def test_single_older_reading_is_not_future_label(self):
        self.assertEqual(episode_from_bits(True,True,'x').inputs,((10,1),(11,2)))
        self.assertEqual(episode_from_bits(False,True,'y').inputs,((10,0),(11,2)))
        self.assertEqual(episode_from_bits(True,False,'z').inputs,((10,1),))

    def test_boolean_input_types_strict(self):
        for a,b in ((1,True),(False,1),(None,True),('yes',False)):
            with self.assertRaises(ValueError):episode_from_bits(a,b,'x')

    def test_new_A1b_source_is_explicit_and_local(self):
        self.assertIn(('ACC',(2,1)),PERSIST)
        self.assertNotIn(('ACC',(2,0)),PERSIST)
        self.assertTrue(persist_native(episode_from_bits(True,True,'x'))['output'])
        self.assertFalse(persist_native(episode_from_bits(False,True,'y'))['output'])

    def test_forged_native_result_rejected(self):
        with patch('spk_v5_research.island_successor_competition_v5t3e.execute_episode',return_value={'output':1}):
            with self.assertRaises(AssertionError):native_boolean_truth_table()

    def test_persistent_extra_relay_cost_is_audit_not_learning(self):
        self.assertEqual(persist_native(episode_from_bits(True,True,'x'))['forward_spikes_A'],1)
        self.assertEqual(persist_native(episode_from_bits(False,True,'x'))['forward_spikes_A'],0)

class TestPublicAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.truth=native_boolean_truth_table()

    def test_label_mutation_cannot_alter_sensor_outputs(self):
        base=rows();flipped=tuple(DatasetRow(r.stamp,r.light,r.co2,not r.occupied) for r in base)
        a=audit_partition(base,'datatraining.txt',self.truth)
        b=audit_partition(flipped,'datatraining.txt',self.truth)
        self.assertEqual(a['physical_state_pattern_counts'],b['physical_state_pattern_counts'])
        self.assertNotEqual(a['candidate_metrics']['current'],b['candidate_metrics']['current'])

    def test_per_day_and_confusion_reconcile(self):
        result=audit_partition(rows(),'datatraining.txt',self.truth)
        self.assertEqual(result['admitted_successor_pairs'],len(rows())-1)
        self.assertEqual(sum(x['n'] for x in result['calendar_day_NOT_INDEPENDENT']),len(rows())-1)
        self.assertEqual(sum(result['physical_state_pattern_counts'].values()),len(rows())-1)
        self.assertEqual(result['candidate_metrics']['current']['n'],len(rows())-1)
        self.assertEqual(result['candidate_metrics']['persist']['n'],len(rows())-1)

    def test_label_free_without_current_positive(self):
        zz=tuple(DatasetRow(r.stamp,0,r.co2,r.occupied) for r in rows())
        result=audit_partition(zz,'datatraining.txt',self.truth)
        self.assertEqual(result['candidate_metrics']['current']['tp'],0)
        self.assertEqual(result['candidate_metrics']['persist']['tp'],0)

    def test_time_reverse_rejected(self):
        with self.assertRaises(ValueError):audit_partition(tuple(reversed(rows())),'datatraining.txt',self.truth)

    def test_nonregular_physical_gap_excluded_and_counted(self):
        original=list(rows())
        for j in range(7,len(original)):
            r=original[j]
            t=datetime.strptime(r.stamp,'%Y-%m-%d %H:%M:%S')+timedelta(minutes=2)
            original[j]=DatasetRow(t.strftime('%Y-%m-%d %H:%M:%S'),r.light,r.co2,r.occupied)
        z=audit_partition(tuple(original),'datatraining.txt',self.truth)
        self.assertEqual(z['rejected_irregular_seconds'],1)
        self.assertEqual(z['admitted_successor_pairs'],len(rows())-2)

    def test_wrong_names_refused(self):
        with self.assertRaises(ValueError):audit_partition(rows(),'fake.txt',self.truth)

    def test_missing_truth_table_rejected(self):
        with self.assertRaises(ValueError):audit_partition(rows(),'datatraining.txt',{})

    def test_bad_confusion_shapes_rejected(self):
        for p,y in (([True],[True,False]),([1],[True]),([],[]),([True],[1])):
            with self.assertRaises(ValueError):metrics(p,y)

    def test_one_class_balanced_accuracy_unknown(self):
        self.assertIsNone(metrics([False,False],[False,False])['balanced_accuracy'])

    def test_training_selection_no_public_data_argument(self):
        result=audit_partition(rows(),'datatraining.txt',self.truth)
        selected=training_only_choice(result)
        self.assertIn(selected,CANDIDATES)
        altered=copy.deepcopy(result)
        altered['candidate_metrics']['current']['balanced_accuracy']=0.9
        altered['candidate_metrics']['persist']['balanced_accuracy']=0.9
        self.assertEqual(training_only_choice(altered),'current')

    def test_missing_training_classes_selection_rejected(self):
        with self.assertRaises(ValueError):training_only_choice({'candidate_metrics':{}})
        with self.assertRaises(ValueError):training_only_choice({'candidate_metrics':{'current':{'balanced_accuracy':None},'persist':{'balanced_accuracy':0.5}}})

    def test_aggregate_causality_contract(self):
        result=aggregate(rows('2015-02-05 10:00:00'),'a'*64,
                         rows('2015-02-02 10:00:00'),'b'*64,
                         rows('2015-02-11 10:00:00'),'c'*64,
                         pred(),'f'*64)
        self.assertEqual(result['schema'],SCHEMA)
        self.assertFalse(result['scientific_boundary']['native_learning'])
        self.assertFalse(result['scientific_boundary']['independent_blind_holdout'])
        self.assertTrue(result['scientific_boundary']['equivalent_simple_two_reading_boolean_rule'])
        self.assertEqual(result['candidate_selection']['candidates'],list(CANDIDATES))

    def test_bad_predecessor_status_rejected(self):
        broken=pred();broken['status']='BLIND_LEARNING_SUCCESS'
        with self.assertRaises(ValueError):aggregate(rows(),'a'*64,rows('2015-02-02 10:00:00'),'b'*64,rows('2015-02-11 10:00:00'),'c'*64,broken,'f'*64)

    def test_bad_predecessor_sources_rejected(self):
        broken=pred();broken['source_sha256_original_bytes']['datatraining.txt']='0'*64
        with self.assertRaises(ValueError):aggregate(rows(),'a'*64,rows('2015-02-02 10:00:00'),'b'*64,rows('2015-02-11 10:00:00'),'c'*64,broken,'f'*64)

    def test_nonchronological_public_dates_rejected(self):
        with self.assertRaises(ValueError):aggregate(rows(),'a'*64,rows(),'b'*64,rows('2015-02-11 10:00:00'),'c'*64,pred(),'f'*64)

    def test_no_promotions_mislabeled_as_RL(self):
        r=aggregate(rows(),'a'*64,rows('2015-02-02 10:00:00'),'b'*64,rows('2015-02-11 10:00:00'),'c'*64,pred(),'f'*64)
        self.assertTrue(r['candidate_selection']['public_tests_already_examined_previously_NOT_BLIND'])
        self.assertTrue(r['scientific_boundary']['source_rows_scored_via_verified_A1b_truth_table_NOT_per_row_reexecution'])

    def test_custody_old_source_pins(self):
        t3d_pins_ok()

    def test_custody_new_source_pins(self):
        t3e_pins_ok()

    def test_create_only_nonexistent_destination(self):
        from search.spk_v5_t3a_external_uci import safe_output
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'new.json'; self.assertEqual(safe_output(p),p)
            p.write_text('exists')
            with self.assertRaises(ValueError):safe_output(p)

    def test_original_source_robust_sealing(self):
        from search.spk_v5_t3c_public_full_coverage import read_sealed
        data={'schema':'fake'};blob=canonical(data)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_bytes(blob)
            with self.assertRaises(ValueError):read_sealed(p,'0'*64)

if __name__=='__main__':unittest.main()
