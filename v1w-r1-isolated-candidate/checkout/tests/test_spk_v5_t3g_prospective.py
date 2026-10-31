"""Adversarial and causal V5-T3g prospective protocol tests, artificial QA ONLY."""
from __future__ import annotations
import csv
from datetime import datetime,timedelta,timezone
import hashlib,json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from spk_v5_research.island_external_task_v5t3a import canonical
from spk_v5_research.island_prospective_validation_v5t3g import (
    read_features,read_labels,precommit,evaluate,admitted_pairs,exact_one_sided_sign_p,
    STATUS_PASS,STATUS_FAIL,STATUS_INSUFFICIENT,SCHEMA,COMMIT_SCHEMA,
)
from search.spk_v5_t3g_prospective import read_commit,pins_ok


def qa_fixture(folder:Path,mode='better',days=10):
    """Deliberately engineered QA fixture, never used as independent evidence."""
    feature=folder/'features.csv'; labels=folder/'labels.csv'
    start=datetime(2026,11,1,tzinfo=timezone.utc)
    with feature.open('w',newline='') as ff,labels.open('w',newline='') as ll:
        f=csv.writer(ff,lineterminator='\n');l=csv.writer(ll,lineterminator='\n')
        f.writerow(['timestamp_utc','light_lux']);l.writerow(['timestamp_utc','occupied'])
        for day in range(days):
            for minute in range(62):
                t=(start+timedelta(days=day,minutes=minute)).strftime('%Y-%m-%dT%H:%M:%SZ')
                lit=int(1<=minute<=12)
                f.writerow([t,300 if lit else 5])
                occupancy = (minute in range(2,13)) if mode=='better' else ((minute in range(1,13)) if mode=='worse' else (minute in range(2,13) and day < 2))
                l.writerow([t,int(occupancy)])
    return feature,labels

class T3gProspective(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='spk-v5-t3g-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.features,self.labels=qa_fixture(self.root)
        self.rows,self.source_sha=read_features(self.features)
        self.truth,self.label_sha=read_labels(self.labels)
        self.proto=hashlib.sha256(Path('docs/spk-v5-t3g-protocol.json').read_bytes()).hexdigest()
        self.cert=precommit(self.rows,self.source_sha,'synthetic-qa-only',self.proto)

    def score(self,**overrides):
        return evaluate(overrides.get('rows',self.rows),overrides.get('source_sha',self.source_sha),
                        overrides.get('labels',self.truth),overrides.get('labels_sha',self.label_sha),
                        overrides.get('commit',self.cert),overrides.get('protocol_sha',self.proto))
    def test_pins(self):pins_ok()
    def test_protocol_status_success_fixture(self):
        x=self.score();self.assertEqual(x['status'],STATUS_PASS)
        self.assertEqual(x['primary_occupied_days']['qualified_days'],10)
        self.assertEqual(x['primary_occupied_days']['wins'],10)
        self.assertEqual(x['primary_occupied_days']['fn_rate_uplift'],0)
        self.assertFalse(x['independent_blind_holdout'])
    def test_reverse_label_outcome_without_changing_neuron_decisions(self):
        f,l=qa_fixture(self.root,'worse')
        truth,digest=read_labels(l)
        x=self.score(labels=truth,labels_sha=digest)
        self.assertEqual(x['status'],STATUS_FAIL)
        self.assertEqual(x['primary_occupied_days']['losses'],10)
        self.assertEqual(x['A1b_four_pattern_truth_table_verified'],self.score()['A1b_four_pattern_truth_table_verified'])
    def test_insufficient_occupied_days(self):
        f,l=qa_fixture(self.root,'too-few')
        truth,digest=read_labels(l)
        x=self.score(labels=truth,labels_sha=digest)
        self.assertEqual(x['status'],STATUS_INSUFFICIENT)
        self.assertEqual(x['primary_occupied_days']['qualified_days'],2)
    def test_success_not_blind_or_native(self):
        x=self.score();self.assertFalse(x['source_provenance_independently_attested'])
        self.assertTrue(any('no native' in line.lower() for line in x['claims_excluded']))
        self.assertEqual(x['frozen_candidate'],'persist')
    def test_no_future_labels_in_precommit(self):
        a=self.cert
        truth,_=read_labels(self.labels)
        changed={k: not v for k,v in truth.items()}
        self.assertEqual(a,precommit(self.rows,self.source_sha,'synthetic-qa-only',self.proto))
        self.assertNotEqual(self.score()['aggregate'],self.score(labels=changed)['aggregate'])
    def test_precommit_reconstructed_source_sha(self):
        bad=dict(self.cert,unlabelled_source_sha256='1'*64)
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_precommit_forged_protocol_sha(self):
        bad=dict(self.cert,protocol_sha256='1'*64)
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_precommit_forged_rows(self):
        bad=dict(self.cert,rows=self.cert['rows']+1)
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_precommit_forged_label_visibility(self):
        bad=dict(self.cert,label_bytes_seen_during_precommit=True)
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_precommit_claim_upgrade(self):
        bad=dict(self.cert,source_provenance_independently_attested=True)
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_precommit_wrong_candidate(self):
        bad=dict(self.cert,candidate_frozen='rise')
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_precommit_extra_field(self):
        bad=dict(self.cert);bad['labels_cached']=True
        with self.assertRaises(ValueError):self.score(commit=bad)
    def test_label_timestamp_alignment_exact(self):
        truth=dict(self.truth);truth.pop(next(iter(truth)))
        with self.assertRaises(ValueError):self.score(labels=truth)
    def test_feature_input_no_occupancy_column(self):
        self.features.write_text('timestamp_utc,light_lux,occupied\n')
        with self.assertRaises(ValueError):read_features(self.features)
    def test_feature_row_extra_field(self):
        self.features.write_text('timestamp_utc,light_lux\n2026-11-01T00:00:00Z,300,1\n')
        with self.assertRaises(ValueError):read_features(self.features)
    def test_source_replayed_2015_is_rejected(self):
        text=self.features.read_text().replace('2026-11','2015-02')
        self.features.write_text(text)
        with self.assertRaises(ValueError):read_features(self.features)
    def test_duplicate_source_timestamp(self):
        text=self.features.read_text().splitlines()
        text[2]=text[1]
        self.features.write_text('\n'.join(text)+'\n')
        with self.assertRaises(ValueError):read_features(self.features)
    def test_nonfinite_and_negative_light(self):
        for x in ('nan','inf','-1','200001'):
            with self.subTest(x=x):
                original=self.features.read_text();self.features.write_text(original.replace(',300\n',','+x+'\n',1))
                with self.assertRaises(ValueError):read_features(self.features)
                self.features.write_text(original)
    def test_labels_are_strict_binary(self):
        for x in ('2','True','','0,1'):
            with self.subTest(x=x):
                raw=self.labels.read_text();self.labels.write_text(raw.replace(',1\n',','+x+'\n',1))
                with self.assertRaises(ValueError):read_labels(self.labels)
                self.labels.write_text(raw)
    def test_labels_duplicate_timestamp(self):
        lines=self.labels.read_text().splitlines();lines[2]=lines[1]
        self.labels.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(ValueError):read_labels(self.labels)
    def test_wrong_source_id(self):
        with self.assertRaises(ValueError):precommit(self.rows,self.source_sha,' /tmp',self.proto)
    def test_not_enough_physical_days(self):
        with self.assertRaises(ValueError):precommit(self.rows[:(62*5)],self.source_sha,'synthetic-qa-only',self.proto)
    def test_source_gap_not_fabricated(self):
        days=admitted_pairs(self.rows)
        self.assertEqual(len(days),10)
        self.assertTrue(all(len(x)==61 for x in days.values()))
    def test_report_day_means_not_aggregate_accuracy(self):
        x=self.score()
        self.assertEqual(x['primary_occupied_days']['wins'],10)
        self.assertEqual(x['primary_occupied_days']['mean_day_error_rate_improvement'],round(1/61,9))
    def test_sign_test_exact(self):
        self.assertEqual(exact_one_sided_sign_p(10,0),round(1/1024,10))
        self.assertEqual(exact_one_sided_sign_p(0,0),None)
        self.assertEqual(exact_one_sided_sign_p(0,10),1.0)
    def test_read_commit_sha_replay_and_canonical(self):
        out=self.root/'precommit.json';out.write_bytes(canonical(self.cert))
        self.assertEqual(read_commit(out,hashlib.sha256(out.read_bytes()).hexdigest()),self.cert)
        with self.assertRaises(ValueError):read_commit(out,'0'*64)
        out.write_bytes(b'{"schema": "not canonical"}\n')
        with self.assertRaises(ValueError):read_commit(out,hashlib.sha256(out.read_bytes()).hexdigest())
    def test_read_commit_symlink(self):
        p=self.root/'orig';p.write_bytes(canonical(self.cert));alias=self.root/'alias';alias.symlink_to(p)
        with self.assertRaises(ValueError):read_commit(alias,hashlib.sha256(p.read_bytes()).hexdigest())
    def test_engineered_results_not_external_provenance(self):
        x=self.score()
        self.assertTrue(any('operator attests' in s for s in x['claims_excluded']))
        self.assertEqual(x['precommit_metadata']['claim'],'FEATURE_COMMIT_ONLY_NOT_BLIND_NOT_INDEPENDENT_CUSTODY')

if __name__=='__main__':unittest.main()
