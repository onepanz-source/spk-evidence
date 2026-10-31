"""BV v0z adversarial, PURE shadow-only research tests; no native judgments."""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
import pytest
from spk_bv_research.judgment_contract_v0y import ledger_template, JudgmentContractError
from spk_bv_research.shadow_update_v0z import template, validate_hypotheses, OUTPUT_STATUS
from search import spk_bv_v0z_shadow_update as cli

H='a'*64
B='b'*64

def ledger():
    x=ledger_template()
    x['criteria']=[dict(criterion_id='crit1',objective_id='objective1',evaluator_id='oracle1',registered_tick=0,direction='maximize')]
    x['decisions']=[dict(decision_id='decision1',neuron_id='A',episode_id='episode1',decision_tick=1,
                         predecision_state_sha256=H,context_sha256=H,
                         admissible_operators=['op1','op2'],chosen_operator='op1')]
    x['judgments']=[dict(judgment_id='judgment1',decision_id='decision1',observer_id='B',receiver_id='A',
                         criterion_id='crit1',sign=-1,source_evidence=['r1'],
                         causal_origin_id='origin1',produced_tick=2,available_tick=3)]
    x['proposals']=[dict(proposal_id='proposal1',target_decision_id='decision1',judgment_ids=['judgment1'],
                         proposed_operator='op2',created_tick=4,eligibility_window=[3,6],verdict='noop')]
    return x

def hypothesis():
    return dict(hypothesis_id='h1',proposal_id='proposal1',criterion_id='crit1',
                planning_tick=4,future_episode_id='episode2',holdout_start_tick=7,
                holdout_end_tick=8,baseline_operator='op1',candidate_operator='op2',
                max_local_changes=1,control_input_sha256=H,candidate_input_sha256=H,
                control_budget_sha256=B,candidate_budget_sha256=B,
                evaluation_objective_id='objective1',evaluation_evaluator_id='oracle1',
                evaluation_mode='declared-paired-external-holdout')

def plan():
    t=template();t['hypotheses']=[hypothesis()];return t

def reject(change, msg, *, on_ledger=False):
    x,p=ledger(),plan()
    change(x if on_ledger else p)
    with pytest.raises(JudgmentContractError,match=msg):validate_hypotheses(p,x)

def test_v0y_empty_ledger_no_synthetic_hypotheses():
    out=validate_hypotheses(template(),ledger_template())
    assert out['hypotheses_admitted_shadow_only']==0
    assert out['applied_updates']==0 and out['observed_native_judgments']==0
    assert out['informativeness_or_improvement_identified'] is False

def test_valid_synthetic_hypothesis_still_no_update():
    x=ledger();p=plan()
    before=copy.deepcopy((x,p))
    o=validate_hypotheses(p,x)
    assert (x,p)==before and o['hypotheses_admitted_shadow_only']==1
    assert o['plans'][0]['candidate_changes_from_baseline']==1
    assert o['plans'][0]['paired_input_or_budget_proven_by_runtime'] is False
    assert o['applied_updates']==o['observed_native_judgments']==o['external_evaluations_completed']==0

@pytest.mark.parametrize('name,change,match',[ 
 ('extra envelope',lambda x:x.update(native_learned=True),'envelope fields'),
 ('wrong schema',lambda x:x.update(schema='v0b'),'envelope'),
 ('wrong status',lambda x:x.update(status='COMMITTED'),'envelope'),
 ('not list',lambda x:x.update(hypotheses={}), 'hypotheses must'),
 ('unexpected result',lambda x:x['hypotheses'][0].update(holdout_score=100),'hypothesis fields'),
 ('missing hypothesis field',lambda x:x['hypotheses'][0].pop('candidate_operator'), 'hypothesis fields'),
 ('duplicate id',lambda x:x['hypotheses'].append(dict(x['hypotheses'][0])), 'duplicate hypothesis'),
 ('unknown proposal',lambda x:x['hypotheses'][0].update(proposal_id='fake'),'unknown proposal'),
 ('unknown criterion',lambda x:x['hypotheses'][0].update(criterion_id='other'),'unknown criterion'),
 ('baseline wrong',lambda x:x['hypotheses'][0].update(baseline_operator='op2'),'baseline not'),
 ('candidate wrong',lambda x:x['hypotheses'][0].update(candidate_operator='op3'),'candidate not'),
 ('same candidate',lambda x:x['hypotheses'][0].update(candidate_operator='op1'),'candidate not'),
 ('bound too broad',lambda x:x['hypotheses'][0].update(max_local_changes=2),'shadow bound'),
 ('bound bool',lambda x:x['hypotheses'][0].update(max_local_changes=True),'shadow bound'),
 ('planned too early',lambda x:x['hypotheses'][0].update(planning_tick=3),'planning outside'),
 ('planned too late',lambda x:x['hypotheses'][0].update(planning_tick=7),'planning outside'),
 ('planned tick bool',lambda x:x['hypotheses'][0].update(planning_tick=True),'tick'),
 ('holdout same episode',lambda x:x['hypotheses'][0].update(future_episode_id='episode1'),'future episode'),
 ('holdout not future',lambda x:x['hypotheses'][0].update(holdout_start_tick=4),'future-only'),
 ('holdout end too early',lambda x:x['hypotheses'][0].update(holdout_end_tick=6),'future-only'),
 ('holdout invalid tick',lambda x:x['hypotheses'][0].update(holdout_end_tick=-1),'nonnegative'),
 ('control candidate inputs mismatch',lambda x:x['hypotheses'][0].update(candidate_input_sha256=B),'paired inputs differ'),
 ('control candidate budgets mismatch',lambda x:x['hypotheses'][0].update(candidate_budget_sha256=H),'paired budgets differ'),
 ('bad declared input hash',lambda x:x['hypotheses'][0].update(control_input_sha256='fake'),'invalid SHA'),
 ('objective changed',lambda x:x['hypotheses'][0].update(evaluation_objective_id='other'),'criterion not identical'),
 ('evaluator changed',lambda x:x['hypotheses'][0].update(evaluation_evaluator_id='other'),'criterion not identical'),
 ('different eval mode',lambda x:x['hypotheses'][0].update(evaluation_mode='native-learned'),'external held-out'),
 ('extra second proposal for same decision',lambda x:x['hypotheses'].append(dict(x['hypotheses'][0],hypothesis_id='h2')), 'multiple hypotheses'),
])
def test_reject(name,change,match):reject(change,match)

def test_reject_mixed_criteria():
    x=ledger();p=plan()
    x['criteria'].append(dict(x['criteria'][0],criterion_id='crit2'))
    x['judgments'].append(dict(x['judgments'][0],judgment_id='judgment2',criterion_id='crit2',causal_origin_id='origin2'))
    x['proposals'][0]['judgment_ids'].append('judgment2')
    with pytest.raises(JudgmentContractError,match='mixed or unrelated criteria'):
        validate_hypotheses(p,x)

def test_more_observers_one_origin_not_independent_votes():
    x=ledger();p=plan()
    x['judgments'].append(dict(x['judgments'][0],judgment_id='j2',observer_id='C',source_evidence=['r2']))
    x['proposals'][0]['judgment_ids'].append('j2')
    o=validate_hypotheses(p,x)
    assert o['plans'][0]['judgments_referenced']==2
    assert o['plans'][0]['declared_origin_groups']==1
    assert o['independent_causal_votes_proven']==0

def test_multiple_plans_same_future_neuron_episode_rejected():
    x=ledger();p=plan()
    x['decisions'].append(dict(x['decisions'][0],decision_id='decision2'))
    x['judgments'].append(dict(x['judgments'][0],judgment_id='judgment2',decision_id='decision2',causal_origin_id='origin2'))
    x['proposals'].append(dict(x['proposals'][0],proposal_id='proposal2',target_decision_id='decision2',judgment_ids=['judgment2']))
    p['hypotheses'].append(dict(p['hypotheses'][0],hypothesis_id='h2',proposal_id='proposal2'))
    with pytest.raises(JudgmentContractError,match='same neuron/episode'):
        validate_hypotheses(p,x)

def test_new_future_episode_admitted_but_no_learning():
    x=ledger();p=plan()
    x['decisions'].append(dict(x['decisions'][0],decision_id='decision2'))
    x['judgments'].append(dict(x['judgments'][0],judgment_id='judgment2',decision_id='decision2',causal_origin_id='origin2'))
    x['proposals'].append(dict(x['proposals'][0],proposal_id='proposal2',target_decision_id='decision2',judgment_ids=['judgment2']))
    p['hypotheses'].append(dict(p['hypotheses'][0],hypothesis_id='h2',proposal_id='proposal2',future_episode_id='episode3'))
    assert validate_hypotheses(p,x)['hypotheses_admitted_shadow_only']==2

def fake_anchor():
    return {'native_cells':15,'native_arms_reexecuted':45,
            'feedback_first_positive_delay_cells':6,'forward_conserved_cells':15,
            'source_hashes':{},'fixture_sha256':H,'cross_process_equality_verified':False}

def setup_cli(tmp_path,monkeypatch, ledger_file=False, plan_file=False):
    root=tmp_path/'repo';root.mkdir()
    y=tmp_path/'y.json'; xx=tmp_path/'x.json';w=tmp_path/'w.json';out=tmp_path/'result.json'
    xx.write_text('{}');w.write_text('{}')
    monkeypatch.setattr(cli,'verify_cost_anchor',lambda *_:fake_anchor())
    l=ledger() if ledger_file else ledger_template()
    ld=tmp_path/'ledger.json'
    if ledger_file:ld.write_text(json.dumps(l))
    pl=tmp_path/'hypotheses.json'
    if plan_file:pl.write_text(json.dumps(plan()))
    expected_y={'schema':cli.Y_SCHEMA,'status':cli.Y_STATUS,
                'v0x_file_sha256':cli.sha_bytes(xx.read_bytes()),
                'v0w_file_sha256':cli.sha_bytes(w.read_bytes()),
                'cost_anchor':fake_anchor(),'contract_counts':cli.validate_ledger(l),
                'shadow_ledger_supplied':ledger_file,'shadow_ledger_sha256':cli.canonical_hash(l),
                'proof_obligations_not_discharged':cli.OBLIGATIONS}
    y.write_text(json.dumps(expected_y))
    args=['--root',str(root),'--v0y',str(y),'--v0x',str(xx),'--v0w',str(w)]
    if ledger_file:args+=['--ledger',str(ld)]
    if plan_file:args+=['--hypotheses',str(pl)]
    args+=['--out',str(out)]
    return args,y,xx,w,out

def test_cli_no_ledger_no_plan_does_not_invent(tmp_path,monkeypatch):
    args,_,_,_,out=setup_cli(tmp_path,monkeypatch)
    assert cli.main(args)==0
    r=json.loads(out.read_text())
    assert r['status']==OUTPUT_STATUS
    assert r['admissibility']['hypotheses_admitted_shadow_only']==0
    assert r['admissibility']['applied_updates']==0
    assert cli.main(args)==2

def test_cli_shadow_only_ledger_plan(tmp_path,monkeypatch):
    args,*_=setup_cli(tmp_path,monkeypatch,True,True)
    assert cli.main(args)==0
    o=json.loads(Path(args[-1]).read_text())
    assert o['admissibility']['hypotheses_admitted_shadow_only']==1
    assert o['admissibility']['external_evaluations_completed']==0

def test_cli_rejects_wrong_v0y_input_binding(tmp_path,monkeypatch):
    args,y,_,_,out=setup_cli(tmp_path,monkeypatch)
    source=json.loads(y.read_text());source['v0x_file_sha256']=B
    y.write_text(json.dumps(source))
    assert cli.main(args)==2 and not out.exists()

def test_cli_rejects_v0y_without_ledger_when_ledger_supplied(tmp_path,monkeypatch):
    args,y,_,_,out=setup_cli(tmp_path,monkeypatch)
    led=tmp_path/'ledger.json';led.write_text(json.dumps(ledger()))
    args=args[:-2]+['--ledger',str(led)]+args[-2:]
    assert cli.main(args)==2 and not out.exists()

def test_cli_rejects_alias_symlink_and_repo_output(tmp_path,monkeypatch):
    args,y,x,w,out=setup_cli(tmp_path,monkeypatch)
    idx=args.index('--v0w')+1
    broken=copy.deepcopy(args);broken[idx]=str(x)
    assert cli.main(broken)==2
    symlink=tmp_path/'alias.json';symlink.symlink_to(w)
    broken=copy.deepcopy(args);broken[idx]=str(symlink)
    assert cli.main(broken)==2
    broken=copy.deepcopy(args);broken[-1]=str(tmp_path/'repo'/'invalid.json')
    assert cli.main(broken)==2
    assert not out.exists()

def test_cli_rejects_unauthorized_native_learning_field(tmp_path,monkeypatch):
    args,*_=setup_cli(tmp_path,monkeypatch,True,True)
    p=tmp_path/'hypotheses.json';raw=json.loads(p.read_text());raw['hypotheses'][0]['gain']=1
    p.write_text(json.dumps(raw))
    assert cli.main(args)==2

def test_real_anchor_if_explicit_files_present_is_only_formal():
    # No ambient native captures required for portable fwork pytest gate.
    assert template()['hypotheses']==[]


def test_cli_rejects_hardlink_alias(tmp_path,monkeypatch):
    args,y,x,w,out=setup_cli(tmp_path,monkeypatch)
    hard=tmp_path/'hardlink.json';hard.hardlink_to(x)
    broken=copy.deepcopy(args);broken[broken.index('--v0w')+1]=str(hard)
    assert cli.main(broken)==2 and not out.exists()

def test_cli_rejects_symlink_parent_input(tmp_path,monkeypatch):
    args,y,x,w,out=setup_cli(tmp_path,monkeypatch)
    original=tmp_path/'directory';original.mkdir()
    source=original/'source.json';source.write_bytes(w.read_bytes())
    alias=tmp_path/'parentalias';alias.symlink_to(original,target_is_directory=True)
    broken=copy.deepcopy(args);broken[broken.index('--v0w')+1]=str(alias/'source.json')
    assert cli.main(broken)==2 and not out.exists()
