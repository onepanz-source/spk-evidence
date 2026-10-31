import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 't3uvw.py'
SPEC = importlib.util.spec_from_file_location('t3uvw', MODULE)
t = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(t)


def fixture():
    runs = []
    for seed, admitted, rej, discard in ((11,120,0,0),(11,86,29,5),(29,120,0,0),
                                        (29,85,31,4),(47,120,0,0),(47,86,31,3)):
        stressed = admitted != 120
        runs.append({'seed': seed, 'stress': stressed, 'episode_digest': 'a'*64,
                     'observations':{'decisions':120,'source_admitted':admitted,'C_proxy_correct':105},
                     'registry':{'updates':admitted,'source_rejected':rej,'discards':discard,
                                 'pending':0,'head':'b'*64,'weights_sha256':'c'*64}})
    return {
        'schema': t.REF_SCHEMA, 'status': t.REF_STATUS,
        'C_verdict_table': {'cases':180,'positive_verdicts':36,'negative_verdicts':36,
                            'counts':{'REJECT_NO_UPDATE':138,'SHADOW_SOURCE_REPLAY_ELIGIBLE':42},
                            'total_charged_native_source_grants':144},
        'online_replay_runs':runs,'total_online_episodes':720,
        'total_source_admitted':617,'total_credited_updates':617,
        'claims_excluded':[
            'dual BV-v0e source invocations per episode, not single native BV semantic channel',
            'host selects terminal observer after reading both passes: no native dynamic sign routing',
            'C CO2 sensor threshold is host-prepared, not authenticated',
            'hash chain is not a signature, no hardware attestation',
        ]}


class T3UVWTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in (*t.PINS, *t.ADDITIONAL_PATHS):
            p=self.root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('fixture-for-' + name)
        prior_validator = Path(__file__).resolve().parents[3] / 'research/spk_v5_t3rst/src/spk_t3rst.py'
        if not prior_validator.is_file():
            raise RuntimeError('T3RST predecessor validator must be present; no mock fallback')
        self.root.joinpath('research/spk_v5_t3rst/src/spk_t3rst.py').write_bytes(
            prior_validator.read_bytes())
        self.report=fixture()
        self.pins={name:t.sha_file(self.root/name) for name in t.PINS}
        self.patch=patch.dict(t.PINS,self.pins,clear=True)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def valid(self):
        return t.validate_report(self.report,self.root)

    def test_valid_reference_report(self):
        self.assertEqual(self.valid()['episodes'],720)
    def test_summary_credited(self):
        self.assertEqual(self.valid()['shadow_updates'],617)
    def test_snapshot_captures_expected_count(self):
        self.assertEqual(len(t.snapshot(self.root)),7)
    def test_pins_match(self):
        t.verify_pins(t.snapshot(self.root))
    def test_frozen_pin_tamper_rejected(self):
        x=t.snapshot(self.root); x[next(iter(t.PINS))]='0'*64
        with self.assertRaisesRegex(t.GateError,'FROZEN_PIN_MISMATCH'):t.verify_pins(x)
    def test_missing_source_rejected(self):
        (self.root/next(iter(t.PINS))).unlink()
        with self.assertRaisesRegex(t.GateError,'REQUIRED_SOURCE_ABSENT'):t.snapshot(self.root)
    def test_missing_original_gate_rejected(self):
        (self.root/t.ADDITIONAL_PATHS[0]).unlink()
        with self.assertRaisesRegex(t.GateError,'REQUIRED_SOURCE_ABSENT'):t.snapshot(self.root)
    def test_bad_report_schema_rejected(self):
        self.report['schema']='different'
        with self.assertRaises(Exception):self.valid()
    def test_bad_report_status_rejected(self):
        self.report['status']='NATIVE_LEARNING'
        with self.assertRaises(Exception):self.valid()
    def test_duplicate_seed_stress_rejected(self):
        self.report['online_replay_runs'][1]['stress']=False
        with self.assertRaises(Exception):self.valid()
    def test_admitted_mismatch_rejected(self):
        self.report['online_replay_runs'][1]['observations']['source_admitted']+=1
        with self.assertRaises(Exception):self.valid()
    def test_broken_conservation_rejected(self):
        self.report['online_replay_runs'][1]['registry']['discards']+=1
        with self.assertRaises(Exception):self.valid()
    def test_break_total_rejected(self):
        self.report['total_credited_updates']+=1
        with self.assertRaises(Exception):self.valid()
    def test_excluded_undisclosed_rejected(self):
        self.report['claims_excluded']=[]
        with self.assertRaises(Exception):self.valid()
    def test_pair_identical_json(self):
        comp=t.compare_runs(self.report,copy.deepcopy(self.report),'a'*64,'a'*64)
        self.assertTrue(comp['exact_json_equal'])
    def test_pair_byte_difference_formatting_recorded(self):
        comp=t.compare_runs(self.report,copy.deepcopy(self.report),'a'*64,'b'*64)
        self.assertFalse(comp['byte_identical'])
    def test_pair_semantic_difference_rejected(self):
        b=copy.deepcopy(self.report);b['total_credited_updates']=616
        with self.assertRaisesRegex(t.GateError,'NONDETERMINISTIC'):t.compare_runs(self.report,b,'a'*64,'b'*64)
    def test_canonical_hash_key_order_independent(self):
        self.assertEqual(t.canonical_sha({'x':1,'a':2}),t.canonical_sha({'a':2,'x':1}))
    def test_build_result_keeps_nonpromotion(self):
        before=t.snapshot(self.root)
        result=t.build_result(self.root,before,before,self.report,copy.deepcopy(self.report),'a'*64,'a'*64,
                              [self.root/'o1.json',self.root/'o2.json'])
        self.assertFalse(result['promotion_allowed'])
        self.assertFalse(result['W_causal_boundary']['native_semantic_BV_proven'])
        self.assertEqual(result['V_original_gate']['invocations'],2)
    def test_build_result_refuses_mutated_source(self):
        before=t.snapshot(self.root)
        after=before.copy();after[next(iter(t.PINS))]='f'*64
        with self.assertRaisesRegex(t.GateError,'SOURCE_CHANGED'):t.build_result(
            self.root,before,after,self.report,self.report,'a'*64,'a'*64,[])
    def test_build_result_refuses_missing_host_disclosure(self):
        before=t.snapshot(self.root)
        self.report['claims_excluded']=[x for x in self.report['claims_excluded'] if 'host selects' not in x]
        with self.assertRaisesRegex(t.GateError,'HOST_SELECTION_DISCLOSURE_MISSING'):t.build_result(
            self.root,before,before,self.report,self.report,'a'*64,'a'*64,[])
    def test_subprocess_gate_zero(self):
        gate=self.root/t.ADDITIONAL_PATHS[0]
        gate.write_text('#!/bin/bash\nprintf "{}\\n" > "$1"\n')
        t.run_original_gate(self.root,self.root/'out.json',self.root/'run.log')
        self.assertEqual((self.root/'out.json').read_text(),'{}\n')
    def test_subprocess_nonzero_fails(self):
        (self.root/t.ADDITIONAL_PATHS[0]).write_text('#!/bin/bash\nexit 4\n')
        with self.assertRaisesRegex(t.GateError,'EXIT_4'):t.run_original_gate(
            self.root,self.root/'out.json',self.root/'run.log')
    def test_subprocess_without_report_fails(self):
        (self.root/t.ADDITIONAL_PATHS[0]).write_text('#!/bin/bash\nexit 0\n')
        with self.assertRaisesRegex(t.GateError,'REPORT_MISSING'):t.run_original_gate(
            self.root,self.root/'out.json',self.root/'run.log')
    def test_main_two_actual_gate_calls_with_fake_producer(self):
        (self.root/'report_fixture.json').write_text(json.dumps(self.report))
        gate=self.root/t.ADDITIONAL_PATHS[0]
        gate.write_text('#!/bin/bash\ncp "$PWD/report_fixture.json" "$1"\n')
        out=self.root/'audit.json'
        with patch.object(sys,'argv',['t3uvw','--repo',str(self.root),'--output',str(out)]):
            self.assertEqual(t.main(),0)
        r=json.loads(out.read_text())
        self.assertEqual(r['V_original_gate']['invocations'],2)
        self.assertTrue(r['V_original_gate']['comparison']['byte_identical'])
        self.assertFalse(r['promotion_allowed'])
        self.assertTrue((self.root/'audit-original-1.json').exists())
        self.assertTrue((self.root/'audit-original-2.json').exists())

    def test_main_source_hash_mismatch_blocks_gate_before_exec(self):
        (self.root/next(iter(t.PINS))).write_text('tampered')
        with patch.object(sys,'argv',['t3uvw','--repo',str(self.root),'--output',str(self.root/'audit.json')]):
            with self.assertRaisesRegex(t.GateError,'FROZEN_PIN_MISMATCH'):t.main()
        self.assertFalse((self.root/'audit.json').exists())

    def test_main_producer_mutation_detected(self):
        first=next(iter(t.PINS))
        gate=self.root/t.ADDITIONAL_PATHS[0]
        gate.write_text(f'#!/bin/bash\necho tampered >> "{self.root/first}"\ncp "$PWD/report_fixture.json" "$1"\n')
        (self.root/'report_fixture.json').write_text(json.dumps(self.report))
        with patch.object(sys,'argv',['t3uvw','--repo',str(self.root),'--output',str(self.root/'audit.json')]):
            with self.assertRaisesRegex(t.GateError,'SOURCE_MUTATED_DURING_RUN'):t.main()

    def test_json_roundtrip(self):
        self.assertEqual(json.loads(json.dumps(self.report)),self.report)
    def test_sha_integrity(self):
        self.assertEqual(t.sha_bytes(b''),hashlib.sha256(b'').hexdigest())

if __name__=='__main__':unittest.main()
