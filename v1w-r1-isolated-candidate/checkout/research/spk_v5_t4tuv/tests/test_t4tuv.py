import ast
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from research.spk_v5_t4tuv import t4tuv as t
from research.spk_v5_t4qrs import t4qrs as q
from research.spk_v5_t4nop import t4nop
from research.spk_v5_t4ghi import t4ghi

ROOT=Path(__file__).resolve().parents[3]
class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.ref,cls.ghi,cls.old=t.references(ROOT)
    def test_old_report_pinned(self):
        self.assertEqual(q.sha(ROOT/'research/spk_v5_t4tuv/reference/t4qrs-process-receiver-port.json'),t.QRS_REPORT_SHA)
    def test_ghi_pinned(self):
        self.assertEqual(q.sha(ROOT/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json'),t.GHI_REPORT_SHA)
    def test_t4nop_pinned(self):self.assertEqual(q.REF_SHA,'32fe39cdd994c02b653e88f99887d989539ba32a9910b805884c7ab439d9b974')
    def test_old_shows_180(self):self.assertEqual(self.old['producer']['original_BV_calls'],180)
    def test_old_has_24(self):self.assertEqual(self.old['receiver']['committed_count'],24)
    def test_old_receiver_ledger_pinned(self):self.assertEqual(self.old['receiver']['ledger_sha256'],'f5d762cf9607ceb1ca6ba286472d0597535949a67e651b8047503c2940fd30a2')
    def test_old_native_denied(self):self.assertIs(self.old['C_neuron_origin_authenticated'],False)
    def test_missing_fields(self):self.assertEqual(set(self.ref['O_missing_semantic_contract_fields']),{'C_emission_id','authenticator','causal_parent_id','semantic_sign','source_identity'})
    def test_all_rows_cached_equal(self):
        for i,(x,y) in enumerate(zip(self.ref['O_rows'],self.ghi['H_rows'])):
            self.assertEqual(x['source_sha256'],y['source_sha256'],i)
            self.assertEqual(x['observed_sign'],y['C_sign_candidate_from_same_source_forward_output'],i)
    def test_cached_guard_partition(self):
        self.assertEqual(sum(x['research_classification']==q.ELIGIBLE for x in self.ref['O_rows']),24)
    def test_cached_sign_balance(self):
        selected=[x for x in self.ref['O_rows'] if x['research_classification']==q.ELIGIBLE]
        self.assertEqual(sum(x['observed_sign']==1 for x in selected),12)
        self.assertEqual(sum(x['observed_sign']==-1 for x in selected),12)
    def test_seam_source_once(self):
        s=t.source_seam(ROOT)
        self.assertIn('execute_live_v0e',s['research/spk_v5_t4ghi/t4ghi.py']['call_sites'])
    def test_seam_host_adapter(self):
        s=t.source_seam(ROOT)
        self.assertEqual(len(s['research/spk_v5_t4qrs/t4qrs.py']['call_sites']),4)
    def test_seam_source_hash(self):
        s=t.source_seam(ROOT)
        self.assertEqual(s['research/spk_v5_t4qrs/t4qrs.py']['source_sha256'],q.sha(ROOT/'research/spk_v5_t4qrs/t4qrs.py'))
    def test_schema_research_only(self):self.assertTrue(t.SCHEMA.endswith('/research-v0'))
    def test_status_explicit_limit(self):self.assertIn('NO_C_ORIGIN',t.STATUS)

class NativeDenialTests(unittest.TestCase):
    def test_empty_denied(self):
        with self.assertRaisesRegex(t.GateError,t.NO_SOURCE):t.native_semantic_claim({})
    def test_forged_label_denied(self):
        with self.assertRaisesRegex(t.GateError,t.NO_SOURCE):t.native_semantic_claim({'source_identity':'C','authenticator':'signed','semantic_sign':1})
    def test_forged_native_flag_denied(self):
        with self.assertRaisesRegex(t.GateError,t.NO_SOURCE):t.native_semantic_claim({'native_C_authored':True})
    def test_forged_causal_parent_denied(self):
        with self.assertRaisesRegex(t.GateError,t.NO_SOURCE):t.native_semantic_claim({'causal_parent_id':'p','C_emission_id':'c','semantic_sign':-1})
    def test_nonnumeric_sign_denied(self):
        with self.assertRaisesRegex(t.GateError,t.NO_SOURCE):t.native_semantic_claim({'semantic_sign':'positive'})
    def test_null_denied(self):
        with self.assertRaisesRegex(t.GateError,'NATIVE_CANDIDATE_INVALID'):t.native_semantic_claim(None)
    def test_array_denied(self):
        with self.assertRaisesRegex(t.GateError,'NATIVE_CANDIDATE_INVALID'):t.native_semantic_claim([])
    def test_true_denied(self):
        with self.assertRaisesRegex(t.GateError,'NATIVE_CANDIDATE_INVALID'):t.native_semantic_claim(True)

class OfflineCounterexampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.ref,cls.ghi,cls.old=t.references(ROOT)
    def run_cache(self,base):
        t.cached_producer(ROOT,base)
        q.relay(base)
        q.receiver(ROOT/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json',base)
        return q.read(base/'A-owned-ledger.json')
    def test_cache_no_scheduler(self):
        with TemporaryDirectory() as tmp:
            with patch.object(t4ghi,'source_once',side_effect=AssertionError('SOURCE_EXECUTED')), \
                 patch.object(q,'producer',side_effect=AssertionError('PRODUCER_EXECUTED')):
                ledger=self.run_cache(Path(tmp))
            self.assertEqual(ledger['accepted'],24)
    def test_cache_exact_ledger_sha(self):
        with TemporaryDirectory() as tmp:
            ledger=self.run_cache(Path(tmp))
            self.assertEqual(q.digest(ledger['entries']),self.old['receiver']['ledger_sha256'])
    def test_cache_source_claim_exaggerates(self):
        with TemporaryDirectory() as tmp:
            t.cached_producer(ROOT,Path(tmp))
            reported=q.read(Path(tmp)/'producer-summary.json')
            actual=q.read(Path(tmp)/'actual-execution-custody.json')
            self.assertEqual(reported['original_BV_calls'],180)
            self.assertEqual(actual['actual_BV_source_calls_in_this_run'],0)
    def test_cache_equal_qrs_report(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);self.run_cache(p)
            with patch.object(t4nop,'custody',return_value=self.ref['N_source_pins']),patch.object(t4nop,'load_reference',return_value={}):
                t.audit(ROOT,p,p/'T4TUV.json')
            self.assertEqual(q.sha(p/'counterfeit-qrs-report.json'),t.QRS_REPORT_SHA)
            result=q.read(p/'T4TUV.json')
            self.assertIs(result['T_QRS_report_reproduced_from_cached_data'],True)
            self.assertEqual(result['U_natively_verified_semantic_receipts'],0)
            self.assertFalse(result['promotion_allowed'])
    def test_double_process_independent_cached_ledgers_equal(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp)
            first=self.run_cache(base/'first')
            second=self.run_cache(base/'second')
            self.assertEqual(first['entries'],second['entries'])
            self.assertEqual(q.digest(first['entries']),self.old['receiver']['ledger_sha256'])
    def test_cache_replay_rejected(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);self.run_cache(p)
            a=q.AReceiver(self.ref,q.read(p/'enrollment.json'))
            x=q.read(p/'relay-outbox.json')['messages'][0]
            a.accept(x)
            with self.assertRaisesRegex(q.GateError,'REPLAY_CASE_REJECTED'):a.accept(x)
    def test_cache_source_sign_forgery_rejected(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);self.run_cache(p)
            a=q.AReceiver(self.ref,q.read(p/'enrollment.json'))
            x=copy.deepcopy(q.read(p/'relay-outbox.json')['messages'][0])
            x['payload']['semantic_sign']*=-1
            with self.assertRaisesRegex(q.GateError,'SIGN_NOT_SOURCE_BOUND'):a.accept(x)
    def test_cache_origin_not_native(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);self.run_cache(p)
            self.assertFalse(q.read(p/'A-owned-ledger.json')['signed_C_neuron_packet_proven'])
    def test_cache_13_attacks_rejected(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);self.run_cache(p)
            self.assertEqual(len(q.read(p/'A-owned-ledger.json')['attacks_rejected']),13)
    def test_output_exclusive(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);t.cached_producer(ROOT,p)
            with self.assertRaisesRegex(q.GateError,'OUTPUT_EXISTS'):t.cached_producer(ROOT,p)

if __name__=='__main__':unittest.main()
