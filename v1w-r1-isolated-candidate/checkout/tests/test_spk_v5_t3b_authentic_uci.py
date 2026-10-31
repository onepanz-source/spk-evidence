"""T3b independent UCI row-index parser and unchanged T3a engine checks."""
from __future__ import annotations

import csv
from datetime import datetime,timedelta
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci
from spk_v5_research.island_external_task_v5t3a import (
    FEATURE_FIELDS, pilot, evaluate, to_demand_episode, canonical,
)

ROOT=Path(__file__).resolve().parent.parent
SCRIPT=ROOT/'search/spk_v5_t3b_authentic_uci.py'


def indexed_csv(path:Path,n:int,start:int=0,first_id:int=1,flip_labels:bool=False):
    with path.open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(FEATURE_FIELDS)
        for i in range(n):
            dt=datetime(2020,1,1)+timedelta(minutes=start+i)
            bright=i%4 in (0,1)
            co2=i%4 in (0,2)
            target=int(bright and co2)
            if flip_labels:target=1-target
            w.writerow([first_id+i,dt.strftime('%Y-%m-%d %H:%M:%S'),22,44,
                        250 if bright else 20,700 if co2 else 480,0.006,target])


class TestAuthenticUCIIndexedCSV(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='spk-t3b-')
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.train=self.folder/'datatraining.txt'
        self.test=self.folder/'datatest2.txt'
        indexed_csv(self.train,180)
        indexed_csv(self.test,60,start=300)

    def parsed(self):
        return read_authentic_uci(self.train,expected_filename='datatraining.txt')

    def modify(self, edit):
        with self.train.open() as f:records=list(csv.reader(f))
        edit(records)
        with self.train.open('w',newline='') as f:csv.writer(f).writerows(records)

    def test_01_original_8_cell_rows_and_exact_raw_hash(self):
        rows,h=self.parsed()
        self.assertEqual(len(rows),180)
        self.assertEqual(h,sha256(self.train.read_bytes()).hexdigest())

    def test_02_id_not_neuron_input(self):
        rows,_=self.parsed()
        ep=to_demand_episode(rows[0],index=0)
        self.assertEqual(ep.episode.inputs,((10,0),(11,2)))
        self.assertNotIn(1,[e[1] for e in ep.episode.inputs])

    def test_03_source_id_may_start_140(self):
        indexed_csv(self.train,180,first_id=140)
        self.assertEqual(len(self.parsed()[0]),180)

    def test_04_skipped_id_rejected(self):
        self.modify(lambda r:r[9].__setitem__(0,'1000'))
        with self.assertRaisesRegex(ValueError,'ID'):self.parsed()

    def test_05_duplicate_id_rejected(self):
        self.modify(lambda r:r[9].__setitem__(0,r[8][0]))
        with self.assertRaisesRegex(ValueError,'ID'):self.parsed()

    def test_06_malformed_7_cell_row_rejected(self):
        self.modify(lambda r:r[4].pop())
        with self.assertRaisesRegex(ValueError,'8 cells'):self.parsed()

    def test_07_malformed_9_cell_row_rejected(self):
        self.modify(lambda r:r[4].append('extraneous'))
        with self.assertRaisesRegex(ValueError,'8 cells'):self.parsed()

    def test_08_nonmonotone_stamp_rejected(self):
        self.modify(lambda r:r[4].__setitem__(1,r[3][1]))
        with self.assertRaisesRegex(ValueError,'timestamp'):self.parsed()

    def test_09_bad_occupancy_rejected(self):
        self.modify(lambda r:r[4].__setitem__(7,'2'))
        with self.assertRaisesRegex(ValueError,'occupancy'):self.parsed()

    def test_10_nan_sensor_rejected(self):
        self.modify(lambda r:r[4].__setitem__(5,'nan'))
        with self.assertRaisesRegex(ValueError,'nonfinite'):self.parsed()

    def test_11_wrong_header_rejected(self):
        self.modify(lambda r:r[0].insert(0,'index'))
        with self.assertRaisesRegex(ValueError,'header'):self.parsed()

    def test_12_wrong_dataset_basename_rejected(self):
        with self.assertRaisesRegex(ValueError,'unsafe'):
            read_authentic_uci(self.train,expected_filename='datatest2.txt')

    def test_13_symlink_rejected(self):
        link=self.folder/'other'/'datatraining.txt'
        link.parent.mkdir()
        link.symlink_to(self.train)
        with self.assertRaisesRegex(ValueError,'unsafe'):
            read_authentic_uci(link,expected_filename='datatraining.txt')

    def test_14_real_A1b_pilot_and_public_evaluation(self):
        rows,raw=self.parsed()
        cert=pilot(rows,raw)
        ev,h=read_authentic_uci(self.test,expected_filename='datatest2.txt')
        result=evaluate(ev,h,cert)
        self.assertEqual(cert['learner']['selected'],'temporal')
        self.assertEqual(result['selected_error'],0)
        self.assertFalse(result['blind_holdout_claim'])

    def test_15_temporal_overlap_rejected(self):
        rows,raw=self.parsed();cert=pilot(rows,raw)
        indexed_csv(self.test,60,start=120)
        ev,h=read_authentic_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaisesRegex(ValueError,'temporally'):
            evaluate(ev,h,cert)

    def test_16_cli_canonical_raw_sha_and_immutable_pilot(self):
        out1=self.folder/'pilot.json';out2=self.folder/'eval.json'
        p=subprocess.run([sys.executable,str(SCRIPT),'pilot','--data',str(self.train),'--out',str(out1)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(out1.read_bytes())
        self.assertEqual(data['source_sha256'],sha256(self.train.read_bytes()).hexdigest())
        self.assertFalse(data['source_id_sent_to_neuron'])
        pin=sha256(out1.read_bytes()).hexdigest()
        q=subprocess.run([sys.executable,str(SCRIPT),'evaluate','--data',str(self.test),'--pilot',str(out1),'--pilot-sha256',pin,'--out',str(out2)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(q.returncode,0,q.stderr)
        self.assertEqual(json.loads(out2.read_bytes())['selected_error'],0)
        self.assertEqual(json.loads(out2.read_bytes())['pilot_certificate_sha256'],pin)

    def test_17_cli_bad_pilot_sha_and_no_output(self):
        p=self.folder/'pilot.json';p.write_text('{}\n')
        out=self.folder/'eval.json'
        q=subprocess.run([sys.executable,str(SCRIPT),'evaluate','--data',str(self.test),'--pilot',str(p),'--pilot-sha256','0'*64,'--out',str(out)],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(q.returncode,0)
        self.assertFalse(out.exists())

    def test_18_cli_existing_output_not_overwritten(self):
        dest=self.folder/'occupied.json';dest.write_text('original')
        p=subprocess.run([sys.executable,str(SCRIPT),'pilot','--data',str(self.train),'--out',str(dest)],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(dest.read_text(),'original')

    def test_19_bad_future_pilot_claim_is_rejected(self):
        rows,raw=self.parsed();cert=pilot(rows,raw)
        cert['learner']['selected']='silent'
        ev,h=read_authentic_uci(self.test,expected_filename='datatest2.txt')
        with self.assertRaises(ValueError):evaluate(ev,h,cert)

    def test_20_label_changes_only_reward_not_inputs(self):
        rows,_=self.parsed()
        events=[to_demand_episode(x,index=i).episode.inputs for i,x in enumerate(rows)]
        indexed_csv(self.train,180,flip_labels=True)
        changed,_=self.parsed()
        events2=[to_demand_episode(x,index=i).episode.inputs for i,x in enumerate(changed)]
        self.assertEqual(events,events2)
        self.assertNotEqual([x.occupied for x in rows],[x.occupied for x in changed])


if __name__=='__main__':unittest.main()
