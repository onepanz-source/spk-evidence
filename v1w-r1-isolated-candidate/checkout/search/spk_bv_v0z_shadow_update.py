#!/usr/bin/env python3
"""BV v0z: attest prospective shadow-only update hypotheses against BV v0y/v0x/v0w."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from spk_bv_research.judgment_contract_v0y import (
    JudgmentContractError, OUTPUT_SCHEMA as Y_SCHEMA, OUTPUT_STATUS as Y_STATUS,
    ledger_template, validate_ledger, verify_cost_anchor,
)
from spk_bv_research.value_boundary_v0x import summarize
from spk_bv_research.shadow_update_v0z import (
    SCHEMA, OUTPUT_SCHEMA, OUTPUT_STATUS, template, validate_hypotheses,
)

OBLIGATIONS=[
    'criterion_truth_and_external_oracle',
    'evidence_lineage_causality_and_cross-observer_independence',
    'decision_binding_to_real_neuron_runtime',
    'future_held-out_counterfactual_improvement',
    'bounded_update_commit_and_rollback',
    'global_credit_learning_and_hardware_performance',
]

def sha_bytes(b):return hashlib.sha256(b).hexdigest()

def canonical_hash(x):
    return sha_bytes(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())

def read_obj(b):
    o=json.loads(b)
    if type(o) is not dict:raise JudgmentContractError('JSON input is not object')
    return o

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for name in ('v0y','v0x','v0w'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ledger',type=Path)
    p.add_argument('--hypotheses',type=Path)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[args.v0y,args.v0x,args.v0w]+([args.ledger] if args.ledger else [])+([args.hypotheses] if args.hypotheses else [])
        inputs=[];input_inodes=set();bytes_in=[]
        for a in paths:
            if a.is_symlink() or any(parent.is_symlink() for parent in a.absolute().parents) or not a.is_file():
                raise JudgmentContractError('missing or symlinked input: '+str(a))
            real=a.resolve(strict=True)
            if real==root or root in real.parents or real in inputs:
                raise JudgmentContractError('unsafe/aliased input')
            st=real.stat()
            if (st.st_dev,st.st_ino) in input_inodes:
                raise JudgmentContractError('hardlinked/aliased input')
            input_inodes.add((st.st_dev,st.st_ino))
            inputs.append(real)
            bytes_in.append(a.read_bytes())
        out=args.out.absolute()
        if (out.exists() or out.is_symlink() or out==root or root in out.parents
                or out in inputs or not out.parent.is_dir()
                or any(a.is_symlink() for a in out.parents)
                or root in out.resolve(strict=False).parents):
            raise JudgmentContractError('unsafe or existing output path')
        y,x,w=map(read_obj,bytes_in[:3])
        anchor=verify_cost_anchor(x,w,summarize)
        ledger=read_obj(bytes_in[3]) if args.ledger else ledger_template()
        plans=read_obj(bytes_in[3+bool(args.ledger)]) if args.hypotheses else template()
        counts=validate_ledger(ledger)
        expected_y={
            'schema':Y_SCHEMA,'status':Y_STATUS,
            'v0x_file_sha256':sha_bytes(bytes_in[1]),
            'v0w_file_sha256':sha_bytes(bytes_in[2]),
            'cost_anchor':anchor,'contract_counts':counts,
            'shadow_ledger_supplied':args.ledger is not None,
            'shadow_ledger_sha256':canonical_hash(ledger),
            'proof_obligations_not_discharged':OBLIGATIONS,
        }
        if y!=expected_y:raise JudgmentContractError('v0y attestation/ledger/anchor mismatch')
        validated=validate_hypotheses(plans,ledger)
        report={
            'schema':OUTPUT_SCHEMA,'status':OUTPUT_STATUS,
            'v0y_sha256':sha_bytes(bytes_in[0]),'v0x_sha256':sha_bytes(bytes_in[1]),
            'v0w_sha256':sha_bytes(bytes_in[2]),
            'shadow_ledger_sha256':canonical_hash(ledger),
            'prospective_plan_sha256':canonical_hash(plans),
            'shadow_ledger_supplied':args.ledger is not None,
            'prospective_plans_supplied':args.hypotheses is not None,
            'native_cost_recomputation_as_attested_v0x':anchor['native_arms_reexecuted'],
            'cross_process_equality_verified':anchor['cross_process_equality_verified'],
            'admissibility':validated,
            'claims_excluded':[
                'no_native_judgments_observed_or_inferred',
                'no_operator_committed_to_native_neurons',
                'paired_inputs_and_budgets_only_declared_not_source_attested',
                'hypothetical_single_operator_change_not_bounded_state_runtime_update',
                'no_heldout_scores_or_observed_improvement',
                'no_objective_truth_or_independent_causes_certified',
                'no_learning_global_credit_or_architecture_promotion',
            ],
        }
        # Attest same bytes as those which were checked.
        if any(pa.read_bytes()!=raw for pa,raw in zip(paths,bytes_in)):
            raise JudgmentContractError('input changed during attestation')
        with out.open('x',encoding='utf8') as fh:
            json.dump(report,fh,sort_keys=True,indent=2,ensure_ascii=True)
            fh.write('\n')
        print(json.dumps({'status':OUTPUT_STATUS,'shadow_hypotheses':validated['hypotheses_admitted_shadow_only'],
                          'native_updates_applied':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
        print('SPK BV v0z REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
