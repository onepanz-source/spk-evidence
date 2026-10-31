#!/usr/bin/env python3
"""BV v1a research: native v0z anchor plus optional explicitly SYNTHETIC toy demo.

No native judgment, objective truth verification, neuron update or learning.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from spk_bv_research.judgment_contract_v0y import JudgmentContractError
from spk_bv_research.symbolic_holdout_v1a import demonstrate

SCHEMA='spk-bv-prospective-symbolic-holdout-audit/v1a'
STATUS='NATIVE_CHAIN_ANCHORED_TOY_EVALUATION_ONLY'


def sha_bytes(b):return hashlib.sha256(b).hexdigest()


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path.cwd())
    for name in ('v0z','v0y','v0x','v0w'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--demo-synthetic',action='store_true',
                    help='run isolated synthetic AND/XOR/OR truth-table demonstration')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[args.v0z,args.v0y,args.v0x,args.v0w]
        unique=set();data=[];sources=[]
        for pa in paths:
            if (pa.is_symlink() or any(p.is_symlink() for p in pa.absolute().parents)
                    or not pa.is_file()):
                raise JudgmentContractError('missing, unsafe, or symlinked input')
            rp=pa.resolve(strict=True);st=rp.stat()
            if rp==root or root in rp.parents or (st.st_dev,st.st_ino) in unique:
                raise JudgmentContractError('unsafe input alias or repository file')
            unique.add((st.st_dev,st.st_ino));sources.append(rp);data.append(pa.read_bytes())
        o=args.out.absolute()
        if (o.exists() or o.is_symlink() or not o.parent.is_dir()
                or any(p.is_symlink() for p in o.parents) or o==root
                or root in o.resolve(strict=False).parents or o in sources):
            raise JudgmentContractError('unsafe or existing output')
        z,y,x,w=tuple(json.loads(b) for b in data)
        if any(type(a) is not dict for a in (z,y,x,w)):
            raise JudgmentContractError('non-object attestation')
        if (z.get('schema')!='spk-bv-shadow-update-admissibility-attestation/v0z'
            or z.get('status')!='PROSPECTIVE_FORMAL_ADMISSIBILITY_ONLY_NO_LEARNING'
            or y.get('schema')!='spk-bv-judgment-contract-attestation/v0y'
            or x.get('schema')!='spk-bv-workload-value-observability-boundary/v0x'
            or w.get('schema')!='spk-bv-native-temporal-workload-three-arm/v0w'):
            raise JudgmentContractError('incorrect v0z/v0y/v0x/v0w chain schemas')
        for i,name in ((1,'v0y'),(2,'v0x'),(3,'v0w')):
            if z.get(name+'_sha256')!=sha_bytes(data[i]):
                raise JudgmentContractError('v0z upstream digest mismatch: '+name)
        if (y.get('v0x_file_sha256')!=sha_bytes(data[2]) or
            y.get('v0w_file_sha256')!=sha_bytes(data[3]) or
            z.get('shadow_ledger_sha256')!=y.get('shadow_ledger_sha256')):
            raise JudgmentContractError('inherited v0y contract chain mismatch')
        a=z.get('admissibility')
        if (type(a) is not dict or type(a.get('plans')) is not list or
            type(a.get('hypotheses_admitted_shadow_only')) is not int or
            a['hypotheses_admitted_shadow_only']!=len(a['plans']) or
            a.get('applied_updates')!=0 or a.get('observed_native_judgments')!=0 or
            a.get('external_evaluations_completed')!=0 or
            a.get('informativeness_or_improvement_identified') is not False):
            raise JudgmentContractError('v0z is not an uncommitted valid shadow attestation')
        demo=demonstrate() if args.demo_synthetic else []
        report={
          'schema':SCHEMA,'status':STATUS,
          'v0z_file_sha256':sha_bytes(data[0]),
          'v0y_file_sha256':sha_bytes(data[1]),
          'v0x_file_sha256':sha_bytes(data[2]),
          'v0w_file_sha256':sha_bytes(data[3]),
          'native_shadow_hypotheses_admitted_as_attested_v0z':a['hypotheses_admitted_shadow_only'],
          'native_shadow_hypotheses_evaluated':0,
          'native_judgments_observed':0,'native_operator_updates_applied':0,
          'source_kind':'toy-isolated-symbolic-boolean-domain-not-SPK-runtime',
          'synthetic_demos_requested':args.demo_synthetic,
          'synthetic_demos':demo,
          'evaluation_domain':'exhaustive-two-bit-input-table-four-cases',
          'toy_input_and_budget_hashes_checked':args.demo_synthetic,
          'observed_native_learning_benefit':False,
          'external_oracle_truth_proven':False,
          'heldout_sampling_independence_proven':False,
          'claims_excluded':['toy-operators-not-native-SPK-operators',
             'toy-signals-and-labels-not-attested-native-judgments',
             'declared-synthetic-labels-not-external-independent-truth',
             'toy-comparison-is-not-native-learning',
             'no-committed-update-no-rollback-or-generalization',
             'no-hardware-cost-and-no-architecture-promotion'],
        }
        if any(pa.read_bytes()!=raw for pa,raw in zip(paths,data)):
            raise JudgmentContractError('input changed during attestation')
        with o.open('x',encoding='utf8') as fh:
            json.dump(report,fh,sort_keys=True,indent=2,ensure_ascii=True);fh.write('\n')
        print(json.dumps({'status':STATUS,'native_learning_proven':False,
            'synthetic_demo_cases':len(demo),'out':str(o)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError) as err:
        print('SPK BV v1a REJECTED: '+str(err),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
