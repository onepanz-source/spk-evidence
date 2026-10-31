"""V5-T3f: post-hoc calendar concentration, physics, source custody and refusals."""
from __future__ import annotations

import copy
from datetime import datetime,timedelta
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_v5_research.island_external_task_v5t3a import DatasetRow,canonical
from spk_v5_research.island_successor_competition_v5t3e import native_boolean_truth_table
from spk_v5_research.island_calendar_stratification_v5t3f import (
    SCHEMA, _sum_metrics, audit_partition, aggregate,
)
from search.spk_v5_t3f_day_stratification import t3f_pins_ok,audit_inputs
from search.spk_v5_t3e_successor_competition import t3e_pins_ok
from search.spk_v5_t3a_external_uci import safe_output

SRC={'datatraining.txt':'a'*64,'datatest.txt':'b'*64,'datatest2.txt':'c'*64}

def fixture(start='2015-02-05 10:00:00',occupancy=(False,)*9):
    t=datetime.strptime(start,'%Y-%m-%d %H:%M:%S')
    lights=(0,230,240,0,230,240,0,250,250)
    return tuple(DatasetRow((t+timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),
                            float(lights[i]),700.,v) for i,v in enumerate(occupancy))

def pilot_rows():
    return fixture('2015-02-05 10:00:00',(False,False,True,False,False,True,False,False,True))

def predecessor():
    from spk_v5_research.island_successor_competition_v5t3e import aggregate as old
    from tests.test_spk_v5_t3e_successor_competition import pred
    return old(pilot_rows(),'a'*64,
               fixture('2015-02-02 10:00:00'),'b'*64,
               fixture('2015-02-11 10:00:00'),'c'*64,
               pred(),'d'*64)

class TestStratification(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.truth=native_boolean_truth_table()

    def test_no_label_sent_into_neuron(self):
        a=fixture(occupancy=(False,)*9)
        b=fixture(occupancy=(True,)*9)
        x=audit_partition(a,'datatraining.txt',self.truth)
        y=audit_partition(b,'datatraining.txt',self.truth)
        self.assertEqual(x['actual_dark_to_bright_opportunities'],y['actual_dark_to_bright_opportunities'])
        self.assertNotEqual(x['total']['net_errors_avoided_by_persist'],y['total']['net_errors_avoided_by_persist'])

    def test_every_disagreement_is_source_physical_dark_to_bright(self):
        a=audit_partition(fixture(),'datatraining.txt',self.truth)
        self.assertEqual(a['actual_dark_to_bright_opportunities'],3)
        self.assertEqual(a['total']['persist_fixes'],3)
        self.assertEqual(a['total']['persist_regressions'],0)

    def test_positive_rise_is_persistence_regression(self):
        occ=(False,True,True,False,True,True,False,True,True)
        x=audit_partition(fixture(occupancy=occ),'datatraining.txt',self.truth)
        self.assertEqual(x['total']['persist_regressions'],3)
        self.assertEqual(x['total']['persist_fixes'],0)

    def test_day_absent_vs_day_positive(self):
        a=fixture('2015-02-05 10:00:00')
        b=fixture('2015-02-06 10:00:00',(False,True,True,False,True,True,False,True,True))
        combined=a+b
        x=audit_partition(combined,'datatraining.txt',self.truth)
        self.assertEqual(x['day_count'],2)
        self.assertEqual(x['rejected_irregular_intervals'],1)
        self.assertEqual(x['stratified_by_posthoc_photo_label_presence']['zero_photo_occupancy_day']['net_errors_avoided_by_persist'],3)
        self.assertEqual(x['stratified_by_posthoc_photo_label_presence']['positive_photo_occupancy_day']['net_errors_avoided_by_persist'],-3)
        self.assertEqual(x['total']['net_errors_avoided_by_persist'],0)

    def test_day_groups_never_implicitly_merge_on_calendar_midnight(self):
        t=datetime(2015,2,5,23,58)
        row=tuple(DatasetRow((t+timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),float((0,250,250,0,250)[i]),700.,False) for i in range(5))
        result=audit_partition(row,'datatraining.txt',self.truth)
        self.assertEqual(result['day_count'],2)
        self.assertEqual(result['total']['n'],4)

    def test_irregular_source_gap_is_excluded(self):
        x=list(fixture())
        for i in range(5,len(x)):
            d=datetime.strptime(x[i].stamp,'%Y-%m-%d %H:%M:%S')+timedelta(minutes=2)
            x[i]=DatasetRow(d.strftime('%Y-%m-%d %H:%M:%S'),x[i].light,x[i].co2,x[i].occupied)
        y=audit_partition(tuple(x),'datatraining.txt',self.truth)
        self.assertEqual(y['rejected_irregular_intervals'],1)
        self.assertEqual(y['total']['n'],7)

    def test_out_of_order_clock_refused(self):
        with self.assertRaises(ValueError):audit_partition(tuple(reversed(fixture())),'datatraining.txt',self.truth)

    def test_no_pair_refused(self):
        rows=fixture()[:1]
        with self.assertRaises(ValueError):audit_partition(rows,'datatraining.txt',self.truth)

    def test_unknown_partition_name_refused(self):
        with self.assertRaises(ValueError):audit_partition(fixture(),'fake.txt',self.truth)

    def test_forged_truth_table_refused(self):
        fake=copy.deepcopy(self.truth)
        fake['01']['persist']=True
        with self.assertRaises(ValueError):audit_partition(fixture(),'datatraining.txt',fake)

    def test_missing_truth_table_refused(self):
        with self.assertRaises(ValueError):audit_partition(fixture(),'datatraining.txt',{})

    def test_untrusted_native_truth_source_rejected_if_changed(self):
        with patch('spk_v5_research.island_calendar_stratification_v5t3f.native_boolean_truth_table',return_value={}):
            with self.assertRaises(ValueError):audit_partition(fixture(),'datatraining.txt',self.truth)

    def test_metrics_aggregate_reconciliation(self):
        x=audit_partition(fixture(),'datatraining.txt',self.truth)
        self.assertEqual(sum(d['n'] for d in x['days']),x['total']['n'])
        self.assertEqual(sum(d['net_errors_avoided_by_persist'] for d in x['days']),x['total']['net_errors_avoided_by_persist'])
        self.assertEqual(sum(x[k] for k in ('days_persist_better','days_current_better','days_tied')),x['day_count'])

    def test_bad_discordance_accounting_rejected(self):
        with self.assertRaises(AssertionError):_sum_metrics([{'n':2,'positive':1,'current_wrong':1,'persist_wrong':0,
                                                  'persist_correct_current_wrong':0,
                                                  'current_correct_persist_wrong':0}])

    def test_leave_one_day_out_is_arithmetically_consistent(self):
        x=audit_partition(fixture(),'datatraining.txt',self.truth)
        self.assertEqual(len(x['leave_one_day_out_DIAGNOSTIC_ONLY']),x['day_count'])
        self.assertEqual(x['leave_one_day_out_DIAGNOSTIC_ONLY'][0]['other_days_net_errors_avoided'],0)

    def test_synthetic_single_day_all_zero_is_not_false_positive(self):
        x=audit_partition(fixture(),'datatraining.txt',self.truth)
        self.assertTrue(x['days'][0]['all_labels_zero'])
        self.assertEqual(x['days'][0]['positive'],0)

    def test_synthetic_one_day_has_externally_occupied_label(self):
        x=audit_partition(fixture(occupancy=(False,True,True,False,True,True,False,True,True)),'datatraining.txt',self.truth)
        self.assertFalse(x['days'][0]['all_labels_zero'])
        self.assertEqual(x['days'][0]['positive'],6)

    def test_no_new_programs_or_weight_update(self):
        x=aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,predecessor(),'e'*64)
        self.assertEqual(x['schema'],SCHEMA)
        self.assertTrue(x['interpretation']['no_native_learning'])
        self.assertTrue(x['interpretation']['no_endogenous_island_reward'])
        self.assertTrue(x['interpretation']['public_data_already_explored'])
        self.assertEqual(x['selection_from_train_frozen'],'persist')

    def test_forged_predecessor_schema_rejected(self):
        p=predecessor();p['schema']='bad'
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_forged_predecessor_source_sha_rejected(self):
        p=predecessor();p['raw_original_file_sha256']['datatraining.txt']='0'*64
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_forged_predecessor_policy_rejected(self):
        p=predecessor();p['candidate_selection']['chosen']='current'
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_fake_native_learning_promotion_refused(self):
        p=predecessor();p['scientific_boundary']['native_learning']=True
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_fake_blind_promotion_refused(self):
        p=predecessor();p['scientific_boundary']['independent_blind_holdout']=True
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_forged_predecessor_totals_rejected(self):
        p=predecessor();p['cohorts']['later_public_after_training']['candidate_metrics']['persist']['errors']+=1
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_forged_paired_disagreement_rejected(self):
        p=predecessor();p['cohorts']['later_public_after_training']['paired_persistence_correct_current_wrong']+=1
        with self.assertRaises(ValueError):aggregate(pilot_rows(),fixture('2015-02-02 10:00:00'),fixture('2015-02-11 10:00:00'),SRC,p,'e'*64)

    def test_original_pins(self):
        t3e_pins_ok()

    def test_new_pins(self):
        t3f_pins_ok()

    def test_nonexistent_output_required(self):
        with tempfile.TemporaryDirectory() as base:
            f=Path(base)/'test.json'
            self.assertEqual(safe_output(f),f)
            f.write_text('exists')
            with self.assertRaises(ValueError):safe_output(f)

    def test_outbound_path_inside_repo_forbidden(self):
        with self.assertRaises(ValueError):safe_output(Path(__file__).resolve().parent.parent/'docs/fake.json')

    def test_unsealed_report_rejected(self):
        from search.spk_v5_t3c_public_full_coverage import read_sealed
        with tempfile.TemporaryDirectory() as base:
            path=Path(base)/'fake.json'
            path.write_bytes(canonical(predecessor()))
            with self.assertRaises(ValueError):read_sealed(path,'f'*64)

    def test_pinned_t3e_report_cannot_be_tampered(self):
        a=json.loads((Path(__file__).resolve().parent.parent/'docs/spk-v5-t3e-original-uci-reference.json').read_text())
        self.assertFalse(a['scientific_boundary']['native_learning'])
        self.assertEqual(a['candidate_selection']['chosen'],'persist')

if __name__=='__main__':unittest.main()
