import copy
import json
from pathlib import Path
import tempfile
import unittest
from research.spk_v5_t4wxy import t4wxy as t

ROOT=Path(__file__).resolve().parents[3]
REF=ROOT/'research/spk_v5_t4wxy/reference/t4tuv-host-authority-counterexample.json'
NOMINAL=ROOT/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json'
SESSION={'key':'7e'*32,'challenge':'25'*32}

class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref=t.reference(REF)
        cls.fixtures=t.fixtures(cls.ref,NOMINAL)
        cls.allowed=[f['case_index'] for f in cls.fixtures]
    def packet(self):return t.C_compute_and_emit(self.fixtures[0],SESSION)
    def wire(self):return t.B_relay([self.packet()])[0]
    def receiver(self):return t.AReceiver(SESSION,self.allowed)
    def deny(self,mutate,expected):
        e=copy.deepcopy(self.wire());mutate(e)
        with self.assertRaisesRegex(t.GateError,expected):self.receiver().accept(e)
    def test_source_reference_hash(self):self.assertEqual(t.sha(REF),t.TUV_SHA)
    def test_source_reference_case_count(self):self.assertEqual(len(self.fixtures),24)
    def test_source_pins(self):self.assertEqual(len(self.ref['source_pins']),12)
    def test_inputs_synthetic_not_original(self):self.assertTrue(all('SYNTHETIC' in f['parent'] for f in self.fixtures))
    def test_input_roles(self):self.assertTrue(all(set(f)=={'case_index','parent','stimulus','tick'} for f in self.fixtures))
    def test_sign_balance(self):
        es=[t.C_compute_and_emit(f,SESSION) for f in self.fixtures]
        self.assertEqual(sum(e['body']['semantic_sign']==1 for e in es),12)
        self.assertEqual(sum(e['body']['semantic_sign']==-1 for e in es),12)
    def test_compute_is_nonlinear_sign_not_separate_verdict(self):
        self.assertEqual(self.packet()['body']['semantic_sign'],1)
        f=copy.deepcopy(self.fixtures[0]);f['stimulus']=[-5,1,0]
        self.assertEqual(t.C_compute_and_emit(f,SESSION)['body']['semantic_sign'],-1)
    def test_zero_activation_no_emission(self):
        f=copy.deepcopy(self.fixtures[0]);f['stimulus']=[1,1,2]
        with self.assertRaisesRegex(t.GateError,'ZERO_ACTIVATION'):t.C_compute_and_emit(f,SESSION)
    def test_issuer_only_envelope(self):self.assertEqual(set(self.packet()),{'body','authenticator'})
    def test_relay_does_not_change_body(self):self.assertEqual(self.wire()['packet'],self.packet())
    def test_receiver_accepts(self):self.assertEqual(self.receiver().accept(self.wire())['case_index'],self.fixtures[0]['case_index'])
    def test_replay(self):
        a=self.receiver();e=self.wire();a.accept(e)
        with self.assertRaisesRegex(t.GateError,'REPLAY'):a.accept(e)
    def test_all_receive(self):
        r=self.receiver()
        for f in self.fixtures:r.accept(t.B_relay([t.C_compute_and_emit(f,SESSION)])[0])
        self.assertEqual(len(r.ledger),24)
    def test_host_forgery_counterexample(self):
        c=t.host_counterexample(SESSION,self.fixtures[0],self.allowed)
        self.assertTrue(c['host_outside_C_can_forge'])
        self.assertFalse(c['issuer_process_provenance_authenticated'])
    def test_probe_count(self):self.assertEqual(len(t.negative_cases([self.wire()],SESSION,self.allowed)),13)
    def test_old_challenge(self):
        x=self.wire();other={'key':SESSION['key'],'challenge':'ff'*32}
        with self.assertRaisesRegex(t.GateError,'CAUSAL_ANCESTRY|STALE'):t.AReceiver(other,self.allowed).accept(x)
    def test_mutation_sign(self):self.deny(lambda e:e['packet']['body'].__setitem__('semantic_sign',-1),'SIGN_CHANNEL')
    def test_mutation_channel(self):self.deny(lambda e:e['packet']['body'].__setitem__('channel',14),'SIGN_CHANNEL')
    def test_mutation_origin(self):self.deny(lambda e:e['packet']['body'].__setitem__('source_context_kind','NATIVE'),'SOURCE_CLAIM')
    def test_mutation_authenticator(self):self.deny(lambda e:e['packet'].__setitem__('authenticator','f'*64),'AUTHENTICATOR')
    def test_mutation_parent(self):self.deny(lambda e:e['packet']['body'].__setitem__('causal_parent_id','wrong'),'CAUSAL_ANCESTRY')
    def test_mutation_relay(self):self.deny(lambda e:e.__setitem__('B_forward_id','0'*64),'RELAY_INTEGRITY')
    def test_wrong_route(self):self.deny(lambda e:e.__setitem__('route',['C','A']),'ROUTE')
    def test_invalid_case(self):self.deny(lambda e:e['packet']['body'].__setitem__('case_index',999),'CASE_OR_TICK')
    def test_bool_is_not_sign(self):self.deny(lambda e:e['packet']['body'].__setitem__('semantic_sign',True),'SIGN_CHANNEL')
    def test_old_packet_shape_rejected(self):self.deny(lambda e:e.__setitem__('packet',{'schema':'QRS'}),'PACKET_FIELDS')
    def test_mac_case_bound(self):self.assertNotEqual(t.mac(SESSION['key'],{'case':0}),t.mac(SESSION['key'],{'case':1}))
    def test_mac_canonical(self):self.assertEqual(t.mac(SESSION['key'],{'b':1,'a':2}),t.mac(SESSION['key'],{'a':2,'b':1}))
    def test_false_historical_promotion_forbidden(self):self.assertFalse(self.ref['promotion_allowed'])
    def test_reference_key_drifts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'src.json';p.write_bytes(REF.read_bytes()+b' ')
            with self.assertRaisesRegex(t.GateError,'HASH_DRIFT'):t.reference(p)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'link.json';p.symlink_to(REF)
            with self.assertRaisesRegex(t.GateError,'SYMLINK'):t.reference(p)
    def test_missing_reference_rejected(self):
        with self.assertRaisesRegex(t.GateError,'MISSING'):t.reference(ROOT/'nonexistent')
    def test_output_overwrite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.json';t.write(p,{})
            with self.assertRaisesRegex(t.GateError,'OUTPUT_ALREADY_EXISTS'):t.write(p,{})
    def test_separate_stages_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp)
            t.write(w/'session.json',SESSION);t.write(w/'fixtures.json',self.fixtures)
            for stage in 'cba':t.stage(stage,w)
            r=t.read(w/'A-receipt.json')
            self.assertEqual(r['accepted'],24)
            self.assertEqual(len(r['rejections']),14)
            self.assertTrue(r['host_counterexample']['host_outside_C_can_forge'])

if __name__=='__main__':unittest.main()
