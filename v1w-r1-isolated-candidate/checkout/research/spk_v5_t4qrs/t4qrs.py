#!/usr/bin/env python3
"""T4QRS experimental process-separated receiver port (research only).

Q: actual one-pass frozen BV source produced in a separate Python process,
   C-channel sign read from *returned* source record by an adapter.
R: process-separated B relay of one-time committed packets.
S: receiver A checks commitment, sender/result/route constraints and anti-replay,
   writes its own ledger, and rejects mutations and unapproved episodes.

A SHA-256 precommit is not a signed native-neuron-origin message. Trusted
commissioning of commitments remains under host control. This program does
NOT demonstrate neuron C authority, native BV receipt or learning.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import secrets
import sys

SCHEMA='spk-v5-t4qrs-actor-receiver-port/research-v0'
PACKET_SCHEMA='spk-v5-t4qrs-semantic-adapter-packet/research-v0'
ENROLL_SCHEMA='spk-v5-t4qrs-host-commissioned-precommit/research-v0'
REF_SHA='32fe39cdd994c02b653e88f99887d989539ba32a9910b805884c7ab439d9b974'
STATUS='PROCESS_SEPARATED_RECEIVER_RESEARCH_COMMIT_NOT_NATIVE_C'
ELIGIBLE='RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT'
PINNED_SOURCE_ROWS=180
EXPECTED_COMMIT=24
SOURCE_KIND='C_OUTPUT_OBSERVED_BY_PYTHON_ADAPTER'
MSG_KEYS={'schema','case_index','source_sha256','semantic_sign','source_kind',
          'emissions','delivery_routes','recipient'}
PROOF_DOMAIN=b'SPK-T4QRS-HOST-COMMISSIONED-PRECOMMIT-v0\x00'
class GateError(ValueError):pass

def need(cond,code):
    if not cond:raise GateError(code)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(v):return sha256(canonical(v)).hexdigest()
def sha(path):return sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path=Path(path)
    need(not path.exists() and not path.is_symlink(),'OUTPUT_EXISTS:'+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def read(path):return json.loads(Path(path).read_bytes())

def load_reference(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),'T4NOP_REFERENCE_ABSENT')
    need(sha(p)==REF_SHA,'T4NOP_REFERENCE_SHA_DRIFT')
    r=read(p)
    need(r.get('schema')=='spk-v5-t4nop-receiver-boundary/research-v0' and
         r.get('status')=='RECEIVER_SEMANTIC_BOUNDARY_OBSERVED_BUT_NOT_AUTHENTICATED','T4NOP_SCHEMA_OR_STATUS_DRIFT')
    need(r.get('O_case_count')==180 and r.get('O_single_source_BV_calls')==180 and
         r.get('O_sign_observations')==72 and r.get('O_research_guard_count')==24 and
         r.get('P_native_semantic_credit_accepted')==0,'T4NOP_COUNTS_DRIFT')
    need(all(r.get(x) is False for x in ('native_receiver_semantic_receipt_proven','native_learning_proven','promotion_allowed')),'T4NOP_UNSAFE_PROMOTION')
    rows=r.get('O_rows')
    need(type(rows) is list and len(rows)==180,'T4NOP_ROWS_DRIFT')
    counts=Counter()
    for i,x in enumerate(rows):
        need(type(x) is dict and x.get('index')==i,'T4NOP_CASE_ORDER_DRIFT')
        need(x.get('receipt_sign_verified') is False and x.get('native_source_authentication_verified') is False and x.get('native_receiver_semantic_credit') is False,'T4NOP_ROW_UNSAFE_PROMOTION')
        need(type(x.get('source_sha256')) is str and len(x['source_sha256'])==64,'T4NOP_RESULT_SHA_INVALID')
        need(x.get('research_classification') in ('NO_SOURCE_SIGN','NO_CAUSAL_EMISSION_TRIPLE','APPLICATION_FORWARD_GUARD_BLOCK',ELIGIBLE),'T4NOP_CLASS_UNEXPECTED')
        counts[x['research_classification']]+=1
    need(counts==Counter({'NO_SOURCE_SIGN':108,'NO_CAUSAL_EMISSION_TRIPLE':24,'APPLICATION_FORWARD_GUARD_BLOCK':24,ELIGIBLE:24}), 'T4NOP_PARTITION_DRIFT')
    return r

def precommit(payload,token):
    need(type(token) is str and len(token)==64,'TOKEN_FORMAT_INVALID')
    try: proof=bytes.fromhex(token)
    except ValueError:raise GateError('TOKEN_HEX_INVALID')
    need(len(proof)==32,'TOKEN_LENGTH_INVALID')
    return sha256(PROOF_DOMAIN+canonical(payload)+proof).hexdigest()

def events_packet(i,src_sha,obs):
    s=obs['C_sign_candidate_from_same_source_forward_output']
    need(type(s) is int and s in (1,-1),'C_SIGN_NOT_PRESENT')
    need(obs['C_B_A_emission_candidate_consistent'] is True,'C_B_A_EVENTS_NOT_CONSISTENT')
    es=obs['event_candidate_paths']
    need(set(es)=={'C','B','A'},'EVENT_ROLES_INVALID')
    emissions=[]
    for role in ('C','B','A'):
        x=es[role];need(type(x) is dict and type(x['timestamp']) is int and type(x['channel']) is int,'EVENT_INVALID_'+role)
        emissions.append({'role':role,'timestamp':x['timestamp'],'channel':x['channel']})
    return {'schema':PACKET_SCHEMA,'case_index':i,'source_sha256':src_sha,
            'semantic_sign':s,'source_kind':SOURCE_KIND,'emissions':emissions,
            'delivery_routes':[['C','B'],['B','A']],'recipient':'A'}

def validate_packet_structure(packet,row):
    need(type(packet) is dict and set(packet)==MSG_KEYS,'PACKET_KEYS_INVALID')
    need(packet['schema']==PACKET_SCHEMA and packet['source_kind']==SOURCE_KIND,'PACKET_SOURCE_KIND_INVALID')
    i=packet['case_index']
    need(type(i) is int and i==row['index'],'PACKET_CASE_INDEX_INVALID')
    need(packet['source_sha256']==row['source_sha256'],'PACKET_SOURCE_SHA_MISMATCH')
    s=packet['semantic_sign']
    need(type(s) is int and s in (-1,1) and s==row['observed_sign'],'PACKET_SIGN_NOT_SOURCE_BOUND')
    need(packet['recipient']=='A' and packet['delivery_routes']==[['C','B'],['B','A']],'PACKET_ROUTE_INVALID')
    emissions=packet['emissions']
    need(type(emissions) is list and len(emissions)==3,'PACKET_EMISSIONS_INVALID')
    for j,role in enumerate(('C','B','A')):
        x=emissions[j]
        need(type(x) is dict and set(x)=={'role','timestamp','channel'} and x['role']==role and
             type(x['timestamp']) is int and type(x['channel']) is int,'PACKET_EVENT_INVALID_'+role)
    c,b,a=emissions
    need((c['channel'],b['channel'],a['channel'])==((11,13,13) if s==1 else (12,14,14)), 'PACKET_SEMANTIC_CHANNEL_MISMATCH')
    need(c['timestamp']<b['timestamp']<a['timestamp'],'PACKET_ORDER_INVALID')
    need(row['research_classification']==ELIGIBLE,'PACKET_NOT_GUARD_ELIGIBLE')
    need(row['delivery_routes']==[['C','B'],['B','A']] and row['delivery_count']==2,'REFERENCE_DELIVERY_ROUTE_MISSING')
    return True

class AReceiver:
    """Receiver owns a local ledger; host-commissioned enrollment NOT C authority."""
    def __init__(self,reference,enrollment):
        self.ref=reference
        need(type(enrollment) is dict and enrollment.get('schema')==ENROLL_SCHEMA,'ENROLL_SCHEMA_INVALID')
        self.commits=enrollment.get('commitments')
        need(type(self.commits) is dict and len(self.commits)==EXPECTED_COMMIT,'ENROLL_COUNT_INVALID')
        elig={str(r['index']) for r in reference['O_rows'] if r['research_classification']==ELIGIBLE}
        need(set(self.commits)==elig,'ENROLL_GUARD_COVERAGE_MISMATCH')
        need(all(type(x) is str and len(x)==64 and all(ch in '0123456789abcdef' for ch in x) for x in self.commits.values()),'ENROLL_COMMIT_FORMAT_INVALID')
        need(len(set(self.commits.values()))==EXPECTED_COMMIT,'ENROLL_DUPLICATE_COMMITMENT')
        self.ledger={};self.tokens=set()
    def accept(self,envelope):
        need(type(envelope) is dict and set(envelope)=={'hop','payload','token'},'ENVELOPE_INVALID')
        need(envelope['hop']=='B_TO_A_RESEARCH_RELAY','RELAY_HOP_INVALID')
        packet=envelope['payload'];need(type(packet) is dict,'PACKET_NOT_MAPPING')
        idx=packet.get('case_index');need(type(idx) is int and 0<=idx<180,'CASE_INDEX_OUT_OF_RANGE')
        need(idx not in self.ledger,'REPLAY_CASE_REJECTED')
        r=self.ref['O_rows'][idx]
        need(str(idx) in self.commits,'CASE_NOT_COMMISSIONED')
        validate_packet_structure(packet,r)
        token=envelope['token']
        need(token not in self.tokens,'REPLAY_TOKEN_REJECTED')
        need(precommit(packet,token)==self.commits[str(idx)],'COMMITMENT_PROOF_MISMATCH')
        self.ledger[idx]={'case_index':idx,'semantic_sign':packet['semantic_sign'],
                          'source_sha256':r['source_sha256'],'message_sha256':digest(packet),
                          'admission':'RESEARCH_RECEIVER_PROCESS_COMMIT_NOT_NATIVE'}
        self.tokens.add(token)
        return self.ledger[idx]

def forge_probes(receiver,envelopes):
    """Mutations are exercised on non-committing probes; all must reject."""
    import copy
    good=envelopes[0];probe={}
    def blocked(tag,attack):
        try:receiver.accept(attack)
        except GateError as err:probe[tag]=str(err)
        else:raise GateError('ATTACK_WAS_ACCEPTED:'+tag)
    e=copy.deepcopy(good);e['payload']['semantic_sign']*=-1;blocked('sign_flip',e)
    e=copy.deepcopy(good);e['payload']['source_sha256']='f'*64;blocked('source_swap',e)
    e=copy.deepcopy(good);e['payload']['emissions'][1]['channel']=14 if e['payload']['semantic_sign']==1 else 13;blocked('B_channel_swap',e)
    e=copy.deepcopy(good);e['payload']['emissions'][2]['timestamp']=e['payload']['emissions'][0]['timestamp'];blocked('causal_order',e)
    e=copy.deepcopy(good);e['payload']['delivery_routes']=[['C','A']];blocked('route',e)
    e=copy.deepcopy(good);e['payload']['case_index']=3;blocked('no_forward_forced',e)
    e=copy.deepcopy(good);e['payload']['case_index']=4;blocked('no_reverse_forced',e)
    e=copy.deepcopy(good);e['payload']['case_index']=1;blocked('no_C_forced',e)
    e=copy.deepcopy(good);e['token']='0'*64;blocked('proof_forgery',e)
    e=copy.deepcopy(good);e['hop']='C_TO_A_DIRECT';blocked('bypass_B',e)
    e=copy.deepcopy(good);e['payload']['source_kind']='C_NATIVE_NEURON';blocked('native_authority_forgery',e)
    e=copy.deepcopy(good);e['payload']['new_authenticator']='host';blocked('new_field_forgery',e)
    need(not receiver.ledger,'ATTACK_SIDE_EFFECT')
    return probe

def producer(root,ref_path,out_dir):
    from research.spk_v5_t4nop import t4nop
    from research.spk_v5_t4ghi import t4ghi
    from research.spk_v5_t4jkl_fix import t4jkl_fix
    ref=load_reference(ref_path)
    pins=t4nop.custody(root,t4nop.load_reference(Path(root)/'research/spk_v5_t4nop/reference/t4jklm-control-flag.json'))
    need(pins==ref['N_source_pins'],'ROOT_SOURCE_PIN_DRIFT')
    ghi=t4jkl_fix.reference(Path(root)/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json')
    need(len(ghi['H_rows'])==180,'GHI_REFERENCE_INCOMPLETE')
    commitments={};out=[];counts=Counter();source_calls=0
    for i,((ident,m,arm),historic,prior) in enumerate(zip(
          t4ghi.prev.table_cases(),ghi['H_rows'],ref['O_rows'])):
        need(ident['failure']==historic['failure'] and ident['arm']==historic['arm'] and prior['index']==i,
             'SOURCE_CASE_RECIPE_DRIFT_'+str(i))
        actual=t4ghi.source_once(m,arm)
        source_calls+=1;dgst=t4ghi.digest(actual)
        need(dgst==historic['source_sha256']==prior['source_sha256'],'SOURCE_REEXECUTION_PARITY_'+str(i))
        obs=t4ghi.observe_forward_result(actual)
        need(obs['C_sign_candidate_from_same_source_forward_output']==prior['observed_sign'] and
             obs['event_candidate_paths']==historic['event_candidate_paths'],'SOURCE_EVENT_DRIFT_'+str(i))
        counts[prior['research_classification']]+=1
        if prior['research_classification']!=ELIGIBLE:continue
        need(m.send_decision and m.forward_enabled and m.reverse_enabled,'SOURCE_RECIPE_DISABLED_'+str(i))
        pkt=events_packet(i,dgst,obs)
        validate_packet_structure(pkt,prior)
        token=secrets.token_hex(32)
        commitments[str(i)]=precommit(pkt,token)
        out.append({'payload':pkt,'token':token})
    need(source_calls==180 and len(out)==24,'PRODUCER_CARDINALITY_INVALID')
    need(counts==Counter(ref['O_classification_counts']),'PRODUCER_CLASS_PARTITION_DRIFT')
    need(t4nop.custody(root,t4nop.load_reference(Path(root)/'research/spk_v5_t4nop/reference/t4jklm-control-flag.json'))==pins,'CUSTODY_CHANGED')
    enroll={'schema':ENROLL_SCHEMA,'boundary':'HOST_TRUSTED_BOOTSTRAP_NOT_NATIVE_C_AUTHORITY',
            'commitments':commitments,'reference_sha256':REF_SHA}
    write(out_dir/'enrollment.json',enroll)
    write(out_dir/'producer-outbox.json',{'messages':out,'schema':'spk-v5-t4qrs-C-adapter-outbox/research-v0'})
    write(out_dir/'producer-summary.json',{'original_BV_calls':source_calls,'guard_selected':len(out),
          'classification_counts':dict(sorted(counts.items())),
          'semantic_signs':dict(sorted(Counter(str(x['payload']['semantic_sign']) for x in out).items())),
          'source_pin_count':len(pins),'adapter_is_not_native_C':True})

def relay(out_dir):
    o=read(out_dir/'producer-outbox.json');need(o.get('schema')=='spk-v5-t4qrs-C-adapter-outbox/research-v0','OUTBOX_SCHEMA_INVALID')
    messages=o.get('messages')
    need(type(messages) is list and len(messages)==24,'OUTBOX_COUNT_INVALID')
    # B cannot mutate the committed payload or proof without detection by A.
    wire=[{'hop':'B_TO_A_RESEARCH_RELAY',**msg} for msg in messages]
    write(out_dir/'relay-outbox.json',{'schema':'spk-v5-t4qrs-B-relay-outbox/research-v0','messages':wire})

def receiver(ref_path,out_dir):
    ref=load_reference(ref_path)
    enrollment=read(out_dir/'enrollment.json')
    need(enrollment.get('reference_sha256')==REF_SHA,'COMMISSIONING_REFERENCE_SHA_DRIFT')
    wire=read(out_dir/'relay-outbox.json')
    need(wire.get('schema')=='spk-v5-t4qrs-B-relay-outbox/research-v0' and type(wire.get('messages')) is list and len(wire['messages'])==24,'RELAY_SCHEMA_OR_COUNT_INVALID')
    rr=AReceiver(ref,enrollment)
    attacks=forge_probes(rr,wire['messages'])
    for msg in wire['messages']:rr.accept(msg)
    try:rr.accept(wire['messages'][0])
    except GateError as ex: attacks['accepted_replay']=str(ex)
    else:raise GateError('REPLAY_ACCEPTED')
    need(len(rr.ledger)==24 and len(attacks)==13,'RECEIVER_ADMISSION_OR_NEGATIVE_COUNT_DRIFT')
    receipt={'schema':'spk-v5-t4qrs-receiver-ledger/research-v0',
             'accepted':len(rr.ledger),'attacks_rejected':attacks,
             'entries':[rr.ledger[i] for i in sorted(rr.ledger)],
             'native_semantic_credit':0,'native_authentication_proven':False,
             'signed_C_neuron_packet_proven':False,'receiver_process_ledger_only':True,
             'trusted_bootstrap_owned_by_host':True}
    write(out_dir/'A-owned-ledger.json',receipt)

def audit(root,ref_path,out_dir,out):
    from research.spk_v5_t4nop import t4nop
    ref=load_reference(ref_path)
    own=read(out_dir/'A-owned-ledger.json');prod=read(out_dir/'producer-summary.json')
    need(prod['original_BV_calls']==180 and prod['guard_selected']==24 and prod['adapter_is_not_native_C'] is True,'PRODUCER_AUDIT_INVALID')
    need(own.get('accepted')==24 and len(own.get('entries',[]))==24 and len(own.get('attacks_rejected',{}))==13,'RECEIVER_AUDIT_INVALID')
    need(all(e['source_sha256']==ref['O_rows'][e['case_index']]['source_sha256'] for e in own['entries']),'RECEIVER_SOURCE_DRIFT')
    need(sum(e['semantic_sign']==1 for e in own['entries'])==12 and sum(e['semantic_sign']==-1 for e in own['entries'])==12,'SIGN_BALANCE_DRIFT')
    need(own['native_semantic_credit']==0 and own['native_authentication_proven'] is False and own['signed_C_neuron_packet_proven'] is False,'UNSAFE_PROMOTION')
    pins=t4nop.custody(root,t4nop.load_reference(Path(root)/'research/spk_v5_t4nop/reference/t4jklm-control-flag.json'))
    need(pins==ref['N_source_pins'],'SOURCE_CUSTODY_DRIFT')
    report={'schema':SCHEMA,'status':STATUS,'reference_sha256':REF_SHA,
            'producer':prod,'receiver':{'committed_count':24,'signs':{'positive':12,'negative':12},
                 'cases':[e['case_index'] for e in own['entries']],
                 'ledger_sha256':digest(own['entries']),'rejected_adversarial_count':13,
                 'rejection_reasons':own['attacks_rejected']},
            'processes_separated':['C-output-adapter','B-relay','A-receiver'],
            'source_pins':pins,'verified_result_parity_180':True,
            'host_commissioned_trust_boundary':True,'C_neuron_origin_authenticated':False,
            'BV_native_receiver_semantic_receipt':False,
            'native_learning_proven':False,'promotion_allowed':False,
            'limits':['A separate Python research process executes original scheduler and reads C sign from returned source data; it is not neuron C authoring a packet',
              'Commitments are bootstrapped by a host-controlled enrollment path; SHA-256 precommit binds bytes but does not prove native C identity',
              'B relays research packets, not scheduler-native C-to-B-to-A semantic payloads',
              'A-owned Python ledger is a process-local research port, not neuronal state or an SPK-native credit transaction',
              'No independently authenticated C sensor, external goal/reward truth or native learning']}
    write(out,report)
    print('T4QRS',STATUS,'BV sources',prod['original_BV_calls'],'A process commits',report['receiver']['committed_count'],'attacks rejected',13,'NATIVE RECEIPTS 0')
    print('SHA256',sha(out))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=('producer','relay','receiver','audit'))
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:
        if a.stage=='producer':producer(a.root,a.reference,a.work)
        elif a.stage=='relay':relay(a.work)
        elif a.stage=='receiver':receiver(a.reference,a.work)
        elif a.stage=='audit':
            need(a.out is not None,'OUTPUT_PATH_REQUIRED')
            audit(a.root,a.reference,a.work,a.out)
    except (GateError,ValueError,KeyError,TypeError,AssertionError,FileNotFoundError,OSError) as e:
        raise SystemExit('T4QRS FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
