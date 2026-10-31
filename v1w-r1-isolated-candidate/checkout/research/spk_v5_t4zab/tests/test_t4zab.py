import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import types
import unittest
from research.spk_v5_t4zab import t4zab as t

class N:
    def __init__(self,node_id):self.node_id=node_id

def _compute_local(node,state,timestamp,channels):
    return (node.node_id,state,timestamp,channels)

def execute_on_pes_v1b():
    return _compute_local(N('C'),{},15,(4,))

class SeamTests(unittest.TestCase):
    def setUp(self):
        self.pe=types.SimpleNamespace(_compute_local=_compute_local,execute_on_pes_v1b=execute_on_pes_v1b)
        self.wxy=Path(__file__).resolve().parents[1]/'reference/t4wxy-c-context-reference.json'
    def test_reference_pin(self):
        self.assertEqual(t.sha(self.wxy),t.WXY_SHA)
    def test_reference_safe_fields(self):
        self.assertFalse(t.wxy_ref(self.wxy)['promotion_allowed'])
    def test_reference_modified_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'r.json';p.write_bytes(self.wxy.read_bytes()+b' ')
            with self.assertRaisesRegex(t.GateError,'WXY_REFERENCE_SHA_DRIFT'):t.wxy_ref(p)
    def test_reference_missing(self):
        with self.assertRaisesRegex(t.GateError,'WXY_REFERENCE_MISSING'):t.wxy_ref('/no-such-file-spk-t4zab')
    def test_source_pin_count(self):self.assertEqual(len(t.wxy_ref(self.wxy)['source_pins']),12)
    def test_source_names_exact(self):self.assertEqual(len(t.SOURCE_NAMES),2)
    def test_sources_pinned(self):self.assertEqual(t.PE_SHA,t.wxy_ref(self.wxy)['source_pins'][t.SOURCE_NAMES[0][0]])
    def test_observe_unchanged(self):
        x=[]
        with t.observe_C_steps(self.pe,x):r=self.pe._compute_local(N('C'),{},15,(2,))
        self.assertEqual(r,('C',{},15,(2,)))
        self.assertEqual(x,[{'timestamp':15,'input_channels':[2],'returned_type':'tuple'}])
        self.assertIs(self.pe._compute_local,_compute_local)
    def test_observe_not_B(self):
        x=[]
        with t.observe_C_steps(self.pe,x):self.pe._compute_local(N('B'),{},15,(2,))
        self.assertEqual(x,[])
    def test_observe_not_A(self):
        x=[]
        with t.observe_C_steps(self.pe,x):self.pe._compute_local(N('A'),{},15,(2,))
        self.assertEqual(x,[])
    def test_observe_no_native_claim(self):
        x=[]
        with t.observe_C_steps(self.pe,x):self.pe._compute_local(N('C'),{},10,(3,))
        self.assertNotIn('native_C',json.dumps(x))
    def test_observe_throws_restore(self):
        with self.assertRaisesRegex(RuntimeError,'boom'):
            with t.observe_C_steps(self.pe,[]):raise RuntimeError('boom')
        self.assertIs(self.pe._compute_local,_compute_local)
    def test_observe_zero_return(self):
        original=self.pe._compute_local
        def zero(node,state,timestamp,channels):return None
        self.pe._compute_local=zero
        events=[]
        with t.observe_C_steps(self.pe,events):self.assertIsNone(self.pe._compute_local(N('C'),{},12,(4,)))
        self.assertIs(self.pe._compute_local,zero)
        self.assertEqual(events[0]['returned_type'],'NoneType')
    def test_wrong_signature(self):
        self.pe._compute_local=lambda a:0
        with self.assertRaisesRegex(t.GateError,'PE_COMPUTE_SIGNATURE_DRIFT'):
            with t.observe_C_steps(self.pe,[]):pass
    def test_wrong_call_graph(self):
        self.pe.execute_on_pes_v1b=lambda:42
        with self.assertRaisesRegex(t.GateError,'PE_CALL_GRAPH_DRIFT'):
            with t.observe_C_steps(self.pe,[]):pass
    def test_timestamp_type(self):
        with self.assertRaisesRegex(t.GateError,'C_COMPUTE_TIMESTAMP_INVALID'):
            with t.observe_C_steps(self.pe,[]):self.pe._compute_local(N('C'),{},'15',(3,))
        self.assertIs(self.pe._compute_local,_compute_local)
    def test_channel_type(self):
        with self.assertRaisesRegex(t.GateError,'C_COMPUTE_CHANNELS_INVALID'):
            with t.observe_C_steps(self.pe,[]):self.pe._compute_local(N('C'),{},15,('4',))
    def test_channel_accepts_tuple(self):
        x=[]
        with t.observe_C_steps(self.pe,x):self.pe._compute_local(N('C'),{},15,(5,))
        self.assertEqual(x[0]['input_channels'],[5])
    def test_channel_accepts_list(self):
        x=[]
        with t.observe_C_steps(self.pe,x):self.pe._compute_local(N('C'),{},15,[5])
        self.assertEqual(x[0]['input_channels'],[5])
    def test_channel_rejects_dict(self):
        with self.assertRaisesRegex(t.GateError,'C_COMPUTE_CHANNELS_INVALID'):
            with t.observe_C_steps(self.pe,[]):self.pe._compute_local(N('C'),{},15,{4:1})
    def test_strict_C(self):
        x=[]
        with t.observe_C_steps(self.pe,x):self.pe._compute_local(N('c'),{},15,(3,))
        self.assertEqual(x,[])
    def test_bounded(self):
        rows=[]
        with self.assertRaisesRegex(t.GateError,'C_COMPUTE_OBSERVATION_OVERFLOW'):
            with t.observe_C_steps(self.pe,rows):
                for _ in range(t.MAX_C_OBSERVATIONS_PER_CASE+1):
                    self.pe._compute_local(N('C'),{},15,(4,))
    def test_no_C_fail_closed(self):
        with self.assertRaisesRegex(t.GateError,'C_NOT_EXECUTED_INSIDE_BV_SOURCE'):
            t.observe_once(lambda m,a:self.pe._compute_local(N('B'),{},15,(4,)),self.pe,None,'x')
    def test_no_late_C_fail_closed(self):
        with self.assertRaisesRegex(t.GateError,'C_LATE_STEP_NOT_OBSERVED'):
            t.observe_once(lambda m,a:self.pe._compute_local(N('C'),{},5,(4,)),self.pe,None,'x')
    def test_live_once(self):
        result,ev=t.observe_once(lambda m,a:self.pe._compute_local(N('C'),{},15,(5,)),self.pe,None,'x')
        self.assertEqual(len(ev),1);self.assertEqual(result,('C',{},15,(5,)))
    def test_canon_stable(self):self.assertEqual(t.canon({'b':1,'a':2}),t.canon({'a':2,'b':1}))
    def test_checksum_stable(self):self.assertEqual(t.checksum({'x':1}),t.checksum({'x':1}))
    def test_checksum_negative(self):self.assertNotEqual(t.checksum({'x':1}),t.checksum({'x':2}))
    def test_report_missing_unsafe(self):
        with self.assertRaisesRegex(t.GateError,'REPORT_PATH_ALREADY_EXISTS'):
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'out.json';p.write_text('x')
                t.write_once(p,{})
    def test_write_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'out.json';t.write_once(p,{'native_learning_proven':False})
            self.assertFalse(json.loads(p.read_text())['native_learning_proven'])
    def test_source_archive_pin_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(t.GateError,'FROZEN_SOURCE_CHANGED'):
                t.snapshot_two(tmp,Path(tmp)/'out.tar.gz')
    def test_case_row_observer_posthoc_not_native(self):
        fake_ghi=types.SimpleNamespace(digest=lambda z:'abc',observe_forward_result=lambda z:{
            'C_sign_candidate_from_same_source_forward_output':1,'event_candidate_paths':{'C':{'channel':11}}})
        ident={'failure':'none','arm':'current','context':'00','C_sensor':True}
        prior={'index':0,**ident,'source_sha256':'abc','C_sign_candidate_from_same_source_forward_output':1,
               'event_candidate_paths':{'C':{'channel':11}}}
        x=t.case_row(0,ident,None,'current',prior,{},[{'timestamp':15,'returned_type':'tuple','input_channels':[4]}],fake_ghi)
        self.assertEqual(x['source_sign_observed_posthoc'],1)
        self.assertFalse(x['native_C_packet_origin_verified'])
    def test_case_row_wrong_sign(self):
        fake_ghi=types.SimpleNamespace(digest=lambda z:'abc',observe_forward_result=lambda z:{
            'C_sign_candidate_from_same_source_forward_output':-1,'event_candidate_paths':{}})
        ident={'failure':'none','arm':'current','context':'00','C_sensor':False}
        prior={'index':0,**ident,'source_sha256':'abc','C_sign_candidate_from_same_source_forward_output':1,
               'event_candidate_paths':{}}
        with self.assertRaisesRegex(t.GateError,'SOURCE_SIGN_OBSERVATION_DRIFT'):
            t.case_row(0,ident,None,'current',prior,{},[],fake_ghi)
    def test_case_row_digest_mismatch(self):
        fake_ghi=types.SimpleNamespace(digest=lambda z:'invalid')
        ident={'failure':'none','arm':'current','context':'00','C_sensor':False}
        prior={'index':0,**ident,'source_sha256':'abc'}
        with self.assertRaisesRegex(t.GateError,'SOURCE_BYTE_PARITY_DRIFT'):
            t.case_row(0,ident,None,'current',prior,{},[],fake_ghi)
    def test_case_row_order_mismatch(self):
        ident={'failure':'none','arm':'current','context':'00','C_sensor':False}
        with self.assertRaisesRegex(t.GateError,'CASE_ORDER_DRIFT'):
            t.case_row(0,ident,None,'current',{'index':1},None,[],None)
    def test_case_row_recipe_mismatch(self):
        ident={'failure':'none','arm':'current','context':'00','C_sensor':False}
        with self.assertRaisesRegex(t.GateError,'MEASUREMENT_RECIPE_DRIFT'):
            t.case_row(0,ident,None,'current',{'index':0,'failure':'no_C','arm':'current','context':'00','C_sensor':False},None,[],None)

if __name__=='__main__':unittest.main()
