"""V5-T3a anti-leakage, source integrity, and real A1b smoke regression."""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from spk_v5_research.island_external_task_v5t3a import (
    DatasetRow, read_uci, downsample, to_demand_episode, balanced_schedule,
    fit_shadow, pilot, evaluate, canonical, sha_bytes, CANDIDATES, PILOT_ROWS,
)
from spk_v5_research.island_endogenous_demand_v5t2c import observe_closed_episode

ROOT=Path(__file__).resolve().parent.parent
RUNNER=ROOT/'search/spk_v5_t3a_external_uci.py'


def make_source(path:Path, count:int, offset=0, *, wrong=False):
    with path.open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['date','Temperature','Humidity','Light','CO2','HumidityRatio','Occupancy'])
        for i in range(count):
            bright=i%4 in (0,1)
            high=i%4 in (0,2)
            label=int(bright and high)
            if wrong:label=1-label
            stamp=datetime(2020,1,1)+timedelta(minutes=offset+i)
            w.writerow([stamp.strftime('%Y-%m-%d %H:%M:%S'),22,40,250 if bright else 50,
                        700 if high else 480,0.006,label])


class TestV5T3aPublicExternalTask(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='spk-v5-t3a-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.train=self.root/'datatraining.txt'
        self.test=self.root/'datatest2.txt'
        make_source(self.train,180)
        make_source(self.test,60,offset=300)

    def rows(self):
        return read_uci(self.train, expected_filename='datatraining.txt')

    def test_01_source_provenance_raw_digest(self):
        rows,sha=self.rows()
        self.assertEqual(len(rows),180)
        self.assertEqual(sha,hashlib.sha256(self.train.read_bytes()).hexdigest())

    def test_02_filename_role_enforced(self):
        with self.assertRaises(ValueError):read_uci(self.train,expected_filename='datatest2.txt')

    def test_03_symlinked_source_rejected(self):
        alias=self.root/'alias'
        alias.symlink_to(self.train)
        with self.assertRaises(ValueError):read_uci(alias,expected_filename='alias')

    def test_04_truncated_source_rejected(self):
        self.train.write_text('date,Light\n1,2\n')
        with self.assertRaises(ValueError):self.rows()

    def test_05_duplicate_timestamp_rejected(self):
        data=self.train.read_text().splitlines()
        data[2]=data[1]
        self.train.write_text('\n'.join(data)+'\n')
        with self.assertRaises(ValueError):self.rows()

    def test_06_reverse_timestamps_rejected(self):
        lines=self.train.read_text().splitlines()
        lines[3],lines[4]=lines[4],lines[3]
        self.train.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(ValueError):self.rows()

    def test_07_bad_occupancy_rejected(self):
        lines=self.train.read_text().splitlines()
        lines[1]=lines[1].rsplit(',',1)[0]+',2'
        self.train.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(ValueError):self.rows()

    def test_08_nan_sensor_rejected(self):
        lines=self.train.read_text().splitlines()
        parts=lines[2].split(',');parts[4]='nan';lines[2]=','.join(parts)
        self.train.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(ValueError):self.rows()

    def test_09_input_adapter_independent_of_label(self):
        x=DatasetRow('2020-01-01 00:00:00',250.,700.,True)
        self.assertEqual(to_demand_episode(x,index=4).episode,
                         to_demand_episode(replace(x,occupied=False),index=4).episode)
        self.assertNotEqual(to_demand_episode(x,index=4).demand,
                            to_demand_episode(replace(x,occupied=False),index=4).demand)

    def test_10_label_only_changes_C_reference_and_reward(self):
        x=DatasetRow('2020-01-01 00:00:00',250.,700.,True)
        a=observe_closed_episode(to_demand_episode(x,index=0),'temporal')
        b=observe_closed_episode(to_demand_episode(replace(x,occupied=False),index=0),'temporal')
        self.assertEqual(a.c_forward_ticks,b.c_forward_ticks)
        self.assertEqual((a.local_reward,b.local_reward),(1,-1))

    def test_11_fixed_timestamp_mapping_precedes_future_reference(self):
        x=DatasetRow('2020-01-01 00:00:00',250.,700.,True)
        ep=to_demand_episode(x,index=0)
        self.assertEqual(ep.episode.inputs,((10,0),(11,2)))
        self.assertEqual(observe_closed_episode(ep,'temporal').closure_tick,16)

    def test_12_downsample_uses_only_indices(self):
        rows,_=self.rows()
        flipped=tuple(replace(r,occupied=not r.occupied) for r in rows)
        self.assertEqual([r.stamp for r in downsample(rows,60)],
                         [r.stamp for r in downsample(flipped,60)])

    def test_13_schedule_balanced(self):
        actions=balanced_schedule(180,seed=357052)
        self.assertEqual({c:actions.count(c) for c in CANDIDATES},{c:60 for c in CANDIDATES})

    def test_14_schedule_seed_reproducible(self):
        self.assertEqual(balanced_schedule(180,seed=357052),balanced_schedule(180,seed=357052))

    def test_15_schedule_bad_horizon_rejected(self):
        with self.assertRaises(ValueError):balanced_schedule(5,seed=0)

    def test_16_pilot_one_arm_uses_A1b_and_selects_solution(self):
        rows,sha=self.rows()
        result=pilot(rows,sha)
        self.assertEqual(result['learner']['selected'],'temporal')
        self.assertEqual(sum(result['learner']['chosen_counts'].values()),180)
        self.assertEqual(result['program_adoptions'],0)

    def test_17_pilot_reference_deterministic(self):
        rows,sha=self.rows()
        self.assertEqual(canonical(pilot(rows,sha)),canonical(pilot(rows,sha)))

    def test_18_public_evaluation_does_not_claim_blind(self):
        rows,sha=self.rows(); certificate=pilot(rows,sha)
        ev,evalsha=read_uci(self.test,expected_filename='datatest2.txt')
        result=evaluate(ev,evalsha,certificate)
        self.assertEqual(result['status'],'PUBLIC_UCI_EVALUATION_NOT_BLIND')
        self.assertEqual(result['selected_policy_frozen'],'temporal')
        self.assertEqual(result['selected_error'],0)
        self.assertFalse(result['blind_holdout_claim'])

    def test_19_better_than_baseline_on_engineered_fixture_not_independent(self):
        rows,sha=self.rows();cert=pilot(rows,sha)
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        m=evaluate(ev,evsha,cert)
        self.assertGreater(m['baseline_error'],m['selected_error'])
        self.assertFalse(m['endogenous_BV_reward_established'])

    def test_20_reverse_world_still_audited_and_not_hidden(self):
        rows,sha=self.rows();cert=pilot(rows,sha)
        make_source(self.test,60,offset=300,wrong=True)
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        m=evaluate(ev,evsha,cert)
        self.assertGreater(m['selected_error'],0)

    def test_21_same_train_test_bytes_rejected(self):
        rows,sha=self.rows();cert=pilot(rows,sha)
        with self.assertRaises(ValueError):evaluate(rows,sha,cert)

    def test_22_overlapping_temporal_test_rejected(self):
        rows,sha=self.rows();cert=pilot(rows,sha)
        make_source(self.test,60,offset=120)
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaises(ValueError):evaluate(ev,evsha,cert)

    def test_23_changed_pilot_winner_rejected(self):
        rows,sha=self.rows();cert=pilot(rows,sha)
        cert['learner']['selected']='silent'
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaises(ValueError):evaluate(ev,evsha,cert)

    def test_24_raised_forged_reward_rejected(self):
        rows,sha=self.rows();cert=pilot(rows,sha)
        cert['learner']['reward_sums']['silent']=1000
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaises(ValueError):evaluate(ev,evsha,cert)

    def test_25_unsupported_candidate_rejected(self):
        rows,sha=self.rows(); cert=pilot(rows,sha)
        cert['learner']['selected']='unknown'
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaises(ValueError):evaluate(ev,evsha,cert)

    def test_26_forbidden_policy_adoption_rejected(self):
        rows,sha=self.rows(); cert=pilot(rows,sha)
        cert['program_adoptions']=1
        ev,evsha=read_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaises(ValueError):evaluate(ev,evsha,cert)

    def test_27_cli_selftest_reference_canonical(self):
        ref=(ROOT/'docs/spk-v5-t3a-selftest-reference.json').read_bytes()
        path=self.root/'result.json'
        run=subprocess.run([sys.executable,str(RUNNER),'selftest','--out',str(path)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(path.read_bytes(),ref)

    def test_28_cli_create_only(self):
        path=self.root/'already.json';path.write_text('do not overwrite')
        run=subprocess.run([sys.executable,str(RUNNER),'selftest','--out',str(path)],cwd=ROOT,capture_output=True)
        self.assertNotEqual(run.returncode,0)
        self.assertEqual(path.read_text(),'do not overwrite')

    def test_29_cli_reject_repo_output(self):
        path=ROOT/'docs/unsafe-t3a-report.json'
        run=subprocess.run([sys.executable,str(RUNNER),'selftest','--out',str(path)],cwd=ROOT,capture_output=True)
        self.assertNotEqual(run.returncode,0)
        self.assertFalse(path.exists())

    def test_30_cli_pilot_then_pinned_evaluation(self):
        certificate=self.root/'pilot.json';evalout=self.root/'eval.json'
        a=subprocess.run([sys.executable,str(RUNNER),'pilot','--data',str(self.train),'--out',str(certificate)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(a.returncode,0,a.stderr)
        pin=sha_bytes(certificate.read_bytes())
        b=subprocess.run([sys.executable,str(RUNNER),'evaluate','--data',str(self.test),'--pilot',str(certificate),'--pilot-sha256',pin,'--out',str(evalout)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(b.returncode,0,b.stderr)
        self.assertEqual(json.loads(evalout.read_text())['selected_error'],0)

    def test_31_cli_wrong_pilot_digest_refused(self):
        certificate=self.root/'pilot.json';certificate.write_text('{}\n')
        output=self.root/'denied.json'
        b=subprocess.run([sys.executable,str(RUNNER),'evaluate','--data',str(self.test),'--pilot',str(certificate),'--pilot-sha256','0'*64,'--out',str(output)],cwd=ROOT,capture_output=True)
        self.assertNotEqual(b.returncode,0)
        self.assertFalse(output.exists())

    def test_32_cli_symlinked_pilot_refused(self):
        certificate=self.root/'pilot.json';certificate.write_text('{}\n')
        alias=self.root/'alias.json';alias.symlink_to(certificate)
        b=subprocess.run([sys.executable,str(RUNNER),'evaluate','--data',str(self.test),'--pilot',str(alias),'--pilot-sha256',sha_bytes(certificate.read_bytes()),'--out',str(self.root/'denied.json')],cwd=ROOT,capture_output=True)
        self.assertNotEqual(b.returncode,0)

    def test_33_cli_source_sha_drift_refused(self):
        # The validator itself is source-pinned; simulate a temporarily wrong pin.
        from unittest.mock import patch
        from search.spk_v5_t3a_external_uci import pins_ok
        original=(ROOT/'docs/spk-v5-t3a-manifest.json').read_text()
        m=json.loads(original);first=next(iter(m['pins_sha256']));m['pins_sha256'][first]='0'*64
        with patch('pathlib.Path.read_text',side_effect=lambda *a,**k:json.dumps(m)):
            with self.assertRaises(ValueError):pins_ok()

    def test_34_no_frozen_repo_files_changed(self):
        m=json.loads((ROOT/'docs/spk-v5-t3a-manifest.json').read_text())
        for rel,expected in m['pins_sha256'].items():
            f=ROOT/rel
            self.assertFalse(f.is_symlink(),rel)
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),expected,rel)
        self.assertIn('spk_backvalidation_v0/live_dual_scheduler_v0e.py',m['pins_sha256'])

    def test_35_selftest_outcome_no_false_external_claim(self):
        data=json.loads((ROOT/'docs/spk-v5-t3a-selftest-reference.json').read_text())
        self.assertTrue(data['selftest_labels_engineered'])
        self.assertTrue(data['selftest_no_external_data_executed'])
        self.assertFalse(data['blind_holdout_claim'])


if __name__=='__main__':unittest.main()
