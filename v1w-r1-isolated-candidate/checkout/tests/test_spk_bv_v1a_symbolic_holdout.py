"""BV v1a: adversarial toy-only paired holdout and native-chain custody."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

import pytest

from spk_bv_research.judgment_contract_v0y import JudgmentContractError
from spk_bv_research.symbolic_holdout_v1a import (
    demonstrate,demo_case,evaluate,digest,apply,SCHEMA,STATUS,
)
from search import spk_bv_v1a_symbolic_holdout as cli


def case():
    truth={(a,b):a^b for a in (0,1) for b in (0,1)}
    return demo_case('positive','toy.and','toy.xor',truth)


def test_three_synthetic_classifications():
    results=demonstrate()
    assert [a['correct_count_delta'] for a in results]==[3,-3,0]
    assert [a['number_of_paired_cases'] for a in results]==[4,4,4]
    assert all(a['native_judgments_observed']==a['applied_updates']==0 for a in results)
    assert all(not a['causal_learning_proven'] and not a['external_truth_or_heldout_independence_proven'] for a in results)
    assert all(a['baseline_correct']+a['correct_count_delta']==a['candidate_correct'] for a in results)


def test_no_mutation():
    led,plan,trial=case();before=copy.deepcopy((led,plan,trial))
    x=evaluate(trial,led,plan)
    assert (led,plan,trial)==before
    assert x['baseline_correct']==1 and x['candidate_correct']==4
    assert x['paired_inputs_and_budget_verified_for_toy']


def test_operator_truth_table():
    assert [apply('toy.and',a,b) for a in (0,1) for b in (0,1)]==[0,0,0,1]
    assert [apply('toy.or',a,b) for a in (0,1) for b in (0,1)]==[0,1,1,1]
    assert [apply('toy.xor',a,b) for a in (0,1) for b in (0,1)]==[0,1,1,0]
    assert [apply('toy.nand',a,b) for a in (0,1) for b in (0,1)]==[1,1,1,0]


@pytest.mark.parametrize('modifier,reason',[
 (lambda d,p,t:t.update(native_credit=1),'envelope'),
 (lambda d,p,t:t.update(status='NATIVE_LEARNING'),'envelope'),
 (lambda d,p,t:t.update(schema='other'),'envelope'),
 (lambda d,p,t:t.update(operator_library='spk.core'),'operator library'),
 (lambda d,p,t:t.update(label_origin='verified-oracle'),'truth source'),
 (lambda d,p,t:t.update(objective_id='toy.other'),'evaluator'),
 (lambda d,p,t:t.update(evaluator_id='toy.other'),'evaluator'),
 (lambda d,p,t:t.update(hypothesis_id='missing'),'unknown hypothesis'),
 (lambda d,p,t:t.update(future_episode_id='past'),'future episode'),
 (lambda d,p,t:t.update(inputs=t['inputs'][:3]),'four input'),
 (lambda d,p,t:t.update(labels=[0,1,1]),'label count'),
 (lambda d,p,t:t['inputs'][0].update(ghost=1),'input record'),
 (lambda d,p,t:t['inputs'][2].update(case_id='x1'),'duplicate input case'),
 (lambda d,p,t:t['inputs'][2].update(a=0,b=1),'duplicate input pair'),
 (lambda d,p,t:t['inputs'][0].update(tick=8),'non-monotonic'),
 (lambda d,p,t:t['inputs'][0].update(tick=6),'outside prospective'),
 (lambda d,p,t:t['inputs'][0].update(a=True),'binary integer'),
 (lambda d,p,t:t['inputs'][1].update(b=2),'binary integer'),
 (lambda d,p,t:t['labels'].__setitem__(0,2),'binary integer'),
 (lambda d,p,t:t['labels'].__setitem__(0,1),'label commitment'),
 (lambda d,p,t:t.update(labels_sha256='1'*64),'label commitment'),
 (lambda d,p,t:t.update(labels_sha256='broken'),'invalid SHA'),
 (lambda d,p,t:t['budget'].update(max_evaluations=5),'exactly four'),
 (lambda d,p,t:t['budget'].update(max_evaluations=True),'exactly four'),
 (lambda d,p,t:t['budget'].update(max_local_changes=2),'one hypothetical'),
 (lambda d,p,t:t['budget'].update(override=True),'budget fields'),
 (lambda d,p,t:p['hypotheses'][0].update(control_input_sha256='e'*64,candidate_input_sha256='e'*64),'input digest'),
 (lambda d,p,t:p['hypotheses'][0].update(control_budget_sha256='e'*64,candidate_budget_sha256='e'*64),'budget digest'),
 (lambda d,p,t:p['hypotheses'][0].update(baseline_operator='toy.nand'),'baseline not'),
 (lambda d,p,t:p['hypotheses'][0].update(candidate_operator='toy.nand'),'candidate not'),
 (lambda d,p,t:p['hypotheses'][0].update(evaluation_objective_id='other'),'criterion not'),
 (lambda d,p,t:p['hypotheses'][0].update(holdout_end_tick=7),'outside prospective'),
 (lambda d,p,t:d['criteria'][0].update(registered_tick=1),'criterion was not'),
 (lambda d,p,t:d['judgments'][0].update(available_tick=9),'feedback unavailable'),
 (lambda d,p,t:d['proposals'][0].update(verdict='commit'),'forbids commit'),
])
def test_reject_corruption(modifier,reason):
    d,p,t=case();modifier(d,p,t)
    with pytest.raises(JudgmentContractError,match=reason):evaluate(t,d,p)


def test_unknown_library_operators():
    with pytest.raises(JudgmentContractError,match='unknown operator'):
        apply('native.X',0,0)
    with pytest.raises(JudgmentContractError,match='binary integer'):
        apply('toy.xor',False,0)


def build_fake_chain(root):
    base=root.parent
    y={'schema':'spk-bv-judgment-contract-attestation/v0y',
       'shadow_ledger_sha256':'a'*64,'v0x_file_sha256':None,'v0w_file_sha256':None}
    x={'schema':'spk-bv-workload-value-observability-boundary/v0x'}
    w={'schema':'spk-bv-native-temporal-workload-three-arm/v0w'}
    xb=json.dumps(x).encode();wb=json.dumps(w).encode()
    y.update(v0x_file_sha256=cli.sha_bytes(xb),v0w_file_sha256=cli.sha_bytes(wb))
    yb=json.dumps(y).encode()
    z={'schema':'spk-bv-shadow-update-admissibility-attestation/v0z',
       'status':'PROSPECTIVE_FORMAL_ADMISSIBILITY_ONLY_NO_LEARNING',
       'v0y_sha256':cli.sha_bytes(yb),'v0x_sha256':cli.sha_bytes(xb),
       'v0w_sha256':cli.sha_bytes(wb),'shadow_ledger_sha256':'a'*64,
       'admissibility':{'plans':[],'hypotheses_admitted_shadow_only':0,
        'applied_updates':0,'observed_native_judgments':0,
        'external_evaluations_completed':0,
        'informativeness_or_improvement_identified':False}}
    paths=[]
    for name,blob in [('z',json.dumps(z).encode()),('y',yb),('x',xb),('w',wb)]:
        pp=base/(name+'.json');pp.write_bytes(blob);paths.append(pp)
    return paths


def cli_args(tmp_path,*,demo=False):
    root=tmp_path/'repo';root.mkdir(exist_ok=True)
    paths=build_fake_chain(root);out=tmp_path/'result.json'
    args=['--root',str(root)]
    for name,path in zip(('v0z','v0y','v0x','v0w'),paths): args+=['--'+name,str(path)]
    if demo:args+=['--demo-synthetic']
    args+=['--out',str(out)]
    return args,paths,out,root


def test_cli_anchored_empty(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    assert cli.main(args)==0
    report=json.loads(out.read_text())
    assert report['synthetic_demos']==[] and report['native_shadow_hypotheses_evaluated']==0
    assert not report['observed_native_learning_benefit']
    assert cli.main(args)==2


def test_cli_explicit_synthetic(tmp_path):
    args,_,out,_=cli_args(tmp_path,demo=True)
    assert cli.main(args)==0
    o=json.loads(out.read_text())
    assert [a['correct_count_delta'] for a in o['synthetic_demos']]==[3,-3,0]
    assert o['native_operator_updates_applied']==o['native_judgments_observed']==0
    assert o['external_oracle_truth_proven'] is False


@pytest.mark.parametrize('target',('v0y','v0x','v0w'))
def test_cli_rejects_wrong_chain_hash(tmp_path,target):
    args,files,out,_=cli_args(tmp_path)
    idx=('v0z','v0y','v0x','v0w').index(target)
    files[idx].write_text(files[idx].read_text()+'\n')
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_wrong_schema(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    z=json.loads(files[0].read_text());z['schema']='other';files[0].write_text(json.dumps(z))
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_false_learning_claim(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    z=json.loads(files[0].read_text());z['admissibility']['applied_updates']=1
    files[0].write_text(json.dumps(z))
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_hardlink_alias(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    new=tmp_path/'hard.json';new.hardlink_to(files[2]);args[args.index('--v0w')+1]=str(new)
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_symlink_input(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    new=tmp_path/'alias.json';new.symlink_to(files[2]);args[args.index('--v0w')+1]=str(new)
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_symlink_parent(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    folder=tmp_path/'directory';folder.mkdir();original=folder/'w.json';original.write_bytes(files[3].read_bytes())
    link=tmp_path/'linked';link.symlink_to(folder,target_is_directory=True)
    args[args.index('--v0w')+1]=str(link/'w.json')
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_output_inside_repo(tmp_path):
    args,files,out,root=cli_args(tmp_path)
    args[-1]=str(root/'result.json')
    assert cli.main(args)==2 and not (root/'result.json').exists()


def test_cli_rejects_alias_file_inputs(tmp_path):
    args,files,out,_=cli_args(tmp_path)
    args[args.index('--v0w')+1]=str(files[2]);assert cli.main(args)==2


def test_digest_order_deterministic():
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})
    assert digest([1,2])!=digest([2,1])
