"""BV v1r standalone synthetic fixtures, accounting and adversarial CLI safety."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research import native_allocation_boundary_v1r as model
from spk_bv_research.native_factorial_interaction_v1q import (
    SCHEMA as Q_SCHEMA, STATUS as Q_STATUS, factorial_coefficients,
)
from search import spk_bv_v1r_allocation_boundary as cli

COUNTS={
    'none':(2,2,2),'A':(0,0,0),'B':(2,1,1),'C':(2,2,1),
    'AB':(0,0,0),'AC':(0,0,0),'BC':(2,1,0),'ABC':(0,0,0),
}


def specimen():
    runs={};intv={}
    for arm,(a,b,c) in COUNTS.items():
        intv[arm]={'arm':arm,'changed_nodes':[] if arm=='none' else list(arm),
                   'mutations':{n:{'instruction_index':2 if n=='A' else 1}
                                for n in ([] if arm=='none' else arm)}}
        runs[arm]={}
        for mode in model.MODES:
            runs[arm][mode]={
                'forward':{'batches':2+a+b+c,'emissions':a+b+c,
                           'occurrences':a+b,'link_grants':a+b,'terminal':c},
                'edges':{'A->B:7->0':a,'B->C:7->0':b},
                'emissions_by_neuron':{'A':a,'B':b,'C':c},
                'feedback_assessments':c if mode=='on' else 0,
                'feedback_deliveries':2*c if mode=='on' else 0}
    tables={};coefs={}
    for mode in model.MODES:
        tables[mode]={};coefs[mode]={}
        for metric in model.METRICS:
            table={}
            for arm,(a,b,c) in COUNTS.items():
                table[arm]={'terminal':c,'A->B:7->0':a,'B->C:7->0':b,
                            'feedback_assessments':c if mode=='on' else 0}[metric]
            tables[mode][metric]=table
            coefs[mode][metric]=factorial_coefficients(table)
    return {
        'schema':Q_SCHEMA,'status':Q_STATUS,
        'source_kind':'FROZEN_NATIVE_SCHEDULER_EXOGENOUS_FULL_FACTORIAL',
        'native_v1p_recomputation_verified_in_this_run':True,
        'native_factorial_repeatability_attested_in_this_run':True,
        'native_scheduler_executions_in_matrix':16,
        'factorial_prefix_negative_control_pairs_verified':16,
        'event_count_interaction_present':True,
        'native_receiver_exposed_to_full_matrix':False,
        'native_independent_absence_certificates':0,
        'native_scored_receiver_judgments':0,'native_operator_updates':0,
        'native_learning_proven':False,'network_utility_identified':False,
        'interaction_coefficients_are_utility_or_credit':False,
        'native_fixture_sha256':'0'*64,
        'frozen_native_sources':{'synthetic-source':'not-authority'},
        'reference_v1p_sha256':'1'*64,
        'factorial_observed_counts':tables,
        'factorial_mobius_count_coefficients':coefs,
        'factorial_runs':runs,'interventions':intv,
    }


def run_audit(doc=None):
    d=specimen() if doc is None else doc
    return model.analyze(d,model.canon(d))


def test_exact_allocation_terminal():
    r=run_audit();a=r['posthoc_rational_allocation']['off']['terminal']
    assert a['suppress_activity']['equal_permutation_average']=={'A':'1','B':'1/2','C':'1/2'}
    assert a['preserve_activity']['equal_permutation_average']=={'A':'-1','B':'-1/2','C':'-1/2'}
    assert a['suppress_activity']['full_coalition_delta']=='2'
    assert a['preserve_activity']['full_coalition_delta']=='-2'
    assert a['suppress_activity']['any_order_sensitive'] is True
    assert r['nonadditivity_diagnostics']['off']['terminal']=={
        'baseline':2,'full_coalition':0,'sum_of_isolated_deltas':-4,
        'observed_full_delta':-2,'nonadditive_correction':2,
        'nonzero_interaction_terms':{'AB':1,'AC':1}}


def test_full_path_marginals():
    d=run_audit()['posthoc_rational_allocation']['off']['terminal']['suppress_activity']
    assert len(d['order_marginals'])==6
    assert d['order_marginals']['ABC']=={'A':'2','B':'0','C':'0'}
    assert d['order_marginals']['BCA']=={'A':'0','B':'1','C':'1'}
    for x in d['order_marginals'].values():
        assert sum((Fraction(s) for s in x.values()),Fraction())==2
    assert d['order_sensitive']=={'A':True,'B':True,'C':True}


def test_different_metric_cannot_be_identified_with_terminal():
    r=run_audit()['posthoc_rational_allocation']['off']
    pol='suppress_activity'
    assert r['A->B:7->0'][pol]['equal_permutation_average']=={'A':'2','B':'0','C':'0'}
    assert r['B->C:7->0'][pol]['equal_permutation_average']=={'A':'3/2','B':'1/2','C':'0'}
    assert r['terminal'][pol]['equal_permutation_average']=={'A':'1','B':'1/2','C':'1/2'}


def test_on_feedback_not_native_judgment():
    r=run_audit()
    assert r['nonadditivity_diagnostics']['off']['feedback_assessments']['baseline']==0
    assert r['posthoc_rational_allocation']['on']['feedback_assessments']==r['posthoc_rational_allocation']['on']['terminal']
    assert all(r[k] == 0 for k in ('native_scored_receiver_judgments','native_operator_updates','new_native_scheduler_runs_in_this_module'))
    assert r['native_v1q_recomputation_verified_in_this_run'] is False
    assert r['native_learning_proven'] is False and r['causal_credit_or_utility_identified'] is False


def test_canon_and_source_pin():
    q=specimen();raw=model.canon(q)
    r=model.analyze(q,raw)
    from hashlib import sha256
    assert r['reference_v1q_sha256']==sha256(raw).hexdigest()
    assert model.canon(r)==model.canon(json.loads(model.canon(r)))
    with pytest.raises(InterventionError):model.analyze(q,raw+b' ')
    with pytest.raises(InterventionError):model.analyze(q,raw[:-1])


@pytest.mark.parametrize('path,value',[ 
    (('native_v1p_recomputation_verified_in_this_run',),False),
    (('native_factorial_repeatability_attested_in_this_run',),False),
    (('native_receiver_exposed_to_full_matrix',),True),
    (('native_scored_receiver_judgments',),1),
    (('native_operator_updates',),1),
    (('native_learning_proven',),True),
    (('network_utility_identified',),True),
    (('interaction_coefficients_are_utility_or_credit',),True),
    (('native_scheduler_executions_in_matrix',),15),
    (('factorial_prefix_negative_control_pairs_verified',),15),
    (('native_fixture_sha256',),'bad'),
    (('frozen_native_sources',),{}),
    (('factorial_observed_counts','on','terminal','ABC'),1),
    (('factorial_observed_counts','off','terminal','A'),True),
    (('factorial_mobius_count_coefficients','on','terminal','AB'),999),
    (('factorial_runs','C','on','forward','terminal'),3),
    (('factorial_runs','B','on','edges','B->C:7->0'),2),
    (('factorial_runs','none','off','forward','emissions'),8),
    (('factorial_runs','AB','on','feedback_assessments'),1),
    (('factorial_runs','B','on','feedback_deliveries'),3),
    (('factorial_runs','none','off','emissions_by_neuron','A'),False),
    (('factorial_runs','ABC','off','forward','link_grants'),1),
    (('interventions','A','changed_nodes'),['B']),
    (('interventions','ABC','mutations'),{}),
    (('factorial_observed_counts','on','feedback_assessments','C'),0),
    (('factorial_observed_counts','off','feedback_assessments','B'),1),
    (('schema',),'wrong-schema'),
    (('status',),'wrong-status'),
    (('source_kind',),'NATIVE_RECEIVER_CREDIT'),
])
def test_adversarial_report_tampering(path,value):
    d=specimen();o=d
    for k in path[:-1]:o=o[k]
    o[path[-1]]=value
    with pytest.raises(InterventionError):run_audit(d)


@pytest.mark.parametrize('d',[
    {'none':2,'A':0,'B':1},
    {a:0 for a in model.ARMS if a!='BC'},
    {a:True for a in model.ARMS},
    {a:-1 for a in model.ARMS},
    {a:0.0 for a in model.ARMS},
])
def test_bad_count_tables(d):
    with pytest.raises(InterventionError):model.allocate(d,-1)


@pytest.mark.parametrize('nodes',[('B','B'),('Z',),('A','D'),('B','A','B')])
def test_invalid_coalitions(nodes):
    with pytest.raises(InterventionError):model.arm_of(nodes)


def test_cli_fails_closed_before_native_execution(tmp_path,monkeypatch,capsys):
    root=tmp_path/'project';root.mkdir();docs=tmp_path/'docs';docs.mkdir()
    q=specimen();names=cli.NAMES
    paths={n:docs/(n+'.json') for n in names}
    for n,p in paths.items():p.write_bytes(model.canon(q) if n=='v1q' else b'{}\n')
    argv=['--root',str(root)]
    for n in names:argv+=['--'+n,str(paths[n])]
    target=docs/'out.json';argv+=['--out',str(target)]
    def happy(args):
        Path(args[-1]).write_bytes(model.canon(q));return 0
    monkeypatch.setattr(cli,'qmain',happy)
    assert cli.main(argv)==0
    out=json.loads(target.read_bytes())
    assert out['native_v1q_recomputation_verified_in_this_run'] is True
    assert out['new_native_scheduler_runs_in_this_module']==0
    assert cli.main(argv)==2  # no clobber
    target.unlink()
    monkeypatch.setattr(cli,'qmain',lambda args: 2)
    assert cli.main(argv)==2 and not target.exists()
    def altered(args):
        Path(args[-1]).write_bytes(model.canon({'invalid':True}));return 0
    monkeypatch.setattr(cli,'qmain',altered)
    assert cli.main(argv)==2 and not target.exists()


def test_cli_rejects_alias_input_and_repository_path(tmp_path,monkeypatch):
    root=tmp_path/'work';root.mkdir();other=tmp_path/'outside';other.mkdir()
    args=['--root',str(root)]
    for n in cli.NAMES:
        p=other/(n+'.json');p.write_bytes(model.canon(specimen()) if n=='v1q' else b'{}\n')
        args+=['--'+n,str(p)]
    args+=['--out',str(other/'result.json')]
    assert cli.main(args)==2 # cannot regenerate using missing native
    aliased=list(args)
    ix=aliased.index('--v1p')+1;aliased[ix]=aliased[aliased.index('--v1q')+1]
    assert cli.main(aliased)==2
    internal=list(args);internal[internal.index('--v1q')+1]=str(root/'in.json')
    (root/'in.json').write_bytes(model.canon(specimen()))
    assert cli.main(internal)==2


def test_uploaded_file_is_not_a_test_dependency():
    assert specimen()['source_kind']=='FROZEN_NATIVE_SCHEDULER_EXOGENOUS_FULL_FACTORIAL'
