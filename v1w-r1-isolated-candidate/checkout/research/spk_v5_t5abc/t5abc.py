#!/usr/bin/env python3
"""T5ABC: real 180-case in-scheduler C semantic BV payload *research fork*.

This extends ONLY a copied, SHA-pinned BV-v0e scheduler. The frozen original
never changes. C's semantic sign comes from PE `_compute_local` outputs during
that SAME fork scheduler batch. Original BV carrier delivers the payload C->B->A.
Host still owns the execution and can counterfeit it: no native C authority.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import argparse, difflib, json

SCHEMA='spk-v5-t5abc-pe-output-bound-bv-transit/research-v0'
STATUS='IN_SCHEDULER_PE_OUTPUT_BOUND_BV_TO_A_RESEARCH_NOT_AUTHENTICATED'
T4ZABC_SHA='7de3ccc8c374212748ccedcbd1a4b3d4e99f116b9a6f39e0190695a746cf9d4c'
T4GHI_SHA='dc98a1a5e45270d665e5119540ae960e405f4d02b703bd0c52d04202873abef3'
FROZEN_SHA='2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
FROZEN_PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
MAX_BYTES=15_000_000

class GateError(ValueError): pass

def need(value, code):
    if not value: raise GateError(code)

def file_hash(path):return sha256(Path(path).read_bytes()).hexdigest()

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(x):return sha256(canon(x)).hexdigest()

def read_pinned(path, sha, label):
    p=Path(path)
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<MAX_BYTES, label+'_MISSING_OR_SIZE')
    need(file_hash(p)==sha,label+'_SHA_DRIFT')
    return json.loads(p.read_bytes())

def custodial_fork_check(root):
    root=Path(root)
    p=root/'research/spk_v5_t5abc'
    frozen=root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
    pe=root/'spk_architecture_v1/pe_execution_v1b.py'
    need(file_hash(frozen)==FROZEN_SHA,'FROZEN_BV_SOURCE_DRIFT')
    need(file_hash(pe)==FROZEN_PE_SHA,'FROZEN_PE_SOURCE_DRIFT')
    orig=frozen.read_text().splitlines(True)
    modified=(p/'live_semantic_fork_v0.py').read_text().splitlines(True)
    expected=''.join(difflib.unified_diff(orig,modified,
        fromfile='frozen/live_dual_scheduler_v0e.py',
        tofile='research/spk_v5_t5abc/live_semantic_fork_v0.py'))
    need(expected==(p/'FORK_DIFF.patch').read_text(),'FORK_DIFF_DRIFT')
    return {'frozen_BV_sha256':FROZEN_SHA,'frozen_PE_sha256':FROZEN_PE_SHA,
            'experimental_fork_sha256':file_hash(p/'live_semantic_fork_v0.py'),
            'fork_diff_sha256':file_hash(p/'FORK_DIFF.patch')}

def strip_experimental(result):
    need(type(result) is dict,'FORK_RESULT_INVALID')
    need('experimental_semantic_port' in result,'FORK_EXTENSION_MISSING')
    return {k:v for k,v in result.items() if k!='experimental_semantic_port'}

def check_port(source, expected_sign, expected_routes):
    port=source.get('experimental_semantic_port')
    need(isinstance(port,dict),'EXPERIMENTAL_PORT_MISSING')
    need(port.get('host_can_forge') is True and port.get('native_origin_authenticated') is False and
         port.get('native_receiver_semantic_credit') is False and port.get('native_learning') is False,
         'NATIVE_PROMOTION_FORBIDDEN')
    issuances=port.get('issuances'); hops=port.get('feedback_hops'); receipts=port.get('receiver_A_sign_receipts')
    need(isinstance(issuances,list) and isinstance(hops,list) and isinstance(receipts,list),
         'PORT_RECORDS_INVALID')
    signs={x['sign'] for x in issuances}
    need(len(issuances)==int(expected_sign is not None),'PE_C_ISSUANCE_COUNT_MISMATCH')
    need(signs==({expected_sign} if expected_sign is not None else set()),'PE_C_ISSUANCE_SIGN_MISMATCH')
    need(len(hops)==2*len(issuances),'SEMANTIC_HOP_COUNT_MISMATCH')
    need(len(receipts)==len(issuances),'A_RECEIPT_COUNT_MISMATCH')
    if issuances:
        i=issuances[0]
        need(i['C_source']=='C' and i['source_channel']==(11 if expected_sign==1 else 12) and
             i['tick']<hops[0]['tick']<hops[1]['tick'] and
             i['compute_batch']>=1 and bool(i['causal_parents']), 'C_COMPUTE_ISSUANCE_INVALID')
        need([(x['sender'],x['receiver']) for x in hops]==[('C','B'),('B','A')],
             'SEMANTIC_HOP_ROUTE_INVALID')
        need(all(x['sign']==expected_sign and x['C_emission_id']==i['C_emission_id'] and
                 x['receiver_authenticates_C'] is False for x in hops),
             'SEMANTIC_HOP_CUSTODY_MISMATCH')
        need(receipts[0]==hops[1], 'A_RECEIPT_NOT_FROM_DELIVERED_BV_PACKET')
        feedback=source['feedback']['deliveries']
        need([(x['sender'],x['receiver']) for x in feedback]==[('C','B'),('B','A')],
             'FROZEN_RECEIVER_ROUTES_DRIFT')
        need([x['packet_id'] for x in feedback]==[x['packet_id'] for x in hops],
             'SEMANTIC_CARRIER_PACKET_ID_DRIFT')
    need([(x['sender'],x['receiver']) for x in source['feedback']['deliveries']]==
         [tuple(r) for r in expected_routes], 'FROZEN_DELIVERY_ROUTING_DRIFT')
    return {'C_issuances':len(issuances),'semantic_BV_hops':len(hops),
            'A_sign_receipts':len(receipts),'native_authentication':False}

def run_fork_source(m,arm):
    from research.spk_v5_t4def import t4def
    from spk_v5_research.island_c_owned_credit_v5t3h import build_case
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from research.spk_v5_t5abc.live_semantic_fork_v0 import execute_live_v0e,LiveBVPlanV0e
    case=t4def.fixed_terminal_case(m,arm,build_case)
    fabric=plan_v1a(case,'spread')
    return execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='C',terminal_channel=30,max_ticks=256))

def run(root):
    from research.spk_v5_t4def import t4def
    custody=custodial_fork_check(root)
    p=Path(root)
    zref=read_pinned(p/'research/spk_v5_t5abc/reference/t4zabc-topology.json',T4ZABC_SHA,'T4ZABC_REF')
    gref=read_pinned(p/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json',T4GHI_SHA,'T4GHI_REF')
    need(zref['BV_PE_C_computes']==312 and zref['BV_PE_computes']==1002 and
         zref['BV_scheduler_entries']==180,'T4ZABC_TOPOLOGY_DRIFT')
    need(len(zref['rows'])==len(gref['H_rows'])==180,'REFERENCE_CASE_COUNT_DRIFT')
    for file,expected in zref['source_pins'].items():
        need(file_hash(p/file)==expected,'SOURCE_PIN_DRIFT_'+file)
    rows=[]; counts=Counter()
    for idx,((meta,m,arm),zrow,grow) in enumerate(zip(t4def.table_cases(),zref['rows'],gref['H_rows'])):
        need(idx==grow['index']==zrow['index'] and
             all(meta[k]==grow[k] for k in ('arm','context','C_sensor','failure')),
             'REFERENCE_CASE_IDENTITY_DRIFT_'+str(idx))
        fork=run_fork_source(m,arm)
        before=strip_experimental(fork)
        refsha=grow['source_sha256']
        need(digest(before)==refsha==zrow['source_sha256'],'FROZEN_OUTPUT_BYTE_PARITY_DRIFT_'+str(idx))
        sign=grow['C_sign_candidate_from_same_source_forward_output']
        result=check_port(fork,sign,grow['BV_delivery_roles'])
        counts.update(result)
        rows.append({'index':idx,'source_sha256':refsha,'sign':sign,
            'C_issuance_count':result['C_issuances'],'A_receipt_count':result['A_sign_receipts'],
            'semantic_hops':result['semantic_BV_hops'],
            'guard_only_not_native_credit':meta['failure']=='none' and sign is not None,
            'experimental_port_sha256':digest(fork['experimental_semantic_port']),
            'native_credit':False})
    need(len(rows)==180 and counts['C_issuances']==72 and counts['A_sign_receipts']==72 and
         counts['semantic_BV_hops']==144 and sum(x['guard_only_not_native_credit'] for x in rows)==24,
         'EXPECTED_SOURCE_CLASSIFICATION_DRIFT')
    need(custodial_fork_check(root)==custody,'FORK_CUSTODY_DRIFT_DURING_RUN')
    return {'schema':SCHEMA,'status':STATUS,'T4ZABC_reference_sha256':T4ZABC_SHA,
        'T4GHI_reference_sha256':T4GHI_SHA,'pins':custody,
        'source_pins_verified':len(zref['source_pins']),
        'original_BV_calls_in_this_run':0,'fork_BV_calls':180,
        'byte_exact_frozen_output_parity':True,
        'in_scheduler_C_issuances':72,'A_received_sign_messages':72,
        'C_B_A_semantic_feedback_hops':144,
        'application_guard_research_candidates_not_native_credit':24,
        'rows_sha256':digest(rows),'rows':rows,
        'native_C_identity_authenticated':False,'native_receiver_semantic_credit_proven':False,
        'native_learning_proven':False,'host_can_forge_runtime':True,
        'promotion_allowed':False,
        'limits':['This is an additive COPIED scheduler fork; original BV-v0e and PE v1b remain frozen',
            'C sign originates from frozen PE _compute_local outputs within the fork execution batch',
            'Semantic metadata passes in fork BV packet to B then A; no independent C-owned cryptographic issuer',
            'Host may modify/provision fork runtime or bootstrap any state: not native C authentication',
            '72 receiver sign observations do not imply 72 application-allowed credits (guard cases 24)',
            'No independent signed C sensor, blind goals, native actor updates, or learning']}

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--root',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    v=a.parse_args()
    try:
        need(not v.out.exists(),'OUTPUT_ALREADY_EXISTS')
        d=run(v.root)
        v.out.parent.mkdir(parents=True,exist_ok=True)
        v.out.write_bytes(json.dumps(d,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
        print('T5ABC',STATUS,'fork',d['fork_BV_calls'],'A sign receipts',d['A_received_sign_messages'],
              'guard only',d['application_guard_research_candidates_not_native_credit'])
        print('sha256',file_hash(v.out))
    except (GateError,ValueError,KeyError,TypeError,ImportError,OSError,AssertionError) as e:
        raise SystemExit('T5ABC FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
