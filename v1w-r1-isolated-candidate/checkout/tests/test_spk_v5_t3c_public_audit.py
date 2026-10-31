"""Adversarial V5-T3c public coverage auditor. No UCI source bundled."""
import json
import tempfile
from datetime import datetime,timedelta
from hashlib import sha256
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_v5_research.island_external_task_v5t3a import (
    DatasetRow,canonical,pilot,evaluate,
)
from spk_v5_research.island_public_audit_v5t3c import (
    SCHEMA,COHORTS,COHORT_SIZE,audit_partition,aggregate_report,
    confusion,validate_temporal_order,
)
from search.spk_v5_t3c_public_full_coverage import read_sealed


def fixture(start=0,n=480):
    t=datetime(2015,1,1)+timedelta(days=start)
    return tuple(DatasetRow((t+timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),
                            400 if i%4 in (0,1) else 0,
                            700 if i%4 in (0,2) else 500,
                            i%4==0) for i in range(n))


class TestT3c(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.early=fixture(0)
        cls.train=fixture(10)
        cls.late=fixture(20)
        cls.pilot=pilot(cls.train,'a'*64)
        cls.pilot.update({
            'source_encoding':'original UCI seven-column header, eight-column indexed rows',
            'source_id_sent_to_neuron':False,
            'source_sha_basis':'raw original file bytes, no transformations',
            'authentic_uci_ingress_schema':'spk-v5-t3b-authentic-uci-row-index/research-v0',
        })
        cls.pilot['claims_excluded'].append('UCI photo labels are external oracle supervision, not endogenous RL credit')
        cls.published=evaluate(cls.late,'b'*64,cls.pilot)
        cls.published.update({
            'source_encoding':'original UCI seven-column header, eight-column indexed rows',
            'source_id_sent_to_neuron':False,
            'source_sha_basis':'raw original file bytes, no transformations',
            'authentic_uci_ingress_schema':'spk-v5-t3b-authentic-uci-row-index/research-v0',
        })
        cls.published['claims_excluded'].append('UCI photo labels are external oracle supervision, not endogenous RL credit')

    def test_positive_matrix(self):
        report=aggregate_report(self.early,'c'*64,self.late,'b'*64,self.train,'a'*64,
                 self.pilot,'d'*64,self.published,'e'*64)
        self.assertEqual(report['schema'],SCHEMA)
        self.assertTrue(report['key_interpretation']['temporal_is_exactly_static_light_ge_200_AND_co2_ge_600'])
        self.assertFalse(report['key_interpretation']['physical_temporal_pattern_learning_demonstrated'])
        for v in report['datasets'].values():
            self.assertEqual(v['full_native_A1b_candidate_audit']['temporal']['errors'],0)
            self.assertEqual(len(v['disjoint_8x60_stratification']),8)
            self.assertTrue(all(c['n']==60 for c in v['disjoint_8x60_stratification']))
            self.assertTrue(v['exact_static_equivalence_all_rows'])
            self.assertEqual(v['static_sensors_auditor_only']['light_and_co2']['errors'],0)

    def test_disjoint_cohorts_sum_and_replay(self):
        r=audit_partition(self.early,original_name='datatest.txt')
        for c in ('temporal','overemit','silent'):
            cohort=sum(x['metrics'][c]['errors'] for x in r['disjoint_8x60_stratification'])
            self.assertTrue(cohort >= 0)
            self.assertEqual(sum(x['metrics'][c]['observations'] for x in r['disjoint_8x60_stratification']),480)
            self.assertEqual(sum(x['metrics'][c]['observations'] for x in r['per_calendar_day']),480)

    def test_confusion_counts_and_balanced(self):
        rows=(DatasetRow('x',201,601,True),DatasetRow('y',0,601,False),
              DatasetRow('z',201,601,False),DatasetRow('q',0,601,True))
        m=confusion(rows,(True,False,True,False))
        self.assertEqual((m['tp'],m['tn'],m['fp'],m['fn']),(1,1,1,1))
        self.assertEqual(m['balanced_accuracy'],0.5)
        self.assertEqual(m['errors'],2)

    def test_confusion_single_class_unknown_balanced(self):
        rows=(DatasetRow('x',200,600,False),)*3
        self.assertIsNone(confusion(rows,(False,)*3)['balanced_accuracy'])

    def test_malformed_prediction_length_and_types(self):
        with self.assertRaises(ValueError):confusion(self.early,())
        with self.assertRaises(ValueError):confusion((self.early[0],),(1,))

    def test_wrong_partition_and_short(self):
        for name in ('train','data','datatest3.txt'):
            with self.assertRaises(ValueError):audit_partition(self.early,original_name=name)
        with self.assertRaises(ValueError):audit_partition(self.early[:-1],original_name='datatest2.txt')

    def test_native_equivalence_detects_transposed_model(self):
        from spk_v5_research.island_public_audit_v5t3c import evaluate_candidate as native
        def wrong(episodes,choice):
            return native(episodes,'overemit' if choice=='temporal' else choice)
        with patch('spk_v5_research.island_public_audit_v5t3c.evaluate_candidate',side_effect=wrong):
            with self.assertRaisesRegex(ValueError,'static sensor rule'):
                audit_partition(self.early,original_name='datatest.txt')

    def test_training_pilot_certificate_reconstruction(self):
        p=dict(self.pilot)
        p['learner']=dict(p['learner'])
        p['learner']['selected']='overemit'
        with self.assertRaises(ValueError):
            aggregate_report(self.early,'c'*64,self.late,'b'*64,self.train,'a'*64,
                 p,'d'*64,self.published,'e'*64)

    def test_published_metric_tampering_refused(self):
        p=dict(self.published)
        p['selected_error']+=1
        with self.assertRaises(ValueError):
            aggregate_report(self.early,'c'*64,self.late,'b'*64,self.train,'a'*64,
                 self.pilot,'d'*64,p,'e'*64)

    def test_published_counterfactual_tampering_refused(self):
        p=json.loads(json.dumps(self.published))
        p['post_selection_counterfactual_audit_ONLY']['silent']['error']+=1
        with self.assertRaises(ValueError):
            aggregate_report(self.early,'c'*64,self.late,'b'*64,self.train,'a'*64,
                 self.pilot,'d'*64,p,'e'*64)

    def test_backdated_pilot_refused(self):
        with self.assertRaises(ValueError):
            validate_temporal_order(self.early,self.late,self.train)

    def test_early_is_prior_not_future(self):
        validate_temporal_order(self.early,self.train,self.late)
        with self.assertRaises(ValueError):validate_temporal_order(self.train,self.train,self.late)
        with self.assertRaises(ValueError):validate_temporal_order((),self.train,self.late)

    def test_sealed_evidence_canonical_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'cert.json'
            raw=canonical(self.pilot)
            p.write_bytes(raw)
            self.assertEqual(read_sealed(p,sha256(raw).hexdigest()),self.pilot)
            with self.assertRaises(ValueError):read_sealed(p,'0'*64)
            with self.assertRaises(ValueError):read_sealed(p,'G'*64)
            p.write_bytes(b'{"a":1}')
            with self.assertRaises(ValueError):read_sealed(p,sha256(p.read_bytes()).hexdigest())

    def test_posthoc_light_only_can_beat_frozen_arm(self):
        original=fixture(0)
        labels_light=tuple(DatasetRow(x.stamp,x.light,x.co2,x.light>=200) for x in original)
        result=audit_partition(labels_light,original_name='datatest.txt')
        self.assertEqual(result['static_sensors_auditor_only']['light_only']['errors'],0)
        self.assertGreater(result['full_native_A1b_candidate_audit']['temporal']['errors'],0)
        self.assertTrue(result['exact_static_equivalence_all_rows'])

    def test_day_slices_preserve_original_totals(self):
        observed=audit_partition(self.early,original_name='datatest.txt')
        for arm in ('temporal','overemit','silent'):
            self.assertEqual(sum(day['metrics'][arm]['errors'] for day in observed['per_calendar_day']),
                             observed['full_native_A1b_candidate_audit'][arm]['errors'])
            self.assertEqual(sum(day['metrics'][arm]['positive'] for day in observed['per_calendar_day']),
                             observed['full_native_A1b_candidate_audit'][arm]['positive'])

    def test_invalid_multiple_spike_claim_is_refused(self):
        from spk_v5_research.island_public_audit_v5t3c import evaluate_candidate as native
        def altered(episodes,arm):
            result=native(episodes,arm)
            if arm=='temporal':result['forward_spikes']=2
            return result
        with patch('spk_v5_research.island_public_audit_v5t3c.evaluate_candidate',side_effect=altered):
            with self.assertRaisesRegex(ValueError,'more than one output'):
                audit_partition(self.early,original_name='datatest2.txt')

    def test_earlier_test_is_not_future_holdout(self):
        self.assertLess(self.early[-1].stamp,self.train[0].stamp)
        self.assertLess(self.train[-1].stamp,self.late[0].stamp)

    def test_symlink_evidence_refused(self):
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/'a',Path(td)/'b'
            a.write_bytes(canonical(self.pilot))
            b.symlink_to(a)
            with self.assertRaises(ValueError):read_sealed(b,sha256(a.read_bytes()).hexdigest())


if __name__=='__main__': unittest.main()
