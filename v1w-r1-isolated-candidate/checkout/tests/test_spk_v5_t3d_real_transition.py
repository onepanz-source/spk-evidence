"""T3d genuine temporal-successor and observational isolation tests."""
import json
import tempfile
from datetime import datetime,timedelta
from hashlib import sha256
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_v5_research.island_external_task_v5t3a import DatasetRow,canonical
from spk_v5_research.island_objective_v5t1 import execute_episode
from spk_v5_research.island_real_transition_v5t3d import (
    SCHEMA,ALLOWED_GAPS_SECONDS,validated_pairs,to_transition_episode,
    audit_partition,aggregate,confusion,
)
from search.spk_v5_t3d_real_transition import audit_inputs
from search.spk_v5_t3c_public_full_coverage import read_sealed


def rows(lights=(0,300,300,0,300,300,0), labels=(False,True,True,False,True,False,False),
         *, start='2015-02-05 10:00:00',gap=60):
    t=datetime.fromisoformat(start)
    return tuple(DatasetRow((t+i*timedelta(seconds=gap)).strftime('%Y-%m-%d %H:%M:%S'),
                  float(light),700.0,bool(label)) for i,(light,label) in enumerate(zip(lights,labels)))


def predecessor(s1='a'*64,s2='b'*64,s3='c'*64):
    return {'schema':'spk-v5-t3c-full-public-coverage-audit/research-v0',
            'status':'PUBLIC_A1B_FULL_COVERAGE_STATIC_EQUIVALENCE_NO_BLIND_NO_RL',
            'source_sha256_original_bytes':{'datatraining.txt':s1,'datatest.txt':s2,'datatest2.txt':s3},
            'key_interpretation':{'temporal_is_exactly_static_light_ge_200_AND_co2_ge_600':True,
                                  'physical_temporal_pattern_learning_demonstrated':False}}


class TestRealTemporalSuccessor(unittest.TestCase):
    def test_true_successor_fires(self):
        r=rows()[:2]
        ep=to_transition_episode(*r,identity='a',physical_delta=60)
        self.assertEqual(ep.inputs,((10,0),(11,2)))
        self.assertEqual(execute_episode(ep,'temporal')['output'],1)
        self.assertEqual(execute_episode(ep,'overemit')['output'],1)

    def test_bright_continuation_not_rising(self):
        r=rows()[1:3]
        ep=to_transition_episode(*r,identity='b',physical_delta=60)
        self.assertEqual(ep.inputs,((10,1),(11,2)))
        self.assertEqual(execute_episode(ep,'temporal')['output'],0)
        self.assertEqual(execute_episode(ep,'overemit')['output'],1)

    def test_not_rising_with_current_dark(self):
        ep=to_transition_episode(*rows()[2:4],identity='dark',physical_delta=60)
        self.assertEqual(len(ep.inputs),1)
        self.assertEqual(execute_episode(ep,'temporal')['output'],0)

    def test_wall_interval_59_60_61_accepted(self):
        for gap in ALLOWED_GAPS_SECONDS:
            a,b=rows(gap=gap)[:2]
            ep=to_transition_episode(a,b,identity=f'gap{gap}',physical_delta=gap)
            self.assertEqual(execute_episode(ep,'temporal')['output'],1)

    def test_gap_120_rejected_not_coerced_to_one_tick(self):
        a,b=rows(gap=120)[:2]
        with self.assertRaises(ValueError):
            to_transition_episode(a,b,identity='bad',physical_delta=120)

    def test_gapped_pair_skipped_and_counted(self):
        x=rows()
        irregular=list(x)
        irregular[2]=DatasetRow((datetime.fromisoformat(x[2].stamp)+timedelta(seconds=120)).strftime('%Y-%m-%d %H:%M:%S'),300,700,True)
        # The following index remains earlier than altered timestamp -> reject.
        with self.assertRaises(ValueError):list(validated_pairs(tuple(irregular)))
        # Monotone irregular series admits all other edges.
        r=(x[0],x[1],DatasetRow('2015-02-05 10:03:00',300,700,True),
           DatasetRow('2015-02-05 10:04:00',300,700,True))
        result=audit_partition(r,'datatraining.txt')
        self.assertEqual(result['rejected_gapped_pairs'],1)
        self.assertEqual(result['admitted_successor_pairs'],2)

    def test_nonmonotone_rejected(self):
        x=rows()
        with self.assertRaises(ValueError): list(validated_pairs((x[0],x[0],x[1])))

    def test_mutation_of_photo_label_cannot_change_A_events(self):
        x=rows()
        altered=tuple(DatasetRow(r.stamp,r.light,r.co2,not r.occupied) for r in x)
        for i in range(1,len(x)):
            orig=to_transition_episode(x[i-1],x[i],identity=str(i),physical_delta=60)
            changed=to_transition_episode(altered[i-1],altered[i],identity=str(i),physical_delta=60)
            self.assertEqual(orig,changed)

    def test_label_tamper_changes_auditor_not_spikes(self):
        x=rows()
        alt=tuple(DatasetRow(r.stamp,r.light,r.co2,False) for r in x)
        a=audit_partition(x,'datatraining.txt')
        b=audit_partition(alt,'datatraining.txt')
        self.assertEqual(a['current_bright_given_previous_dark'],b['current_bright_given_previous_dark'])
        self.assertNotEqual(a['native_A1b_full_successor_replay']['temporal']['tp'],
                            b['native_A1b_full_successor_replay']['temporal']['tp'])

    def test_temporal_distinguishes_fixed_current_different_past(self):
        x=rows()
        a=to_transition_episode(x[0],x[1],identity='one',physical_delta=60)
        b=to_transition_episode(x[1],x[2],identity='two',physical_delta=60)
        self.assertEqual(x[1].light,x[2].light)
        self.assertEqual(execute_episode(a,'temporal')['output'],1)
        self.assertEqual(execute_episode(b,'temporal')['output'],0)

    def test_reverse_real_order_no_false_temporal_positive(self):
        x=rows()
        # Reverse sensor values but keep causal physical order and timestamps.
        a=DatasetRow(x[0].stamp,300,700,False)
        b=DatasetRow(x[1].stamp,0,700,True)
        ep=to_transition_episode(a,b,identity='swap',physical_delta=60)
        self.assertEqual(execute_episode(ep,'temporal')['output'],0)

    def test_native_replay_is_mandatory(self):
        with patch('spk_v5_research.island_real_transition_v5t3d.execute_episode',return_value={'output':1}):
            with self.assertRaisesRegex(AssertionError,'A1b mismatch'):
                audit_partition(rows(),'datatraining.txt')

    def test_onset_frequency_and_two_reading_equivalence(self):
        r=audit_partition(rows(),'datatraining.txt')
        self.assertEqual(r['admitted_successor_pairs'],6)
        self.assertEqual(r['native_A1b_full_successor_replay']['temporal']['tp'],2)
        self.assertEqual(r['native_A1b_full_successor_replay']['temporal']['errors'],0)
        self.assertTrue(r['exact_temporal_equivalence_to_two_reading_rule'])
        self.assertTrue(r['counterexample_to_current_only_equivalence_exists'])

    def test_cannot_claim_universal_causal_learning(self):
        r=audit_partition(rows(),'datatraining.txt')
        self.assertFalse(r['causal_input_assertions']['physical_latency_of_internal_SPk_tick_verified'])
        self.assertTrue(r['causal_input_assertions']['photo_label_not_sent_to_A'])

    def test_static_current_only_is_different(self):
        r=audit_partition(rows(),'datatraining.txt')
        self.assertNotEqual(r['native_A1b_full_successor_replay']['temporal']['errors'],
                            r['native_A1b_full_successor_replay']['overemit']['errors'])

    def test_disallow_bad_episode_identity_and_source_types(self):
        r=rows()
        for identity in ('',None):
            with self.assertRaises(ValueError):to_transition_episode(r[0],r[1],identity=identity,physical_delta=60)
        with self.assertRaises(ValueError):to_transition_episode('not-row',r[1],identity='a',physical_delta=60)
        with self.assertRaises(ValueError):audit_partition(list(r),'datatraining.txt')

    def test_wrong_physical_delta_refused(self):
        a,b=rows()[:2]
        for n in (59,61,True,60.0):
            with self.assertRaises(ValueError):to_transition_episode(a,b,identity='x',physical_delta=n)

    def test_wrong_partition_refused(self):
        with self.assertRaises(ValueError):audit_partition(rows(),'invented.txt')

    def test_confusion_strict_integer_not_bool(self):
        with self.assertRaises(ValueError):confusion([True,False],[True])
        with self.assertRaises(ValueError):confusion([1],[True])
        with self.assertRaises(ValueError):confusion([],[])

    def test_single_class_balanced_is_unknown(self):
        r=confusion([False,False,False],[False,False,False])
        self.assertEqual(r['errors'],0)
        self.assertIsNone(r['balanced_accuracy'])

    def test_aggregate_read_order_and_predecessor(self):
        early=rows(start='2015-02-02 10:00:00')
        train=rows(start='2015-02-05 10:00:00')
        late=rows(start='2015-02-11 10:00:00')
        out=aggregate(train,'a'*64,early,'b'*64,late,'c'*64,predecessor(),'d'*64)
        self.assertEqual(out['schema'],SCHEMA)
        self.assertFalse(out['interpretation']['new_shadow_learning_occurred'])
        self.assertFalse(out['interpretation']['independent_blind_holdout'])
        self.assertEqual(out['interpretation']['native_program_updates'],0)
        self.assertIn('late_PUBLIC_TEST',out['splits'])

    def test_reject_predecessor_forged(self):
        early=rows(start='2015-02-02 10:00:00')
        train=rows(start='2015-02-05 10:00:00')
        late=rows(start='2015-02-11 10:00:00')
        p=predecessor();p['key_interpretation']['physical_temporal_pattern_learning_demonstrated']=True
        with self.assertRaises(ValueError):aggregate(train,'a'*64,early,'b'*64,late,'c'*64,p,'d'*64)
        with self.assertRaises(ValueError):aggregate(train,'a'*64,early,'b'*64,late,'c'*64,predecessor('0'*64),'d'*64)

    def test_reject_nonchronological_partitions(self):
        early=rows(start='2015-02-02 10:00:00')
        train=rows(start='2015-02-05 10:00:00')
        with self.assertRaises(ValueError):aggregate(train,'a'*64,train,'b'*64,early,'c'*64,predecessor(),'d'*64)

    def test_predecessor_sealed_exact(self):
        p=predecessor()
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'t3c.json';data=canonical(p);f.write_bytes(data)
            self.assertEqual(read_sealed(f,sha256(data).hexdigest()),p)
            with self.assertRaises(ValueError):read_sealed(f,'0'*64)
            f.write_bytes(b'{"a":1}')
            with self.assertRaises(ValueError):read_sealed(f,sha256(f.read_bytes()).hexdigest())

    def test_daily_pairs_reconcile(self):
        r=audit_partition(rows(),'datatraining.txt')
        for p in ('temporal','overemit','silent'):
            self.assertEqual(sum(day['metrics'][p]['observations'] for day in r['per_calendar_day_NONINDEPENDENT']),
                             r['admitted_successor_pairs'])
            self.assertEqual(sum(day['metrics'][p]['errors'] for day in r['per_calendar_day_NONINDEPENDENT']),
                             r['native_A1b_full_successor_replay'][p]['errors'])

    def test_data_order_is_not_synthetic_one_row(self):
        x=rows()
        ep=to_transition_episode(x[0],x[1],identity='pair',physical_delta=60)
        self.assertNotEqual(ep.inputs,((10,0),(10,2)))
        self.assertEqual(len(ep.inputs),2)

if __name__=='__main__':unittest.main()
