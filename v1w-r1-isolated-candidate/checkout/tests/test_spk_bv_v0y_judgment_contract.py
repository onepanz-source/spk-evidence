"""Fail-closed research tests. Synthetic records never count as native judgments."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from spk_bv_research.judgment_contract_v0y import (
    JudgmentContractError, ledger_template, validate_ledger, verify_cost_anchor,
    OUTPUT_STATUS,
)
from search import spk_bv_v0y_judgment_contract as cli

H='a'*64

def example():
    x=ledger_template()
    x['criteria']=[dict(criterion_id='c1',objective_id='objective1',evaluator_id='external',registered_tick=0,direction='maximize')]
    x['decisions']=[dict(decision_id='d1',neuron_id='A',episode_id='e1',decision_tick=1,
                         predecision_state_sha256=H,context_sha256=H,
                         admissible_operators=['op1','op2'],chosen_operator='op1')]
    x['judgments']=[dict(judgment_id='j1',decision_id='d1',observer_id='B',receiver_id='A',
                          criterion_id='c1',sign=-1,source_evidence=['r1'],
                          causal_origin_id='original1',produced_tick=2,available_tick=3)]
    x['proposals']=[dict(proposal_id='u1',target_decision_id='d1',judgment_ids=['j1'],
                          proposed_operator='op2',created_tick=4,eligibility_window=[3,6],verdict='noop')]
    return x

def reject(change, msg):
    d=example()
    change(d)
    with pytest.raises(JudgmentContractError,match=msg):validate_ledger(d)

def test_empty_native_ledger_contains_no_inferred_judgments():
    r=validate_ledger(ledger_template())
    assert r['judgments_declared_shadow_only']==0 and r['applied_updates']==0
    assert r['information_benefit_identified'] is False

def test_shadow_judgment_is_not_learning():
    r=validate_ledger(example())
    assert r['criteria_declared']==1 and r['decisions_declared']==1
    assert r['judgments_declared_shadow_only']==1 and r['proposals_noop_only']==1
    assert r['applied_updates']==0 and r['native_judgments_observed']==0

@pytest.mark.parametrize('name,edit,message',[
 ('unknown top field',lambda x:x.update(learning_gain=3),'unexpected'),
 ('false status',lambda x:x.update(status='NATIVE_JUDGMENTS_PROVEN'),'shadow ledger'),
 ('unknown criterion',lambda x:x['judgments'][0].update(criterion_id='fake'),'unknown criterion'),
 ('late criterion',lambda x:x['criteria'][0].update(registered_tick=2),'not predeclared'),
 ('same tick criterion',lambda x:x['criteria'][0].update(registered_tick=1),'not predeclared'),
 ('bad criterion direction',lambda x:x['criteria'][0].update(direction='higher'),'unknown direction'),
 ('duplicate criterion',lambda x:x['criteria'].append(dict(x['criteria'][0])),'duplicate criterion'),
 ('chosen unadmitted',lambda x:x['decisions'][0].update(chosen_operator='op3'),'not admitted'),
 ('candidate duplicated',lambda x:x['decisions'][0].update(admissible_operators=['op1','op1']),'duplicate'),
 ('missing decision',lambda x:x['judgments'][0].update(decision_id='d2'),'unknown decision'),
 ('duplicate decision',lambda x:x['decisions'].append(dict(x['decisions'][0])),'duplicate decision'),
 ('unknown receiver',lambda x:x['judgments'][0].update(receiver_id='Z'),'receiver'),
 ('self judgement',lambda x:x['judgments'][0].update(observer_id='A'),'self-judgment'),
 ('missing evidence',lambda x:x['judgments'][0].update(source_evidence=[]),'invalid list'),
 ('duplicate evidence',lambda x:x['judgments'][0].update(source_evidence=['r1','r1']),'duplicate'),
 ('no evidence lineage',lambda x:x['judgments'][0].update(causal_origin_id=''),'invalid identifier'),
 ('judgement from future tick',lambda x:x['judgments'][0].update(produced_tick=1),'noncausal'),
 ('available before produced',lambda x:x['judgments'][0].update(available_tick=1),'noncausal'),
 ('sign float',lambda x:x['judgments'][0].update(sign=0.5),'sign must'),
 ('sign bool',lambda x:x['judgments'][0].update(sign=True),'sign must'),
 ('missing shadow verdict',lambda x:x['proposals'][0].update(verdict='commit'),'forbids commit'),
 ('unknown proposal decision',lambda x:x['proposals'][0].update(target_decision_id='d2'),'unknown decision'),
 ('out of candidate',lambda x:x['proposals'][0].update(proposed_operator='op3'),'outside admissible'),
 ('unknown judgment in proposal',lambda x:x['proposals'][0].update(judgment_ids=['j2']),'unknown judgment'),
 ('early proposal',lambda x:x['proposals'][0].update(created_tick=2),'outside'),
 ('invalid future availability',lambda x:x['judgments'][0].update(available_tick=5),'unavailable'),
 ('premature window start',lambda x:x['proposals'][0].update(eligibility_window=[2,6]),'unavailable'),
 ('expired proposal',lambda x:x['proposals'][0].update(eligibility_window=[3,3]),'outside'),
 ('bad tick bool',lambda x:x['decisions'][0].update(decision_tick=True),'nonnegative'),
 ('incorrect SHA',lambda x:x['decisions'][0].update(context_sha256='bad'),'invalid SHA'),
 ('secret utility score field',lambda x:x['judgments'][0].update(score=1),'unexpected'),
 ('duplicate judgment',lambda x:x['judgments'].append(dict(x['judgments'][0])),'duplicate judgment'),
 ('duplicate proposal',lambda x:x['proposals'].append(dict(x['proposals'][0])),'duplicate proposal'),
 ('duplicated proposal ref',lambda x:x['proposals'][0].update(judgment_ids=['j1','j1']),'duplicate'),
])
def test_fail_closed(name,edit,message): reject(edit,message)

def test_same_origin_group_is_not_double_counted_as_independent_vote():
    x=example()
    j=dict(x['judgments'][0],judgment_id='j2',observer_id='C',source_evidence=['r2'])
    x['judgments'].append(j)
    assert validate_ledger(x)['declared_origin_groups_with_multiple_records']==1
    assert validate_ledger(x)['claimed_independent_votes']==0

def test_same_origin_conflicting_sign_fails():
    def change(x):
        x['judgments'].append(dict(x['judgments'][0],judgment_id='j2',sign=1))
    reject(change,'conflicting')

def test_proposal_cannot_mix_decisions():
    def change(x):
        x['decisions'].append(dict(x['decisions'][0], decision_id='d2',neuron_id='B'))
        x['judgments'].append(dict(x['judgments'][0],judgment_id='j2',decision_id='d2',
                                    observer_id='A',receiver_id='B',causal_origin_id='other'))
        x['proposals'][0]['judgment_ids']=['j1','j2']
    reject(change,'mixes decisions')

def test_exact_anchor_reconstruction_and_tamper_detection():
    w={'ok':True}
    source={'schema':'spk-bv-workload-value-observability-boundary/v0x',
            'status':'REPORT_ONLY_COST_OBSERVABILITY_NO_INFORMATIONAL_BENEFIT_IDENTIFICATION',
            'native_cells':15, 'native_arms_examined':45,'feedback_first_positive_delay_cells':6,
            'forward_outcome_conservation_cells':15,'input_source_sha256':{'a':H},
            'input_fixture_sha256':H}
    x=dict(source,status='SOURCE_RECOMPUTED_COST_ONLY_NO_INFORMATIONAL_BENEFIT_IDENTIFICATION',
           native_workloads_reexecuted_and_equal=True,source_sha256_reverified=True,
           cross_process_payload_equality_verified=False)
    a=verify_cost_anchor(x,w,lambda _: source)
    assert a['native_arms_reexecuted']==45 and a['cross_process_equality_verified'] is False
    for change in [lambda z:z.update(native_workloads_reexecuted_and_equal=False),
                   lambda z:z.update(native_cells=17),
                   lambda z:z.update(unexpected='forged'),
                   lambda z:z.update(status='REPORT_ONLY_COST_OBSERVABILITY_NO_INFORMATIONAL_BENEFIT_IDENTIFICATION'),
                   lambda z:z.update(cross_process_payload_equality_verified='false')]:
        tampered=copy.deepcopy(x);change(tampered)
        with pytest.raises(JudgmentContractError):verify_cost_anchor(tampered,w,lambda _:source)

def test_cli_shadow_empty_smoke_no_overwrite(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir()
    a=tmp_path/'v0x.json';b=tmp_path/'v0w.json';c=tmp_path/'report.json'
    a.write_text('{"x":1}',encoding='utf-8');b.write_text('{"w":2}',encoding='utf-8')
    monkeypatch.setattr(cli,'verify_cost_anchor',lambda _x,_w,_s: {
        'native_cells':15,'native_arms_reexecuted':45,'feedback_first_positive_delay_cells':6,
        'forward_conserved_cells':15,'source_hashes':{},'fixture_sha256':H,
        'cross_process_equality_verified':False})
    cmd=['--root',str(root),'--v0x',str(a),'--v0w',str(b),'--out',str(c)]
    assert cli.main(cmd)==0
    d=json.loads(c.read_text());assert d['status']==OUTPUT_STATUS
    assert d['contract_counts']['native_judgments_observed']==0
    assert cli.main(cmd)==2

def test_cli_bad_ledger_rejects_without_output(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir()
    a=tmp_path/'v0x.json';b=tmp_path/'v0w.json';c=tmp_path/'report.json';led=tmp_path/'ledger.json'
    a.write_text('{}');b.write_text('{}')
    led.write_text(json.dumps(dict(example(),proposals=[dict(example()['proposals'][0],verdict='commit')])))
    monkeypatch.setattr(cli,'verify_cost_anchor',lambda *_:{'native_cells':15})
    cmd=['--root',str(root),'--v0x',str(a),'--v0w',str(b),
         '--ledger',str(led),'--out',str(c)]
    assert cli.main(cmd)==2 and not c.exists()

def test_cli_rejects_same_input_and_alias_and_symlink(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir()
    a=tmp_path/'v0x.json';a.write_text('{}');b=tmp_path/'v0w.json';b.write_text('{}')
    c=tmp_path/'report.json'
    monkeypatch.setattr(cli,'verify_cost_anchor',lambda *_:{'native_cells':15})
    common=['--root',str(root),'--out',str(c)]
    assert cli.main(common+['--v0x',str(a),'--v0w',str(a)])==2
    alias=tmp_path/'alias.json';alias.symlink_to(b)
    assert cli.main(common+['--v0x',str(a),'--v0w',str(alias)])==2
    assert not c.exists()


def test_cli_rejects_repo_output(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir()
    a=tmp_path/'v0x.json';a.write_text('{}');b=tmp_path/'v0w.json';b.write_text('{}')
    monkeypatch.setattr(cli,'verify_cost_anchor',lambda *_:{'native_cells':15})
    assert cli.main(['--root',str(root),'--v0x',str(a),'--v0w',str(b),
                      '--out',str(root/'written.json')])==2
