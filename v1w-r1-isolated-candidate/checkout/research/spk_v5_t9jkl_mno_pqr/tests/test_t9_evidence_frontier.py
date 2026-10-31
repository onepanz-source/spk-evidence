import copy, json, sqlite3, tempfile, unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import MultiTickEngine, Reject
from research.spk_v5_t9jkl_mno_pqr.stale_evidence_v1 import HistoricalEvidence, attestable_stale
from research.spk_v5_t9jkl_mno_pqr.admission_frontier_v1 import run_strategy
from research.spk_v5_t9jkl_mno_pqr.cumulative_evidence_frontier import stale_credit_counterexample,report,PARENT_SHA,sha

ROOT=Path(__file__).resolve().parents[3]

class HistoricalCustody(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.p=Path(self.t.name)
        self.e=MultiTickEngine(self.p/'r.sqlite',max_inflight=3)
        self.addCleanup(self.e.close)
        self.epochs=[self.e.submit(0,11),self.e.submit(0,11),self.e.submit(1,12)]
        self.e.run()
        self.rows=attestable_stale(self.e)
    def test_source_audit_observes_one_veto(self):self.assertEqual(len(self.rows),1)
    def test_p_grants_untouched_by_observer(self):
        before=self.e.audit();self.assertEqual(len(self.rows),1);self.assertEqual(before,self.e.audit())
    def test_original_not_double_credited(self):
        self.assertEqual([self.e.result(i)['grant'] for i in self.epochs],[0,None,1])
    def test_original_event_and_relay_evidence(self):
        self.assertEqual(self.rows[0]['issued_version'],0)
        self.assertEqual(self.rows[0]['observed_version'],1)
        self.assertEqual(self.rows[0]['verdict'],'WORSENED')
    def test_historical_has_no_authority(self):
        self.assertFalse(self.rows[0]['P_grant_allowed']);self.assertEqual(self.rows[0]['authority'],'OBSERVATION_ONLY')
    def test_append_reopen_replay(self):
        led=HistoricalEvidence(self.p/'h.sqlite');led.append(self.rows[0]);before=led.audit();led.reopen()
        self.assertEqual(before,led.audit())
        with self.assertRaisesRegex(Reject,'HISTORICAL_REPLAY'):led.append(self.rows[0])
        self.assertEqual(led.audit()['P_grants'],0);led.close()
    def test_bad_promotions_rejected(self):
        for changes in ({'P_grant_allowed':True},{'authority':'C_NATIVE_P'},{'sensor_authenticated':True},{'observed_version':0},{'verdict':'UNDEFINED'},{'feedback_digest':'invalid'}):
            led=HistoricalEvidence(self.p/('bad_'+str(list(changes)[0])+'.sqlite'))
            with self.subTest(changes=changes),self.assertRaises(Reject):led.append({**self.rows[0],**changes})
            led.close()
    def test_ledger_tamper_rejected_on_reopen(self):
        led=HistoricalEvidence(self.p/'bad.sqlite');led.append(self.rows[0]);led.close()
        db=sqlite3.connect(self.p/'bad.sqlite')
        db.execute("UPDATE evidence SET tip='FAKE' WHERE seq=0");db.commit();db.close()
        with self.assertRaisesRegex(Reject,'HISTORICAL_LEDGER_DRIFT'):HistoricalEvidence(self.p/'bad.sqlite')
    def test_veto_event_tamper_rejected_by_engine(self):
        self.e.db.execute('UPDATE event SET digest=? WHERE kind=?',('X'*64,'SEM_B_C'))
        with self.assertRaises(Reject):attestable_stale(self.e)
    def test_veto_ledger_tamper_rejected_by_engine(self):
        self.e.db.execute("UPDATE ledger SET digest='BAD' WHERE kind='VETO_STALE_POLICY'")
        with self.assertRaises(Reject):attestable_stale(self.e)
    def test_non_stale_has_empty_receipts(self):
        with tempfile.TemporaryDirectory() as t:
            e=MultiTickEngine(Path(t)/'x.sqlite');e.submit(0,11);e.run()
            self.assertEqual(attestable_stale(e),[]);e.close()
    def test_fabricated_observer_row_is_host_forgeable(self):
        led=HistoricalEvidence(self.p/'forge.sqlite')
        forged=copy.deepcopy(self.rows[0]);forged['feedback_digest']='f'*64
        led.append(forged)
        self.assertEqual(led.audit()['historical_records'],1)
        self.assertEqual(led.audit()['P_grants'],0)
        led.close()
    def test_host_change_to_observed_outcome_not_native_authority(self):
        led=HistoricalEvidence(self.p/'forge2.sqlite')
        forged=copy.deepcopy(self.rows[0]);forged['verdict']='IMPROVED'
        led.append(forged)
        self.assertEqual(led.audit()['historical_records'],1)
        led.close()

class AdmissionFrontier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=run_strategy('serial');cls.n=run_strategy('batch3');cls.a=run_strategy('context_affinity')
    def test_serial_success(self):self.assertEqual(self.s['successes'],88)
    def test_naive_success(self):self.assertEqual(self.n['successes'],84)
    def test_affinity_success(self):self.assertEqual(self.a['successes'],88)
    def test_success_gain_four(self):self.assertEqual(self.a['successes']-self.n['successes'],4)
    def test_same_episodes(self):self.assertEqual([x['episodes'] for x in (self.s,self.n,self.a)],[96,96,96])
    def test_same_dispatch_event_count(self):self.assertEqual([x['dispatcher_slots'] for x in (self.s,self.n,self.a)],[480,480,480])
    def test_serial_waves(self):self.assertEqual(self.s['waves'],96)
    def test_naive_waves(self):self.assertEqual(self.n['waves'],32)
    def test_affinity_waves(self):self.assertEqual(self.a['waves'],48)
    def test_affinity_has_parallelism_cost(self):self.assertEqual(self.a['waves']-self.n['waves'],16)
    def test_affinity_only_two_active(self):self.assertEqual(self.a['max_inflight_admitted'],2)
    def test_naive_reaches_three(self):self.assertEqual(self.n['max_inflight_admitted'],3)
    def test_serial_active_one(self):self.assertEqual(self.s['max_inflight_admitted'],1)
    def test_parent_grant_count_preserved(self):self.assertEqual([x['P_grants'] for x in (self.s,self.n,self.a)],[8,8,8])
    def test_naive_stale_evidence(self):self.assertEqual(self.n['stale_vetoes'],4)
    def test_affinity_zero_stale(self):self.assertEqual(self.a['stale_vetoes'],0)
    def test_historical_credit_never_p_grant(self):self.assertEqual(self.n['historical_evidence']['P_grants'],0)
    def test_historical_exactly_four(self):self.assertEqual(self.n['historical_evidence']['historical_records'],4)
    def test_affinity_evidence_zero(self):self.assertEqual(self.a['historical_evidence']['historical_records'],0)
    def test_no_feedback_no_learning(self):
        x=run_strategy('batch3',learn=False)
        self.assertEqual((x['successes'],x['P_grants']), (48,0))
    def test_naive_reopen(self):
        x=run_strategy('batch3',reopen_each_wave=True)
        for k in ('core_rows_digest','historical_evidence','successes','P_grants','stale_vetoes'):
            self.assertEqual(x[k],self.n[k],k)
    def test_affinity_reopen(self):
        x=run_strategy('context_affinity',reopen_each_wave=True)
        for k in ('core_rows_digest','historical_evidence','successes','P_grants','stale_vetoes'):
            self.assertEqual(x[k],self.a[k],k)
    def test_invalid_strategy(self):
        with self.assertRaises(Reject):run_strategy('grant-all-stale')

class CumulativeGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=report(ROOT)
    def test_pin_reference(self):
        self.assertEqual(sha(ROOT/'research/spk_v5_t9jkl_mno_pqr/reference/t9abc-def-ghi-cumulative.json'),PARENT_SHA)
    def test_exact_parent_naive_digest(self):
        p=json.loads((ROOT/'research/spk_v5_t9jkl_mno_pqr/reference/t9abc-def-ghi-cumulative.json').read_text())
        self.assertEqual(self.r['T9MNO']['naive_three_inflight']['core_rows_digest'],p['T9ABC']['three_epoch_adaptive']['rows_sha256'])
    def test_exact_parent_serial_digest(self):
        p=json.loads((ROOT/'research/spk_v5_t9jkl_mno_pqr/reference/t9abc-def-ghi-cumulative.json').read_text())
        self.assertEqual(self.r['T9MNO']['serial']['core_rows_digest'],p['T9ABC']['serial_t8_parity']['rows_sha256'])
    def test_no_stale_credit(self):self.assertEqual(self.r['T9JKL']['historical_feedback_P_grants'],0)
    def test_counterexample_pe_real(self):
        x=self.r['T9PQR']['stale_credit_harm_counterexample']
        self.assertEqual((x['correct_C_action'],x['unsafe_hypothetical_recredit_action']),(11,12))
    def test_reference_native_separated(self):
        self.assertEqual(self.r['native_SPK_P_grants'],0);self.assertFalse(self.r['native_learning'])
    def test_old_scheduler_never_called(self):self.assertEqual(self.r['new_frozen_scheduler_calls'],0)
    def test_research_promotion_denied(self):self.assertFalse(self.r['promotion_allowed'])
    def test_source_not_authenticated(self):self.assertTrue(self.r['host_can_forge'])
    def test_historical_no_backdoor(self):self.assertFalse(self.r['T9PQR']['credit_reinterpretation_permitted'])
    def test_physical_time_not_claimed(self):self.assertFalse(self.r['T9MNO']['physical_latency_or_energy_measured'])
    def test_identical_report(self):self.assertEqual(self.r,report(ROOT))

if __name__=='__main__':unittest.main()
