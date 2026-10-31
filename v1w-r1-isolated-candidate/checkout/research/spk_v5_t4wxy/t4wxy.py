#!/usr/bin/env python3
"""T4WXY experimental isolated C-execution port, NOT native SPK C.

It builds an *additive reference engine*, not a monkeypatch or a replacement
for BV-v0e. C computes from host-supplied synthetic stimuli inside its own
execution step, then authors an envelope; B relays; A checks and commits.
The host provisions both C and A with the SAME HMAC key. Thus the host can
still forge an apparently valid C message, deliberately demonstrated here.
Nothing here proves independent C authority, native BV, or learning.
"""
from __future__ import annotations
import argparse
import copy
from hashlib import sha256
import hmac
import json
from pathlib import Path
import secrets
import subprocess
import sys
from collections import Counter

SCHEMA = 'spk-v5-t4wxy-C-context-execution-reference/research-v0'
PACKET_SCHEMA = 'spk-v5-t4wxy-C-context-packet/research-v0'
TUV_SHA = 'c9896293b6030820968217b1f628346e04377716c464b9dd971999a3140a339a'
STATUS = 'EXPERIMENTAL_C_CONTEXT_COMPUTE_AND_EMIT_HOST_PROVISIONED_NOT_NATIVE'
EXPECTED = 24
RESEARCH_ELIGIBLE = 'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT'
SOURCE_ID = 'EXPERIMENTAL_C_CONTEXT_NOT_FROZEN_SPK_NEURON'
DOMAIN = b'SPK-T4WXY-EXPERIMENTAL-HOST-KEYED-C-ENVELOPE-V0\0'

class GateError(ValueError): pass

def need(ok,why):
    if not ok: raise GateError(why)

def canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def checksum(obj): return sha256(canon(obj)).hexdigest()
def sha(path):return sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def write(path,obj):
    p=Path(path)
    need(not p.exists() and not p.is_symlink(),'OUTPUT_ALREADY_EXISTS')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')

def reference(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),'TUV_REFERENCE_MISSING_OR_SYMLINK')
    need(sha(p)==TUV_SHA,'TUV_REFERENCE_HASH_DRIFT')
    r=read(p)
    need(r.get('schema')=='spk-v5-t4tuv-host-authority-counterexample/research-v0' and
         r.get('status')=='HOST_CACHED_EVIDENCE_REPRODUCES_A_LEDGER_NO_C_ORIGIN','TUV_REFERENCE_SCHEMA_DRIFT')
    need(r.get('T_cached_source_invocations_this_run')==0 and
         r.get('T_A_process_accepted_cached_packets')==24 and
         r.get('U_natively_verified_semantic_receipts')==0 and
         r.get('native_learning_proven') is False and r.get('promotion_allowed') is False,
         'TUV_REFERENCE_UNSAFE')
    need(len(r.get('source_pins',{}))==12,'TUV_SOURCE_PINS_MISSING')
    return r

def fixtures(tuv,nominal):
    """Synthetic stimuli, made to exercise both polarities, NOT original C inputs.

    Historical 24 case indices are identifiers only. They cannot grant authority.
    The input +/- 3 is chosen locally by this harness, and not independently
    sensed. No source call occurs in this experimental protocol.
    """
    from research.spk_v5_t4qrs import t4qrs
    ref=t4qrs.load_reference(nominal)
    need(ref['N_source_pins']==tuv['source_pins'],'SOURCE_PIN_MISMATCH')
    rows=[r for r in ref['O_rows'] if r['research_classification']==RESEARCH_ELIGIBLE]
    need(len(rows)==EXPECTED,'CASE_SET_DRIFT')
    return [{'case_index':r['index'],'parent':f'SYNTHETIC_INPUT:{r["index"]}',
             'stimulus':[3 if j%2==0 else -3,0,0], 'tick':j+1}
             for j,r in enumerate(rows)]

def mac(key,body):return hmac.new(bytes.fromhex(key),DOMAIN+canon(body),'sha256').hexdigest()

def session_valid(session):
    need(type(session) is dict and set(session)=={'key','challenge'},'SESSION_FIELDS_INVALID')
    need(type(session['key']) is str and len(session['key'])==64 and
         all(c in '0123456789abcdef' for c in session['key']),'SESSION_KEY_INVALID')
    need(type(session['challenge']) is str and len(session['challenge'])==64 and
         all(c in '0123456789abcdef' for c in session['challenge']),'SESSION_CHALLENGE_INVALID')
    return session

def C_compute_and_emit(fixture,session):
    """The only issuer method of the experimental context. Python, not SPK C."""
    session_valid(session)
    need(type(fixture) is dict and set(fixture)=={'case_index','parent','stimulus','tick'},'STIMULUS_FIELDS_INVALID')
    i=fixture['case_index'];t=fixture['tick'];x=fixture['stimulus']
    need(type(i) is int and i>=0 and type(t) is int and t>0,'STIMULUS_INDEX_OR_TICK_INVALID')
    need(type(x) is list and len(x)==3 and all(type(n) is int for n in x),'STIMULUS_INVALID')
    need(type(fixture['parent']) is str and fixture['parent']==f'SYNTHETIC_INPUT:{i}','STIMULUS_PARENT_INVALID')
    computed=x[0]+x[1]-x[2]
    need(computed!=0,'C_ZERO_ACTIVATION_NO_EMISSION')
    sign=1 if computed>0 else -1
    body={'schema':PACKET_SCHEMA,'source_identity':'C','source_context_kind':SOURCE_ID,
          'semantic_sign':sign,'channel':11 if sign==1 else 12,
          'case_index':i,'tick':t,'causal_parent_id':fixture['parent'],
          'C_emission_id':f'EXP-C:{session["challenge"][:16]}:{i}:{t}',
          'execution_challenge':session['challenge']}
    return {'body':body,'authenticator':mac(session['key'],body)}

def B_relay(packets):
    out=[]
    for p in packets:
        need(type(p) is dict and set(p)=={'body','authenticator'},'B_PACKET_SHAPE_INVALID')
        # B never recomputes C semantics; only forwards exactly the same bytes.
        out.append({'route':['C','B','A'],'packet':p,
                    'B_forward_id':checksum({'original':p,'hop':'B_TO_A_RESEARCH'})})
    return out

class AReceiver:
    def __init__(self,session,case_ids):
        self.session=session_valid(session)
        self.allowed=set(case_ids)
        self.ledger={};self.seen=set()
    def accept(self,wrapped):
        need(type(wrapped) is dict and set(wrapped)=={'route','packet','B_forward_id'},'A_ENVELOPE_INVALID')
        need(wrapped['route']==['C','B','A'],'A_ROUTE_INVALID')
        p=wrapped['packet']
        need(type(p) is dict and set(p)=={'body','authenticator'},'A_PACKET_FIELDS_INVALID')
        body=p['body']
        need(type(body) is dict and set(body)=={'schema','source_identity','source_context_kind','semantic_sign','channel','case_index','tick','causal_parent_id','C_emission_id','execution_challenge'},'A_BODY_FIELDS_INVALID')
        need(body['schema']==PACKET_SCHEMA and body['source_identity']=='C' and
             body['source_context_kind']==SOURCE_ID,'A_SOURCE_CLAIM_INVALID')
        sign=body['semantic_sign']
        need(type(sign) is int and sign in (-1,1) and body['channel']==(11 if sign==1 else 12),'A_SIGN_CHANNEL_MISMATCH')
        idx=body['case_index'];tick=body['tick']
        need(type(idx) is int and idx in self.allowed and type(tick) is int and tick>0,'A_CASE_OR_TICK_INVALID')
        need(body['causal_parent_id']==f'SYNTHETIC_INPUT:{idx}' and
             body['C_emission_id']==f'EXP-C:{self.session["challenge"][:16]}:{idx}:{tick}',
             'A_CAUSAL_ANCESTRY_INVALID')
        need(body['execution_challenge']==self.session['challenge'],'A_STALE_EXECUTION_CHALLENGE')
        need(type(p['authenticator']) is str and hmac.compare_digest(p['authenticator'],mac(self.session['key'],body)),
             'A_AUTHENTICATOR_INVALID')
        need(wrapped['B_forward_id']==checksum({'original':p,'hop':'B_TO_A_RESEARCH'}),'A_RELAY_INTEGRITY_INVALID')
        need(idx not in self.ledger and body['C_emission_id'] not in self.seen,'A_REPLAY_REJECTED')
        # Admission is *research-process* state, not SPK native credit state.
        self.ledger[idx]={'case_index':idx,'semantic_sign':sign,
            'admission':'EXPERIMENTAL_REFERENCE_RECEIVER_ONLY'}
        self.seen.add(body['C_emission_id'])
        return self.ledger[idx]

def negative_cases(wrapped,session,case_ids):
    originals=wrapped[0];fails={}
    def verify(tag,fn):
        x=copy.deepcopy(originals);fn(x)
        fresh=AReceiver(session,case_ids)
        try:fresh.accept(x)
        except (GateError,KeyError,TypeError,ValueError) as e:fails[tag]=str(e)
        else:raise GateError('FORGED_CASE_ACCEPTED:'+tag)
    verify('sign_flip',lambda x:x['packet']['body'].__setitem__('semantic_sign',-x['packet']['body']['semantic_sign']))
    verify('channel_flip',lambda x:x['packet']['body'].__setitem__('channel',14))
    verify('fake_C_identity',lambda x:x['packet']['body'].__setitem__('source_identity','C_NATIVE'))
    verify('wrong_origin_kind',lambda x:x['packet']['body'].__setitem__('source_context_kind','SPK_NATIVE'))
    verify('stale_challenge',lambda x:x['packet']['body'].__setitem__('execution_challenge','f'*64))
    verify('wrong_parent',lambda x:x['packet']['body'].__setitem__('causal_parent_id','SYNTHETIC_INPUT:999'))
    verify('new_emission_id',lambda x:x['packet']['body'].__setitem__('C_emission_id','forged'))
    verify('wrong_route',lambda x:x.__setitem__('route',['C','A']))
    verify('B_relay_edit',lambda x:x['packet']['body'].__setitem__('tick',999))
    verify('packet_mac_tamper',lambda x:x['packet'].__setitem__('authenticator','0'*64))
    verify('wrong_B_integrity',lambda x:x.__setitem__('B_forward_id','0'*64))
    verify('unselected_case',lambda x:x['packet']['body'].__setitem__('case_index',3))
    verify('QRS_archived_packet',lambda x:x['packet'].__setitem__('body',{'schema':'spk-v5-t4qrs-semantic-adapter-packet/research-v0'}))
    need(len(fails)==13,'ADVERSARIAL_COVERAGE_INVALID')
    return fails

def host_counterexample(session,fixture,case_ids):
    """Even this new receiver can be fooled by the host *with provisioning key*.

    Deliberately construct the message outside the experimental C process.
    MUST remain a counterexample, never an authentication PASS.
    """
    # A host can synthesize arbitrary effective inputs and invoke the same
    # publicly available envelope builder outside the original C process.
    pkt=C_compute_and_emit(fixture,session)
    fake=B_relay([pkt])[0]
    r=AReceiver(session,case_ids)
    r.accept(fake)
    need(len(r.ledger)==1,'HOST_AUTHORITY_COUNTEREXAMPLE_DISAPPEARED')
    return {'host_outside_C_can_forge':True,'host_fake_A_accepts':1,
            'issuer_process_provenance_authenticated':False}

def stage(stage,work):
    session=read(work/'session.json');inputs=read(work/'fixtures.json')
    session_valid(session)
    if stage=='c':
        write(work/'C-outbox.json',{'schema':'spk-v5-t4wxy-C-outbox/research-v0',
             'messages':[C_compute_and_emit(f,session) for f in inputs]})
    elif stage=='b':
        inp=read(work/'C-outbox.json')
        need(inp['schema']=='spk-v5-t4wxy-C-outbox/research-v0','C_OUTBOX_SCHEMA_INVALID')
        write(work/'B-outbox.json',{'schema':'spk-v5-t4wxy-B-outbox/research-v0',
             'messages':B_relay(inp['messages'])})
    elif stage=='a':
        inp=read(work/'B-outbox.json')
        need(inp['schema']=='spk-v5-t4wxy-B-outbox/research-v0','B_OUTBOX_SCHEMA_INVALID')
        ids=[f['case_index'] for f in inputs]
        recv=AReceiver(session,ids)
        rejects=negative_cases(inp['messages'],session,ids)
        for w in inp['messages']:recv.accept(w)
        try:recv.accept(inp['messages'][0])
        except GateError as e:rejects['accepted_replay']=str(e)
        else:raise GateError('A_REPLAY_WAS_ACCEPTED')
        need(len(recv.ledger)==EXPECTED and len(rejects)==14,'A_COUNTS_INVALID')
        host=host_counterexample(session,inputs[0],ids)
        write(work/'A-receipt.json',{'accepted':len(recv.ledger),
             'positive':sum(r['semantic_sign']==1 for r in recv.ledger.values()),
             'negative':sum(r['semantic_sign']==-1 for r in recv.ledger.values()),
             'rejections':rejects,'host_counterexample':host,
             'ledger_digest':checksum([recv.ledger[i] for i in sorted(recv.ledger)])})
    else:raise GateError('UNSUPPORTED_STAGE')

def run(root,reference_path,output):
    # Actual original scheduler is NOT invoked. This is a reference contract.
    import tempfile
    tuv=reference(reference_path)
    nominal=Path(root)/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json'
    stimuli=fixtures(tuv,nominal)
    need(len(stimuli)==EXPECTED,'NO_FIXTURES')
    with tempfile.TemporaryDirectory(prefix='spk-v5-t4wxy-') as temp:
        w=Path(temp);w.chmod(0o700)
        sess={'key':secrets.token_hex(32),'challenge':secrets.token_hex(32)}
        write(w/'session.json',sess);write(w/'fixtures.json',stimuli)
        pid_list=[]
        for cmd in ('c','b','a'):
            p=subprocess.run([sys.executable,str(Path(__file__).resolve()),'stage',cmd,'--work',str(w)],
                  cwd=root,text=True,capture_output=True)
            need(p.returncode==0,'PROCESS_'+cmd.upper()+'_FAILED:'+p.stderr[-350:])
            pid_list.append(cmd)
        recv=read(w/'A-receipt.json')
        need(recv['accepted']==EXPECTED and recv['positive']==12 and recv['negative']==12,'RECEIVER_COUNT_DRIFT')
        need(recv['host_counterexample']['host_outside_C_can_forge'] is True,'HOST_FORGERY_NOT_DEMONSTRATED')
        report={'schema':SCHEMA,'status':STATUS,'T4TUV_reference_sha256':TUV_SHA,
            'W_original_BV_scheduler_calls':0,'W_reference_C_compute_steps':EXPECTED,
            'W_synthetic_input_count':EXPECTED,'W_frozen_runtime_modified':False,
            'X_separate_python_process_stages':pid_list,
            'X_receiver_process_commits':recv['accepted'],
            'X_positive':recv['positive'],'X_negative':recv['negative'],
            'X_adversarial_rejections':len(recv['rejections']),
            'X_rejection_reasons':recv['rejections'],
            'Y_host_can_forge_even_with_reference_C_context':recv['host_counterexample'],
            'Y_native_neuron_identity_verified':False,
            'Y_native_BV_semantic_receipts':0,'Y_native_learning':False,
            'source_pins':tuv['source_pins'],'promotion_allowed':False,
            'limits':['The 24 stimuli are synthetic fixture values, not independent sensors or native C computation',
                'The experimental C Python process runs its own C_compute_and_emit, not frozen BV-v0e execute_live_v0e',
                'Source snapshots are used for selecting cases and static custody only',
                'The host provisions the HMAC key and can forge fresh C packets. A valid MAC is NOT native neuron identity',
                'B and A are Python research processes, not SPK neuronal PE-owned transactions',
                'No frozen scheduler integration, no native semantic back validation, no learning update']}
        write(output,report)
        print('T4WXY',STATUS,'synthetic C steps',EXPECTED,'A commits',recv['accepted'],
              'rejections',len(recv['rejections']),'HOST FORGERY STILL POSSIBLE')
        print('sha256',sha(output))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    st=sub.add_parser('stage');st.add_argument('stage',choices=('c','b','a'));st.add_argument('--work',type=Path,required=True)
    rn=sub.add_parser('run');rn.add_argument('--root',type=Path,required=True)
    rn.add_argument('--reference',type=Path,required=True);rn.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.command=='stage':stage(args.stage,args.work)
        else:run(args.root.resolve(),args.reference,args.out)
    except (GateError,KeyError,ValueError,TypeError,FileNotFoundError,OSError) as e:
        raise SystemExit('T4WXY FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
