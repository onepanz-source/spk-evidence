"""T5GHI: A-owned freshness, C PE-scope binding, and unavoidable privileged-host rebind.

A's process protects against unmodified replay, but the host can impersonate
C with an existing computation plus a freshly visible challenge. Research only.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import difflib
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from research.spk_v5_t5abc import t5abc
from research.spk_v5_t5def import t5def
from research.spk_v5_t5ghi.challenge_contract_v0 import challenge_digest

SCHEMA='spk-v5-t5ghi-receiver-freshness-pe-scope/research-v0'
STATUS='RECEIVER_FRESHNESS_REPLAY_BLOCKED_PRIVILEGED_HOST_CAN_REBIND_NOT_NATIVE'
REF_SHA='e5e966c7692a839cee0cc5575f031bfde2c7d02e5b3ca29ed41f3d97f0674e55'
PARENT_FORK_SHA='22fcdd3c8de9ec029fb8ae32b53e37fd434ad1b1460fb3226a0a5a735e5fe585'

class GateError(ValueError):pass

def need(cond,code):
    if not cond:raise GateError(code)

def sha_file(p):return sha256(Path(p).read_bytes()).hexdigest()

def custody(root):
    r=Path(root);p=r/'research/spk_v5_t5ghi'
    old=r/'research/spk_v5_t5def/live_pe_issuer_fork_v0.py'
    new=p/'live_challenge_fork_v0.py'
    need(sha_file(old)==PARENT_FORK_SHA,'PARENT_FORK_DRIFT')
    patch=''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),
        fromfile='research/spk_v5_t5def/live_pe_issuer_fork_v0.py',tofile='research/spk_v5_t5ghi/live_challenge_fork_v0.py'))
    need(patch==(p/'FORK_DIFF.patch').read_text(),'CHALLENGE_FORK_PATCH_DRIFT')
    prev=t5def.check_custody(r)
    need(prev['experimental_fork_sha256']==PARENT_FORK_SHA,'PARENT_CUSTODY_DRIFT')
    # No unstated changes to frozen PE or BV; old custody verifies their exact SHA.
    return {'T5DEF_fork_sha256':PARENT_FORK_SHA, 'challenge_fork_sha256':sha_file(new),
        'challenge_PE_sha256':sha_file(p/'pe_challenge_issuer_v0.py'),
        'A_process_sha256':sha_file(p/'receiver_authority_v0.py'),
        'fork_diff_sha256':sha_file(p/'FORK_DIFF.patch'),
        'frozen_BV_sha256':t5abc.FROZEN_SHA,'frozen_PE_sha256':t5abc.FROZEN_PE_SHA}

class AProcess:
    def __init__(self):
        self.p=subprocess.Popen([sys.executable,'-u','-m','research.spk_v5_t5ghi.receiver_authority_v0'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.seen_nonces=set()
    def cmd(self,**values):
        need(self.p.poll() is None,'A_PROCESS_DIED')
        self.p.stdin.write(json.dumps(values,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
        self.p.stdin.flush()
        response=self.p.stdout.readline()
        need(bool(response),'A_PROCESS_NO_RESPONSE')
        return json.loads(response)
    def issue(self,idx):
        response=self.cmd(op='issue',case_index=idx)
        need(response.get('ok') is True,'A_CHALLENGE_ISSUE_FAILED')
        challenge=response['challenge'];need(challenge['nonce'] not in self.seen_nonces,'A_NONCE_COLLISION')
        self.seen_nonces.add(challenge['nonce'])
        return challenge
    def verify(self,idx,issuance,receipt):
        return self.cmd(op='verify',case_index=idx,issuance=issuance,receipt=receipt)
    def expire(self,idx):
        return self.cmd(op='expire',case_index=idx)
    def stats(self):return self.cmd(op='stats')
    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close();self.p.wait(timeout=10)
        self.p.stdout.close();self.p.stderr.close()
        need(self.p.returncode==0,'A_PROCESS_EXIT_NONZERO')


def strip_challenge(x):
    if isinstance(x,dict):return {k:strip_challenge(v) for k,v in x.items() if k!='challenge_digest'}
    if isinstance(x,list):return [strip_challenge(v) for v in x]
    return x


def run_source(m,arm,challenge):
    from research.spk_v5_t4def import t4def
    from spk_v5_research.island_c_owned_credit_v5t3h import build_case
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from research.spk_v5_t5ghi.live_challenge_fork_v0 import execute_live_v0e,LiveBVPlanV0e
    case=t4def.fixed_terminal_case(m,arm,build_case)
    fabric=plan_v1a(case,'spread')
    return execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='C',terminal_channel=30,max_ticks=256),
        receiver_challenge=challenge)


def host_rebind_witness(m,arm,expected_row):
    """Host can forge an A-fresh answer by reusing C's old compute output."""
    from research.spk_v5_t5ghi import live_challenge_fork_v0 as fork
    authority=AProcess();original=fork.compute_and_issue;cache=[];used=Counter()
    try:
        ch1=authority.issue(10000)
        def capture(node,*args):
            result=original(node,*args)
            if node.node_id=='C':cache.append(result)
            return result
        fork.compute_and_issue=capture
        initial=run_source(m,arm,ch1)
        need(len(cache)>0,'WITNESS_NO_ORIGINAL_C_STEP')
        port=initial['experimental_semantic_port']
        need(authority.verify(10000,port['issuances'][0],port['receiver_A_sign_receipts'][0])['ok'] is True,
             'WITNESS_ORIGINAL_A_DENIED')
        ch2=authority.issue(10001)
        q=iter(cache)
        def forged_with_fresh_digest(node,*args):
            if node.node_id!='C':return original(node,*args)
            used['C_cache']+=1
            v=next(q)
            if v[3] is None:return v
            emission=replace(v[3], challenge_digest=challenge_digest(ch2,v[3].to_packet()))
            return (*v[:3],emission)
        fork.compute_and_issue=forged_with_fresh_digest
        replay=run_source(m,arm,ch2)
        need(used['C_cache']==len(cache),'HOST_REBIND_C_CACHE_COUNT_DRIFT')
        need(t5abc.canon(strip_challenge(initial))==t5abc.canon(strip_challenge(replay)),
             'HOST_REBIND_SCHEDULER_DIVERGENCE')
        port2=replay['experimental_semantic_port']
        need(authority.verify(10001,port2['issuances'][0],port2['receiver_A_sign_receipts'][0])['ok'] is True,
             'HOST_FORGERY_NOT_ACCEPTED')
        need(t5abc.digest(strip_challenge(port2))==expected_row['port_sha256'],'HOST_FORGERY_PORT_DRIFT')
        counts=authority.stats()
        need(counts['counts']['accepted']==2 and counts['counts']['issued']==2,'HOST_WITNESS_A_COUNTS')
        return {'C_new_PE_computations':0,'cached_C_results_rebound':used['C_cache'],
                'fresh_challenge_accepted_by_A':True,'native_origin_attestation_falsified':True}
    finally:
        fork.compute_and_issue=original
        authority.close()


def run(root):
    from research.spk_v5_t4def import t4def
    from research.spk_v5_t5ghi import live_challenge_fork_v0 as fork
    r=Path(root);pins=custody(r)
    ref=t5abc.read_pinned(r/'research/spk_v5_t5ghi/reference/t5def-pe-scope-issuer.json',
                          REF_SHA,'T5DEF_PASS_REFERENCE')
    need(ref['experimental_fork_cases']==180 and ref['PE_scope_compute_steps']==1002 and
         ref['C_PE_compute_steps']==312 and ref['PE_scope_sign_issuances']==72 and
         ref['A_sign_receipts']==72 and ref['research_guard_only_cases']==24 and
         ref['host_can_forge_runtime'] is True,'T5DEF_REFERENCE_INVALID')
    auth=AProcess(); counts=Counter(); rows=[]; attacks=Counter(); original=fork.compute_and_issue
    def observe(node,*args):
        res=original(node,*args)
        counts['pe']+=1
        if node.node_id=='C':counts['c']+=1
        if res[3] is not None:counts['issue']+=1
        return res
    try:
        fork.compute_and_issue=observe
        for index,((meta,m,arm),old) in enumerate(zip(t4def.table_cases(),ref['rows'])):
            need(old['index']==index,'CASE_ORDER_DRIFT')
            challenge=auth.issue(index)
            result=run_source(m,arm,challenge)
            # Freshness binding alters ONLY additive semantic messages; all frozen
            # output and prior PE-scope semantics remain byte-exact.
            need(t5abc.digest(t5abc.strip_experimental(result))==old['source_sha256'],
                 'FROZEN_PARITY_FAIL_'+str(index))
            port=result['experimental_semantic_port']
            need(t5abc.digest(strip_challenge(port))==old['port_sha256'],
                 'T5DEF_PORT_PARITY_FAIL_'+str(index))
            issuance=port['issuances'];receipts=port['receiver_A_sign_receipts']
            need(len(issuance)==old['C_PE_issued'] and len(receipts)==old['A_received'],
                 'RECEIPT_COUNTS_DRIFT_'+str(index))
            if issuance:
                # Negative tests BEFORE consumption: mistaken case, modified
                # challenge commitment and stale receipt. They must not consume it.
                if index==0:
                    v=auth.verify(index+999999,issuance[0],receipts[0])
                    need(v['ok'] is False,'WRONG_CASE_ACCEPTED');attacks['wrong_case']+=1
                    forged=deepcopy(issuance[0]);forged['challenge_digest']='0'*64
                    v=auth.verify(index,forged,receipts[0])
                    need(v['ok'] is False,'WRONG_DIGEST_ACCEPTED');attacks['altered_digest']+=1
                    bad=deepcopy(receipts[0]);bad['sign']*=-1
                    v=auth.verify(index,issuance[0],bad)
                    need(v['ok'] is False,'TAMPERED_SIGN_ACCEPTED');attacks['altered_sign']+=1
                accepted=auth.verify(index,issuance[0],receipts[0])
                need(accepted.get('ok') is True and accepted.get('native_authenticated') is False,
                     'A_REJECTED_CURRENT_C_RECEIPT_'+str(index))
                if index==0:
                    v=auth.verify(index,issuance[0],receipts[0])
                    need(v['ok'] is False,'REPLAY_ACCEPTED');attacks['replay']+=1
            else:
                need(auth.expire(index)['ok'] is True,'A_CHALLENGE_CANCEL_FAIL')
            rows.append({'index':index,'source_sha256':old['source_sha256'],
                  'port_sha256':old['port_sha256'],'A_fresh_accept':bool(issuance),
                  'C_issued':len(issuance),'guard_only':old['guard_only'],
                  'native_credit':False})
        stats=auth.stats()
        need(stats['ok'] is True and stats['outstanding']==0,'A_CHALLENGES_NOT_CLOSED')
        s=stats['counts']
        need((s['issued'],s['accepted'],s['expired'],s['rejected'])==(180,72,108,4),
             'A_PROCESS_RECEIPT_COUNTS_DRIFT')
        need(len(auth.seen_nonces)==180,'RECEIVER_NONCE_REUSE')
    finally:
        fork.compute_and_issue=original
        auth.close()
    need((counts['pe'],counts['c'],counts['issue'])==(1002,312,72),'PE_COMPUTE_COUNTS_DRIFT')
    cases=list(t4def.table_cases())
    witness=host_rebind_witness(cases[0][1],cases[0][2],ref['rows'][0])
    need(custody(r)==pins,'CUSTODY_DRIFT_DURING_RUN')
    return {'schema':SCHEMA,'status':STATUS,'T5DEF_reference_sha256':REF_SHA,
            'pins':pins,'fork_cases':180,'original_frozen_BV_calls':0,
            'PE_steps':counts['pe'],'C_steps':counts['c'],'C_fresh_issuances':counts['issue'],
            'A_receiver_process_stats':s,'freshness_attack_rejections':dict(sorted(attacks.items())),
            'A_nonce_uniqueness_checked':True,'ephemeral_nonces_omitted_from_report':True,
            'all_180_source_and_T5DEF_port_sha_parity':True,
            'host_rebind_forgery_witness':witness,'host_can_forge_runtime':True,
            'native_C_authenticated':False,'native_BV_credit':False,'native_learning':False,
            'promotion_allowed':False,'rows_sha256':t5abc.digest(rows),'rows':rows,
            'limits':['Receiver A runs in a separate host-controlled Python process, uses unpredictable one-time challenges',
                      'PE-scope wrapper derives challenge binding during C compute, scheduler only relays',
                      'Receiver prevents stale challenge replay and tampering, not adversarial host recomputation',
                      'Privileged host can rebind cached C result to new challenge and pass A verification',
                      'No independent attestation, authenticated C sensor, native BV or learning']}


def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    args=a.parse_args()
    try:
        need(not args.out.exists(),'OUTPUT_ALREADY_EXISTS')
        d=run(args.root)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(json.dumps(d,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
        print('T5GHI',d['status'],'fork cases',d['fork_cases'],'A fresh accepts',d['A_receiver_process_stats']['accepted'],
              'rejections',d['A_receiver_process_stats']['rejected'],'HOST STILL CAN FORGE')
        print('sha256',sha_file(args.out))
    except (GateError,t5abc.GateError,t5def.GateError,ValueError,KeyError,TypeError,ImportError,OSError,AssertionError,StopIteration,subprocess.TimeoutExpired) as exc:
        raise SystemExit('T5GHI FAIL CLOSED: '+str(exc))

if __name__=='__main__':main()
