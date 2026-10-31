"""T17 adversarial proof: source PE, actuator discovery, owned P, replay and denial."""
import inspect,json,sqlite3,tempfile,unittest
from pathlib import Path
from research.spk_v5_t17_macro_polarity.adaptive_runtime_v2 import (
 StagedCell,STAGES,map_action,judge_with_effect,forward_with_effect,propose_P)
from research.spk_v5_t15_macro_causal_learning.causal_cell_v1 import (
 HEAT,COOL,ANeuron,CNeuron)
from spk_architecture_v1.pe_execution_v1b import _compute_local

class PolarityTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  self.path=Path(tmp.name)/'one.sqlite'
 def cell(self,reverse=False,**kw):
  c=StagedCell(self.path,setpoint=kw.pop('setpoint',5),reverse_actuator=reverse,**kw)
  self.addCleanup(c.close);return c
 def progress(self,c,steps):return [c.dispatch() for _ in range(steps)]
 def test_01_source_pe_is_frozen_original(self):
  self.assertEqual(inspect.getmodule(_compute_local).__name__,'spk_architecture_v1.pe_execution_v1b')
 def test_02_all_sensor_directions_pe(self):
  for before in range(16):
   for after in range(16):
    a=judge_with_effect(before,after,5)
    self.assertEqual(a['effect_direction'],(after>before)-(after<before))
    self.assertEqual(a['verdict'],ANeuron.judge(before,after,5)['verdict'])
    self.assertEqual(len(a['effect_PE_digest']),64)
 def test_03_unknown_mapping_defaults_to_probe(self):
  self.assertEqual(map_action(HEAT,0),HEAT);self.assertEqual(map_action(COOL,0),COOL)
 def test_04_reverse_swaps_both_actions(self):
  self.assertEqual(map_action(HEAT,-1),COOL);self.assertEqual(map_action(COOL,-1),HEAT)
 def test_05_bad_sign_denied(self):
  with self.assertRaises(ValueError):map_action(HEAT,3)
 def test_06_forward_direction_is_bounded_to_a(self):
  a=judge_with_effect(6,5,5);p=forward_with_effect(7,a)
  self.assertEqual(p['effect_direction'],-1);self.assertEqual(p['A_digest'],__import__('research.spk_v5_t17_macro_polarity.adaptive_runtime_v2',fromlist=['sha']).sha(a))
 def test_07_normal_sign_discovers_from_action(self):
  c=self.cell();r=c.trial(6)
  self.assertEqual(r['credit'],1);self.assertEqual(c.state()['actuator_sign'],1);c.audit()
 def test_08_reversed_sign_discovers_from_action(self):
  c=self.cell(reverse=True);r=c.trial(6)
  self.assertEqual(r['credit'],1);self.assertEqual(c.state()['actuator_sign'],-1);c.audit()
 def test_09_reverse_neutral_at_boundary_never_guesses(self):
  c=self.cell(reverse=True);r=c.trial(0)
  self.assertEqual(r['credit'],0);self.assertEqual(c.state()['actuator_sign'],0)
 def test_10_no_theta_change_during_unknown_polarity_learning(self):
  c=self.cell(reverse=True);c.trial(6)
  self.assertEqual(c.state()['theta'],12)
 def test_11_threshold_changes_only_after_polarity(self):
  c=self.cell(reverse=True);c.trial(6);c.trial(8)
  self.assertEqual(c.state()['actuator_sign'],-1);self.assertEqual(c.state()['theta'],8)
 def test_12_reopen_preserves_both_P_fields(self):
  c=self.cell(reverse=True);c.trial(6);before=c.audit();p=c.state();c.reopen()
  self.assertEqual(c.state(),p);self.assertEqual(c.audit(),before)
 def test_13_five_independent_durable_ticks(self):
  c=self.cell(reverse=True);ep=c.submit(6)
  for stage in STAGES:
   self.assertEqual(c.dispatch()['kind'],stage);c.audit();c.reopen()
  self.assertEqual(c.result(ep)['credit'],1)
 def test_14_no_host_supplied_verdict(self):
  c=self.cell()
  with self.assertRaises(TypeError):c.submit(6,verdict='IMPROVED')
 def test_15_no_host_supplied_polarity(self):
  c=self.cell()
  with self.assertRaises(TypeError):c.submit(6,actuator_sign=-1)
 def test_16_learning_off_freezes_both_P(self):
  c=self.cell(reverse=True)
  for t in (6,8,10):c.trial(t,learning=False)
  self.assertEqual(c.state(),{'theta':12,'actuator_sign':0,'version':0,'commits':0})
 def test_17_missing_feedback_zero_grants(self):
  c=self.cell(reverse=True);r=c.trial(6,feedback='missing')
  self.assertEqual(r['credit'],0);self.assertEqual(c.state()['version'],0)
 def test_18_wrong_lineage_zero_grants(self):
  c=self.cell(reverse=True);r=c.trial(6,feedback='wrong_lineage')
  self.assertEqual(r['credit'],0);self.assertEqual(c.state()['actuator_sign'],0)
 def test_19_altered_verdict_zero_grants(self):
  c=self.cell(reverse=True);r=c.trial(6,feedback='altered')
  self.assertEqual(r['credit'],0);c.audit()
 def test_20_effect_direction_tamper_zero_grants(self):
  c=self.cell(reverse=True);r=c.trial(6,feedback='effect_tamper')
  self.assertEqual(r['credit'],0);self.assertEqual(c.state()['version'],0);c.audit()
 def test_21_direct_P_update_denied(self):
  c=self.cell(reverse=True)
  with self.assertRaises(sqlite3.IntegrityError):c.db.execute('UPDATE p SET actuator_sign=-1,version=1,commits=1')
 def test_22_direct_theta_update_denied(self):
  c=self.cell()
  with self.assertRaises(sqlite3.IntegrityError):c.db.execute('UPDATE p SET theta=8,version=1,commits=1')
 def test_23_policy_verify_stalls_then_resumes(self):
  c=self.cell(reverse=True);c.set_policy(expected_revision=0,mode='verify')
  ep=c.submit(6);c.drain();self.assertEqual(c.audit()['pending'],1)
  c.reopen();c.set_policy(expected_revision=1,mode='execute');c.drain()
  self.assertEqual(c.result(ep)['credit'],1)
 def test_24_exhaustion_stalls_then_resumes(self):
  c=self.cell(reverse=True,ceiling=0);ep=c.submit(6);c.drain()
  self.assertEqual(c.state()['version'],0);self.assertEqual(c.audit()['pending'],1)
  c.reopen();c.set_policy(expected_revision=0,ceiling=3);c.drain()
  self.assertEqual(c.result(ep)['credit'],1)
 def test_25_stale_version_denies_double_grant(self):
  c=self.cell(reverse=True,max_active=2);a=c.submit(6);b=c.submit(8);c.drain()
  self.assertEqual(c.result(a)['credit'],1)
  self.assertEqual(c.result(b)['credit'],0)
  self.assertEqual(c.result(b)['reason'],'STALE_P_VERSION');c.audit()
 def test_26_cannot_replay_completed_credit(self):
  c=self.cell(reverse=True);c.trial(6);old=c.audit();c.reopen()
  self.assertIsNone(c.dispatch());self.assertEqual(c.audit(),old)
 def test_27_invalid_sensor_input_denied(self):
  c=self.cell()
  for t in (-1,16,False,1.1):
   with self.subTest(t=t),self.assertRaises(ValueError):c.submit(t)
 def test_28_bad_reopen_world_configuration_denied(self):
  c=self.cell(reverse=True);c.close()
  with self.assertRaises(ValueError):StagedCell(self.path,setpoint=5,create=False,reverse_actuator=False)
 def test_29_A_event_tamper_denied(self):
  c=self.cell(reverse=True);c.submit(6);self.progress(c,4)
  c.db.execute("UPDATE episode SET A_digest='X'")
  with self.assertRaises(ValueError):c.dispatch()
 def test_30_WORLD_event_tamper_denied(self):
  c=self.cell(reverse=True);c.submit(6);self.progress(c,4)
  c.db.execute("UPDATE event SET body='{}' WHERE kind='WORLD'")
  with self.assertRaises(ValueError):c.dispatch()
 def test_31_A_payload_tamper_denied(self):
  c=self.cell(reverse=True);c.submit(6);self.progress(c,4)
  a=json.loads(c.db.execute('SELECT A_json FROM episode').fetchone()[0]);a['effect_direction']=1
  c.db.execute('UPDATE episode SET A_json=?',(json.dumps(a),))
  with self.assertRaises(ValueError):c.dispatch()
 def test_32_event_digest_drift_audited(self):
  c=self.cell(reverse=True);c.trial(6)
  c.db.execute("UPDATE event SET digest='X' WHERE kind='A_PE'")
  with self.assertRaises(ValueError):c.audit()
 def test_33_p_grant_sign_drift_audited(self):
  c=self.cell(reverse=True);c.trial(6)
  c.db.execute('UPDATE p_grant SET new_sign=1')
  with self.assertRaises(ValueError):c.audit()
 def test_34_p_sign_drift_audited(self):
  c=self.cell(reverse=True);c.trial(6)
  c.db.execute('DROP TRIGGER p_update_guard');c.db.execute('UPDATE p SET actuator_sign=1')
  with self.assertRaises(ValueError):c.audit()
 def test_35_source_sign_not_host_provided(self):
  c=self.cell(reverse=True);c.submit(6)
  self.progress(c,3)
  a=json.loads(c.db.execute('SELECT A_json FROM episode').fetchone()[0])
  self.assertEqual(a['effect_direction'],-1)
  self.assertEqual(a['effect_preprocessing'],'A_LOCAL_SIGNED_SENSOR_DIFFERENCE_V1')
 def test_36_C_does_not_call_plant_during_credit(self):
  c=self.cell(reverse=True);ep=c.submit(6);self.progress(c,4)
  old=c.world.apply
  def forbidden(*args):raise AssertionError('C_APPLIED_WORLD_MODEL')
  c.world.apply=forbidden
  self.assertEqual(c.dispatch()['kind'],'C_CREDIT')
  c.world.apply=old
  self.assertEqual(c.result(ep)['credit'],1);c.audit()
 def test_37_audit_independently_checks_plant(self):
  c=self.cell(reverse=True);c.trial(6)
  c.db.execute('UPDATE episode SET after_temp=7')
  with self.assertRaises(ValueError):c.audit()
 def test_38_readonly_eval_remains_unchanged(self):
  c=self.cell(reverse=True);c.trial(6);before=c.state()
  for t in range(16):c.trial(t,learning=False)
  self.assertEqual(before,c.state());c.audit()
 def test_39_no_learning_claim(self):
  c=self.cell(reverse=True);c.trial(6)
  self.assertFalse(c.audit()['original_SPK_native_learning'])
 def test_40_resume_when_paused_before_world(self):
  c=self.cell(reverse=True);c.submit(8);c.dispatch();c.reopen()
  c.drain();self.assertEqual(c.audit()['settled'],1)
 def test_41_no_credit_on_boundary_ineffective_action(self):
  c=self.cell(reverse=True);c.trial(0)
  self.assertEqual(c.state()['actuator_sign'],0)
 def test_42_C_program_original_branch(self):
  c=self.cell(reverse=True);ep=c.submit(8);c.dispatch()
  row=c.db.execute('SELECT choice_PE_sha FROM episode').fetchone()
  self.assertEqual(len(row[0]),64)
  c.drain();c.audit()

# Additional online custody tests: audit is not the only barrier.
class OnlineCustodyTests(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.path=Path(t.name)/'db.sqlite'
 def test_43_B_json_changed_to_intended_packet_is_not_enough(self):
  c=StagedCell(self.path,setpoint=5,reverse_actuator=True)
  self.addCleanup(c.close);ep=c.submit(6,feedback='wrong_lineage')
  for _ in range(4):c.dispatch()
  a=json.loads(c.db.execute('SELECT A_json FROM episode').fetchone()[0])
  genuine=forward_with_effect(ep,a)
  c.db.execute('UPDATE episode SET B_json=?',(json.dumps(genuine,sort_keys=True,separators=(',',':')),))
  with self.assertRaises(ValueError):c.dispatch()
 def test_44_B_event_tamper_even_when_digest_resealed(self):
  c=StagedCell(self.path,setpoint=5,reverse_actuator=True)
  self.addCleanup(c.close);c.submit(6)
  for _ in range(4):c.dispatch()
  c.db.execute("UPDATE event SET body='null',digest='forged' WHERE kind='B_RELAY'")
  with self.assertRaises(ValueError):c.dispatch()
 def test_45_A_event_payload_tamper_even_if_episode_intact(self):
  c=StagedCell(self.path,setpoint=5,reverse_actuator=True)
  self.addCleanup(c.close);c.submit(6)
  for _ in range(4):c.dispatch()
  c.db.execute("UPDATE event SET body='{}' WHERE kind='A_PE'")
  with self.assertRaises(ValueError):c.dispatch()

if __name__=='__main__':unittest.main()
