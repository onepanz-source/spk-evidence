#!/usr/bin/env python3
"""Attest shadow-only BV judgment contract against source-recomputed v0x/v0w."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from spk_bv_research.judgment_contract_v0y import (
    JudgmentContractError, ledger_template, validate_ledger,
    verify_cost_anchor, OUTPUT_SCHEMA, OUTPUT_STATUS,
)
from spk_bv_research.value_boundary_v0x import summarize


def load_object(p):
    with p.open('r', encoding='utf-8') as f:
        r=json.load(f)
    if type(r) is not dict:
        raise JudgmentContractError('input must be a JSON object')
    return r


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v0x',type=Path,required=True)
    parser.add_argument('--v0w',type=Path,required=True)
    parser.add_argument('--ledger',type=Path,help='Optional explicit SHADOW-only records; no native judgment inference')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        require_files=[args.v0x,args.v0w]+([args.ledger] if args.ledger else [])
        inputs=[]
        for p in require_files:
            if p.is_symlink() or not p.is_file():
                raise JudgmentContractError('missing or symlinked input: '+str(p))
            real=p.resolve(strict=True)
            if root in real.parents:
                raise JudgmentContractError('input within repository prohibited: '+str(p))
            if real in inputs:
                raise JudgmentContractError('aliased input files')
            inputs.append(real)
        out=args.out.absolute()
        if (out.exists() or out.is_symlink() or out == root or root in out.parents
                or out in inputs or any(part.is_symlink() for part in out.parents)
                or not out.parent.is_dir() or root in out.resolve(strict=False).parents):
            raise JudgmentContractError('unsafe or existing output path')
        xb,wb=args.v0x.read_bytes(),args.v0w.read_bytes()
        x,w=json.loads(xb),json.loads(wb)
        anchor=verify_cost_anchor(x,w,summarize)
        ledger=load_object(args.ledger) if args.ledger else ledger_template()
        counts=validate_ledger(ledger)
        result={
            'schema':OUTPUT_SCHEMA,'status':OUTPUT_STATUS,
            'v0x_file_sha256':hashlib.sha256(xb).hexdigest(),
            'v0w_file_sha256':hashlib.sha256(wb).hexdigest(),
            'cost_anchor':anchor,'contract_counts':counts,
            'shadow_ledger_supplied':args.ledger is not None,
            'shadow_ledger_sha256':hashlib.sha256(
                json.dumps(ledger,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
            ).hexdigest(),
            'proof_obligations_not_discharged':[
                'criterion_truth_and_external_oracle',
                'evidence_lineage_causality_and_cross-observer_independence',
                'decision_binding_to_real_neuron_runtime',
                'future_held-out_counterfactual_improvement',
                'bounded_update_commit_and_rollback',
                'global_credit_learning_and_hardware_performance',
            ],
        }
        # Fail closed if either input changed during validation.
        if args.v0x.read_bytes()!=xb or args.v0w.read_bytes()!=wb:
            raise JudgmentContractError('cost anchor inputs changed during audit')
        if args.ledger and load_object(args.ledger)!=ledger:
            raise JudgmentContractError('ledger changed during audit')
        with out.open('x',encoding='utf-8') as f:
            json.dump(result,f,sort_keys=True,indent=2,ensure_ascii=True)
            f.write('\n')
        print(json.dumps({'status':OUTPUT_STATUS,'native_recomputed_cells':anchor['native_cells'],
                          'shadow_judgments':counts['judgments_declared_shadow_only'],
                          'updates_applied':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print('SPK BV v0y REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
