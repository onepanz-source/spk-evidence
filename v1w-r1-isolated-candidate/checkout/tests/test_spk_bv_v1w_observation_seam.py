"""v1w adversarial, offline, source-verified, and CLI custody tests.

All fake source specimens are SYNTHETIC, not a claim of native API execution.
"""
from __future__ import annotations
import ast, json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import pytest

from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.frozen_observation_surface_v1v import audit_surface
import spk_bv_research.observation_seam_contract_v1w as mod
from search.spk_bv_v1w_observation_seam import main, NAMES

SCHED_SOURCE = b'''class LiveBVPlanV0e: pass
def execute_live_v0e(case, fabric, tplan, pplan, mplan, lplan, bv):
    log_emission(case)
    record_occurrence(fabric)
    deliver_ingress(bv)
    assess_feedback(bv)
    dispatch_batch(mplan)
    return {'forward': []}
'''
PRODUCER_SOURCE=b'''def fixture(program,ticks,**kwargs):
    return program, ticks
'''
ARCH_SOURCE=b'''def _admit(case, fabric):
    return ({}, {})
def _compute_local(node,state,timestamp,channels):
    return node
'''
TEST_SOURCE=b'''def test_placeholder():
    assert True
'''


def specimen(monkeypatch):
    blobs={mod.SCHED:SCHED_SOURCE,mod.PRODUCER:PRODUCER_SOURCE,
           mod.TEST:TEST_SOURCE,mod.ARCH:ARCH_SOURCE}
    hashes={k:sha256(v).hexdigest() for k,v in blobs.items()}
    compute=next(x for x in ast.parse(ARCH_SOURCE).body if isinstance(x,ast.FunctionDef)
                 and x.name=='_compute_local')
    compute_ast=sha256(ast.dump(compute,include_attributes=False).encode()).hexdigest()
    monkeypatch.setattr(mod,'EXPECTED_PINS',hashes)
    monkeypatch.setattr(mod,'EXPECTED_COMPUTE_AST',compute_ast)
    u={'frozen_native_sources': {
        'frozen_producer_sha256':{k:hashes[k] for k in mod.PINS},
        'frozen_a1_compute_source_sha256':hashes[mod.ARCH],
        'compute_function_ast_sha256':compute_ast,
        'compute_function_name':'_compute_local',
        'compute_function_positional_args':['node','state','timestamp','channels']},
        'reference_v1t_sha256':'a'*64, 'reference_v1u_sha256':'b'*64}
    from spk_bv_research.incremental_shadow_channel_v1u import (
        run_lab, PLANS, SCHEMA as U_SCHEMA, STATUS as U_STATUS)
    sessions=[run_lab(a,m,p,{'sender':2 if a=='original' else 0,
                              'ingress':2 if a=='original' else 0})
              for a in ('original','variant') for m in ('off','on')
              for p in PLANS if not(p=='contradictory_source' and a=='variant')]
    from spk_bv_research.frozen_observation_surface_v1v import audit_surface
    fake_u={
        'schema':U_SCHEMA,'status':U_STATUS,
        'source_kind':'ATTESTED_NATIVE_V1T_PLUS_RESEARCH_OWNED_INCREMENTAL_CLOCK',
        'inherited_native_v1t_recomputation_verified_in_this_run':True,
        'new_native_scheduler_runs_in_this_module':0,
        'lab_incremental_session_count':58,'lab_incremental_sessions':sessions,
        'native_scheduler_callback_connected':False,
        'native_receiver_received_live_control_packets':0,
        'native_authenticated_source_evidence':0,
        'native_independent_absence_certificates':0,
        'native_scored_receiver_judgments':0,'native_operator_updates':0,
        'native_learning_proven':False,
        'lab_tick_is_simulated_not_native':True,
        'lab_ingress_is_simulated_from_posthoc_count':True,
        'lab_control_loss_fails_closed':True,'lab_queue_overflow_fails_closed':True,
        'producer_posthoc_counts_withheld_from_receiver':True,
        'no_cross_world_event_pairing':True,
        'reference_v1t_sha256':'a'*64,'reference_v1m_sha256':'b'*64,
        'reference_v1s_sha256':'c'*64,'native_fixture_sha256':'d'*64,
        'frozen_native_sources':u['frozen_native_sources']}
    # v1v does not hardcode the archived hashes; its output remains a mock contract.
    v=audit_surface(fake_u,canon(fake_u),blobs)
    v['inherited_native_v1u_recomputation_verified_in_this_run']=True
    return v,blobs


def test_synthetic_static_probe_not_live(monkeypatch):
    v,blobs=specimen(monkeypatch)
    r=mod.analyze(v,canon(v),blobs=blobs)
    assert r['schema']==mod.SCHEMA and r['status']==mod.STATUS
    names=r['source_pinned_static_candidate_inventory']['candidate_count_by_category']
    assert names=={key:1 for key in mod.NAME_HINTS}
    for group in r['source_pinned_static_candidate_inventory']['bounded_callsite_examples'].values():
        assert len(group)==1 and group[0]['verified_hook'] is False
    assert r['native_observation_message_delivered_to_B'] is False
    assert r['native_event_callback_invoked'] is False
    assert r['source_files_modified'] is False
    assert len(r['proof_obligations_unmet'])==10
    assert all(x['verified'] is False for x in r['proof_obligations_unmet'])
    assert r['inherited_native_v1v_recomputation_verified_in_this_run'] is False


def test_offline_contract_never_claims_native(monkeypatch):
    v,_=specimen(monkeypatch);r=mod.analyze(v,canon(v))
    assert r['source_pinned_static_candidate_inventory'] is None
    assert r['native_source_readonly_bytes_rechecked_in_this_run'] is False
    assert r['inherited_native_v1v_recomputation_verified_in_this_run'] is False


@pytest.mark.parametrize('key,bad',[
 ('schema','wrong'),('status','wrong'),('source_kind','wrong'),
 ('frozen_source_bytes_rechecked_in_this_run',False),
 ('inherited_native_v1u_recomputation_verified_in_this_run',False),
 ('public_live_event_hook_semantics_verified',True),
 ('native_per_event_callback_invoked',True),
 ('native_source_to_B_control_delivery_verified',True),
 ('native_independent_absence_certificate_verified',True),
 ('native_clock_or_coverage_certified',True),
 ('native_scored_receiver_judgments',1),('native_operator_updates',1),
 ('native_learning_proven',True),('no_new_scheduler_executions_in_v1v',False),
 ('integration_requirements_not_yet_satisfied',[]),
 ('reference_v1u_sha256','g'*64),('actual_native_API_surface',None),
 ('frozen_native_sources',{}),
])
def test_prev_authority_forgery_rejected(monkeypatch,key,bad):
    v,blobs=specimen(monkeypatch);v[key]=bad
    with pytest.raises(InterventionError):mod.analyze(v,canon(v),blobs=blobs)


@pytest.mark.parametrize('field,bad',[
 ('scheduler_entrypoint',{'name':'other'}),
 ('fixture_entrypoint',{'name':'other'}),
 ('neuron_compute_entrypoint',{'name':'other'}),
 ('observation_class','LIVE_HOOK'),('producer_files_sha256',{}),
 ('plan_class_found',False),
])
def test_source_surface_forgery_rejected(monkeypatch,field,bad):
    v,blobs=specimen(monkeypatch);v['actual_native_API_surface'][field]=bad
    with pytest.raises(InterventionError):mod.analyze(v,canon(v),blobs=blobs)


@pytest.mark.parametrize('field',(*mod.EXPECTED_PINS,))
def test_drift_in_each_source_rejected(monkeypatch,field):
    v,blobs=specimen(monkeypatch);blobs[field]+=b'\n# changed'
    with pytest.raises(InterventionError,match='source|Source|SHA256'):
        mod.analyze(v,canon(v),blobs=blobs)


def test_source_missing_extra_bogus_bytes_rejected(monkeypatch):
    v,blobs=specimen(monkeypatch)
    for change in [dict(),{**blobs,'anything.py':b'x'},
                   {**blobs,mod.SCHED:'nonbytes'}]:
        with pytest.raises(InterventionError):mod.analyze(v,canon(v),blobs=change)


def test_noncanonical_json_rejected(monkeypatch):
    v,blobs=specimen(monkeypatch)
    with pytest.raises(InterventionError):mod.analyze(v,json.dumps(v).encode(),blobs=blobs)


def test_compute_ast_change_even_with_rehashed_byte_source_rejected(monkeypatch):
    v,blobs=specimen(monkeypatch)
    src=blobs[mod.ARCH].replace(b'return node',b'return state')
    blobs[mod.ARCH]=src
    mod.EXPECTED_PINS[mod.ARCH]=sha256(src).hexdigest()
    v['frozen_native_sources']['frozen_a1_compute_source_sha256']=sha256(src).hexdigest()
    v['actual_native_API_surface']['producer_files_sha256'][mod.ARCH]=sha256(src).hexdigest()
    with pytest.raises(InterventionError,match='AST drift'):
        mod.analyze(v,canon(v),blobs=blobs)


@pytest.mark.parametrize('old,new',[
 (b'def execute_live_v0e',b'def execute_altered'),
 (b'class LiveBVPlanV0e',b'class OtherPlan'),
])
def test_missing_named_native_component_rejected_even_if_rehashed(monkeypatch,old,new):
    v,blobs=specimen(monkeypatch)
    src=blobs[mod.SCHED].replace(old,new)
    blobs[mod.SCHED]=src
    digest=sha256(src).hexdigest()
    mod.EXPECTED_PINS[mod.SCHED]=digest
    v['frozen_native_sources']['frozen_producer_sha256'][mod.SCHED]=digest
    v['actual_native_API_surface']['producer_files_sha256'][mod.SCHED]=digest
    with pytest.raises(InterventionError):mod.analyze(v,canon(v),blobs=blobs)


def test_all_events_are_only_static_name_hints(monkeypatch):
    v,blobs=specimen(monkeypatch)
    r=mod.source_candidate_inventory(v,blobs)
    assert not r['native_event_semantics_established']
    assert not r['native_listener_or_callback_installed']
    assert all(not x['verified_hook'] for group in r['bounded_callsite_examples'].values() for x in group)


def test_empty_names_never_prove_no_hook(monkeypatch):
    v,blobs=specimen(monkeypatch)
    original=blobs[mod.SCHED]
    mutated=original.replace(b'log_emission',b'foo_1').replace(b'record_occurrence',b'foo_2')\
        .replace(b'deliver_ingress',b'foo_3').replace(b'assess_feedback',b'foo_4')\
        .replace(b'dispatch_batch',b'foo_5')
    blobs[mod.SCHED]=mutated
    digest=sha256(mutated).hexdigest()
    mod.EXPECTED_PINS[mod.SCHED]=digest
    v['frozen_native_sources']['frozen_producer_sha256'][mod.SCHED]=digest
    v['actual_native_API_surface']['producer_files_sha256'][mod.SCHED]=digest
    r=mod.analyze(v,canon(v),blobs=blobs)
    assert not any(r['source_pinned_static_candidate_inventory']['candidate_count_by_category'].values())
    assert not r['native_event_callback_invoked']
    assert r['integration_path_selection'].endswith('NOT_INSTALLED')


def test_pinned_read_fails_on_symlink_and_drift(monkeypatch,tmp_path):
    v,blobs=specimen(monkeypatch)
    root=tmp_path/'checkout';root.mkdir()
    for rel,raw in blobs.items():
        path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    assert mod.read_pinned_sources(root)==blobs
    path=root/mod.ARCH;path.write_bytes(b'changed')
    with pytest.raises(InterventionError):mod.read_pinned_sources(root)
    path.write_bytes(blobs[mod.ARCH]); path.unlink();path.symlink_to(root/mod.SCHED)
    with pytest.raises(InterventionError):mod.read_pinned_sources(root)


def _cli_fixture(monkeypatch,tmp_path):
    import search.spk_bv_v1w_observation_seam as cli
    v,blobs=specimen(monkeypatch)
    root=tmp_path/'checkout';root.mkdir()
    for rel,raw in blobs.items():
        path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    args=['--root',str(root)]
    paths={}
    for name in NAMES:
        path=tmp_path/(name+'.json');path.write_bytes(canon(v) if name=='v1v' else b'{}\n')
        paths[name]=path;args.extend(('--'+name,str(path)))
    out=tmp_path/'v1w.json';args.extend(('--out',str(out)))
    return cli,v,blobs,root,paths,out,args


def test_cli_contract_only_rejects_native_mode_without_full_chain(monkeypatch,tmp_path):
    cli,v,blobs,root,paths,out,args=_cli_fixture(monkeypatch,tmp_path)
    assert cli.main(['--root',str(root),'--v1v',str(paths['v1v']),
                     '--out',str(out),'--contract-only'])==0
    report=json.loads(out.read_bytes())
    assert not report['native_source_readonly_bytes_rechecked_in_this_run']
    assert not report['inherited_native_v1v_recomputation_verified_in_this_run']
    assert cli.main(['--root',str(root),'--v1v',str(paths['v1v']),
                     '--out',str(tmp_path/'second.json')])==2


def test_cli_full_requires_replay_byte_identity(monkeypatch,tmp_path):
    cli,v,blobs,root,paths,out,args=_cli_fixture(monkeypatch,tmp_path)
    called=[]
    def fake_vmain(argv):
        called.append(argv)
        Path(argv[argv.index('--out')+1]).write_bytes(paths['v1v'].read_bytes());return 0
    monkeypatch.setattr(cli,'vmain',fake_vmain)
    assert cli.main(args)==0
    report=json.loads(out.read_bytes())
    assert len(called)==1 and '--v1u' in called[0]
    assert report['inherited_native_v1v_recomputation_verified_in_this_run'] is True
    assert report['native_source_readonly_bytes_rechecked_in_this_run'] is True
    assert report['native_observation_message_delivered_to_B'] is False
    assert report['native_operator_updates']==0
    assert cli.main(args)==2


@pytest.mark.parametrize('failure',('nonzero','wrong_report','changed_predecessor','changed_source'))
def test_cli_full_refuses_failed_replay_and_toctou(monkeypatch,tmp_path,failure):
    cli,v,blobs,root,paths,out,args=_cli_fixture(monkeypatch,tmp_path)
    def fake(argv):
        if failure=='nonzero':return 2
        dest=Path(argv[argv.index('--out')+1])
        dest.write_bytes(paths['v1v'].read_bytes() if failure!='wrong_report' else b'{}\n')
        if failure=='changed_predecessor':paths['v1v'].write_bytes(paths['v1v'].read_bytes()+b'\n')
        if failure=='changed_source':
            p=root/mod.SCHED;p.write_bytes(p.read_bytes()+b'\n')
        return 0
    monkeypatch.setattr(cli,'vmain',fake)
    assert cli.main(args)==2
    assert not out.exists()


def test_cli_rejects_predecessor_inside_root(monkeypatch,tmp_path):
    cli,v,blobs,root,paths,out,args=_cli_fixture(monkeypatch,tmp_path)
    inside=root/'in.json';inside.write_bytes(canon(v))
    assert cli.main(['--root',str(root),'--v1v',str(inside),'--contract-only',
                     '--out',str(tmp_path/'no.json')])==2


def test_untrusted_json_cannot_authorize_native_stream(monkeypatch):
    v,blobs=specimen(monkeypatch)
    v['native_source_to_B_control_delivery_verified']=True
    with pytest.raises(InterventionError):mod.analyze(v,canon(v))


def test_uploaded_real_v1v_offline_contract():
    p=Path('/mnt/data/spk-bv-v1v-frozen-observation-surface.json')
    if not p.is_file():pytest.skip('uploaded report not mounted in remote gate')
    raw=p.read_bytes();v=json.loads(raw)
    # The test environment itself is not authorized to inspect frozen sources.
    report=mod.analyze(v,raw)
    assert report['reference_v1v_sha256']==sha256(raw).hexdigest()
    assert report['source_pinned_static_candidate_inventory'] is None
    assert not report['native_event_callback_invoked']
