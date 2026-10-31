import copy
import json
from pathlib import Path
import tempfile
import unittest
from research.spk_v5_t4qrs import t4qrs as q

ROOT=Path(__file__).resolve().parents[3]
REF=ROOT/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json'

class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=q.load_reference(REF)
        cls.rows=[r for r in cls.r['O_rows'] if r['research_classification']==q.ELIGIBLE]
    def setup_auth(self):
        commits={};messages=[]
        for row in self.rows:
            i=row['index'];sign=row['observed_sign'];typ=1 if sign==1 else -1
            event_channels=(11,13,13) if typ==1 else (12,14,14)
            packet={'schema':q.PACKET_SCHEMA,'case_index':i,'source_sha256':row['source_sha256'],
                  'semantic_sign':sign,'source_kind':q.SOURCE_KIND,'emissions':[
                     {'role':role,'channel':ch,'timestamp':t} for role,ch,t in zip(('C','B','A'),event_channels,(14,15,16))],
                  'delivery_routes':[['C','B'],['B','A']],'recipient':'A'}
            token=f'{i+1:064x}';commits[str(i)]=q.precommit(packet,token)
            messages.append({'hop':'B_TO_A_RESEARCH_RELAY','payload':packet,'token':token})
        enrollment={'schema':q.ENROLL_SCHEMA,'commitments':commits,'reference_sha256':q.REF_SHA}
        return q.AReceiver(self.r,enrollment),messages
    def check_reject(self,mutate,reason):
        receiver,messages=self.setup_auth();bad=copy.deepcopy(messages[0]);mutate(bad)
        with self.assertRaisesRegex(q.GateError,reason):receiver.accept(bad)
        self.assertEqual(len(receiver.ledger),0)

class SourceAndPolicyTests(Base):
    def test_reference_hash(self):self.assertEqual(q.sha(REF),q.REF_SHA)
    def test_case_total(self):self.assertEqual(len(self.r['O_rows']),180)
    def test_guard_only_24(self):self.assertEqual(len(self.rows),24)
    def test_sign_balance(self):self.assertEqual([sum(r['observed_sign']==s for r in self.rows) for s in (1,-1)],[12,12])
    def test_no_native_credits(self):self.assertTrue(all(not r['native_receiver_semantic_credit'] for r in self.r['O_rows']))
    def test_schema(self):self.assertTrue(q.SCHEMA.endswith('/research-v0'))
    def test_canonical_stable(self):self.assertEqual(q.canonical({'b':2,'a':1}),q.canonical({'a':1,'b':2}))
    def test_token_domain(self):self.assertNotEqual(q.precommit({'a':1},'01'*32),q.digest({'a':1}))
    def test_token_shape(self):
        with self.assertRaisesRegex(q.GateError,'TOKEN_FORMAT'):q.precommit({},'oops')
    def test_token_hex(self):
        with self.assertRaisesRegex(q.GateError,'TOKEN_HEX'):q.precommit({},'q'*64)
    def test_both_signs_have_distinct_channels(self):
        for row in self.rows:
            obs={'C_sign_candidate_from_same_source_forward_output':row['observed_sign'],
                 'C_B_A_emission_candidate_consistent':True,
                 'event_candidate_paths':{role:{'timestamp':t,'channel':ch} for role,t,ch in zip(
                   ('C','B','A'),(14,15,16),((11,13,13) if row['observed_sign']==1 else (12,14,14)))}}
            pkt=q.events_packet(row['index'],row['source_sha256'],obs)
            self.assertTrue(q.validate_packet_structure(pkt,row))
    def test_no_sign_denied(self):
        with self.assertRaisesRegex(q.GateError,'C_SIGN_NOT_PRESENT'):
            q.events_packet(1,self.r['O_rows'][1]['source_sha256'],{'C_sign_candidate_from_same_source_forward_output':None})
    def test_inconsistent_chain_denied(self):
        with self.assertRaisesRegex(q.GateError,'C_B_A_EVENTS_NOT_CONSISTENT'):
            q.events_packet(0,self.r['O_rows'][0]['source_sha256'],{'C_sign_candidate_from_same_source_forward_output':1,'C_B_A_emission_candidate_consistent':False})

class ReceiverTests(Base):
    def test_24_commits(self):
        a,es=self.setup_auth()
        for e in es:a.accept(e)
        self.assertEqual(len(a.ledger),24)
        self.assertEqual(len(a.tokens),24)
    def test_atomic_negative_probes(self):
        a,es=self.setup_auth()
        attacks=q.forge_probes(a,es)
        self.assertEqual(len(attacks),12)
        self.assertEqual(a.ledger,{})
    def test_replay(self):
        a,es=self.setup_auth();a.accept(es[0])
        with self.assertRaisesRegex(q.GateError,'REPLAY_CASE_REJECTED'):a.accept(es[0])
        self.assertEqual(len(a.ledger),1)
    def test_sign_change(self):self.check_reject(lambda e:e['payload'].__setitem__('semantic_sign',-e['payload']['semantic_sign']),'SIGN_NOT_SOURCE_BOUND')
    def test_hash_change(self):self.check_reject(lambda e:e['payload'].__setitem__('source_sha256','f'*64),'SOURCE_SHA_MISMATCH')
    def test_channel_change(self):self.check_reject(lambda e:e['payload']['emissions'][1].__setitem__('channel',99),'SEMANTIC_CHANNEL_MISMATCH')
    def test_timestamp_reversal(self):self.check_reject(lambda e:e['payload']['emissions'][2].__setitem__('timestamp',10),'ORDER_INVALID')
    def test_forward_route(self):self.check_reject(lambda e:e['payload'].__setitem__('delivery_routes',[['C','A']]),'ROUTE_INVALID')
    def test_author_kind_spoof(self):self.check_reject(lambda e:e['payload'].__setitem__('source_kind','NATIVE_C'),'SOURCE_KIND_INVALID')
    def test_extra_field(self):self.check_reject(lambda e:e['payload'].__setitem__('authenticator','forge'),'PACKET_KEYS_INVALID')
    def test_proof_forgery(self):self.check_reject(lambda e:e.__setitem__('token','0'*64),'COMMITMENT_PROOF_MISMATCH')
    def test_weak_bypass(self):self.check_reject(lambda e:e.__setitem__('hop','C_TO_A_DIRECT'),'RELAY_HOP_INVALID')
    def test_boolean_sign(self):self.check_reject(lambda e:e['payload'].__setitem__('semantic_sign',True),'SIGN_NOT_SOURCE_BOUND')
    def test_wrong_recipient(self):self.check_reject(lambda e:e['payload'].__setitem__('recipient','B'),'ROUTE_INVALID')
    def test_no_forward_case(self):self.check_reject(lambda e:e['payload'].__setitem__('case_index',3),'CASE_NOT_COMMISSIONED')
    def test_no_reverse_case(self):self.check_reject(lambda e:e['payload'].__setitem__('case_index',4),'CASE_NOT_COMMISSIONED')
    def test_no_sensor_case(self):self.check_reject(lambda e:e['payload'].__setitem__('case_index',1),'CASE_NOT_COMMISSIONED')
    def test_enroll_missing_case(self):
        a,es=self.setup_auth();c=dict(a.commits);c.pop(next(iter(c)))
        with self.assertRaisesRegex(q.GateError,'ENROLL_COUNT_INVALID'):
            q.AReceiver(self.r,{'schema':q.ENROLL_SCHEMA,'commitments':c})
    def test_enroll_duplicate(self):
        a,es=self.setup_auth();c=dict(a.commits);keys=list(c);c[keys[1]]=c[keys[0]]
        with self.assertRaisesRegex(q.GateError,'ENROLL_DUPLICATE_COMMITMENT'):
            q.AReceiver(self.r,{'schema':q.ENROLL_SCHEMA,'commitments':c})
    def test_enroll_wrong_index(self):
        a,es=self.setup_auth();c=dict(a.commits);c['4']=c.pop(next(iter(c)))
        with self.assertRaisesRegex(q.GateError,'ENROLL_GUARD_COVERAGE_MISMATCH'):
            q.AReceiver(self.r,{'schema':q.ENROLL_SCHEMA,'commitments':c})
    def test_delayed_commit_mutation(self):
        a,es=self.setup_auth()
        a.accept(es[0]);before=copy.deepcopy(a.ledger)
        e=copy.deepcopy(es[1]);e['payload']['emissions'][0]['timestamp']=19
        with self.assertRaises(q.GateError):a.accept(e)
        self.assertEqual(before,a.ledger)
    def test_token_swapped(self):
        a,es=self.setup_auth();e=copy.deepcopy(es[0]);e['token']=es[1]['token']
        with self.assertRaisesRegex(q.GateError,'COMMITMENT_PROOF_MISMATCH'):a.accept(e)
    def test_undocumented_unknown_signal(self):
        a,es=self.setup_auth();e=copy.deepcopy(es[0]);e['payload']['emissions'][0]['channel']=30
        with self.assertRaisesRegex(q.GateError,'SEMANTIC_CHANNEL_MISMATCH'):a.accept(e)
    def test_wrong_envelope_fields(self):
        a,es=self.setup_auth();e=copy.deepcopy(es[0]);e['metadata']={}
        with self.assertRaisesRegex(q.GateError,'ENVELOPE_INVALID'):a.accept(e)
    def test_output_create_exclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'data.json';q.write(p,{'ok':True})
            with self.assertRaisesRegex(q.GateError,'OUTPUT_EXISTS'):q.write(p,{'ok':False})

class OfflinePipelineTests(Base):
    def test_all_three_process_stage_functions_with_mocked_source(self):
        # Only an adapter-to-receiver integration test: source_once is mocked.
        # The real 180 BV source calls are independently required by the user gate.
        from unittest.mock import patch
        from research.spk_v5_t4nop import t4nop
        from research.spk_v5_t4ghi import t4ghi
        from research.spk_v5_t4jkl_fix import t4jkl_fix
        ghi=t4jkl_fix.reference(ROOT/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json')
        historical=ghi['H_rows']
        from types import SimpleNamespace
        cases=[]; sources=[]
        for i,h in enumerate(historical):
            failure=h['failure']
            measurement=SimpleNamespace(send_decision=failure!='no_marker',
                forward_enabled=failure!='no_forward',reverse_enabled=failure!='no_reverse')
            cases.append(({'failure':failure,'arm':h['arm']},measurement,h['arm']))
            sources.append({'__sha':h['source_sha256'],
                '__obs':{'C_sign_candidate_from_same_source_forward_output':h['C_sign_candidate_from_same_source_forward_output'],
                         'event_candidate_paths':h['event_candidate_paths'],
                         'C_B_A_emission_candidate_consistent':h['C_B_A_emission_candidate_consistent']}})
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            with patch.object(t4nop,'custody',return_value=self.r['N_source_pins']),\
                 patch.object(t4nop,'load_reference',return_value={}),\
                 patch.object(t4ghi.prev,'table_cases',return_value=iter(cases)),\
                 patch.object(t4ghi,'source_once',side_effect=iter(sources)),\
                 patch.object(t4ghi,'digest',side_effect=lambda x:x['__sha']),\
                 patch.object(t4ghi,'observe_forward_result',side_effect=lambda x:x['__obs']):
                q.producer(ROOT,REF,directory)
                q.relay(directory)
                q.receiver(REF,directory)
                q.audit(ROOT,REF,directory,directory/'report.json')
            report=q.read(directory/'report.json')
            self.assertEqual(report['producer']['original_BV_calls'],180)
            self.assertEqual(report['receiver']['committed_count'],24)
            self.assertEqual(report['receiver']['rejected_adversarial_count'],13)
            self.assertFalse(report['C_neuron_origin_authenticated'])
            self.assertFalse(report['promotion_allowed'])

if __name__=='__main__':unittest.main()
