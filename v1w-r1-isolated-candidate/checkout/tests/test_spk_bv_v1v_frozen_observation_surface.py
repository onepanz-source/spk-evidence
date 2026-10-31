"""Self-contained v1v read-only native surface audit + fail-closed tests."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast,json
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.incremental_shadow_channel_v1u import run_lab,PLANS,SCHEMA as U_SCHEMA,STATUS as U_STATUS
from spk_bv_research.frozen_observation_surface_v1v import (
    SCHEMA,STATUS,PINS,PRODUCER,SCHED,TEST,ARCH,
    audit_surface,read_pinned_sources,validate_predecessor,REQUIRED_BOUNDARY,
)
from search.spk_bv_v1v_frozen_observation_surface import main,NAMES


def specimen(scheduler='''class LiveBVPlanV0e: pass\ndef execute_live_v0e(case,fabric,capacity,clock,plan):\n    return {'forward':[]}\n'''):
    files={SCHED:scheduler.encode(),PRODUCER:b'def fixture():\n    return (1,2,3)\n',
           TEST:b'def test_fixture():\n    assert True\n',
           ARCH:b'def _admit(case,fabric):\n    return ({},{})\ndef _compute_local(node,state,timestamp,channels):\n    return []\n'}
    compute=next(n for n in ast.parse(files[ARCH]).body
                 if isinstance(n,ast.FunctionDef) and n.name=='_compute_local')
    frozen={'frozen_producer_sha256':{n:sha256(files[n]).hexdigest() for n in PINS},
            'frozen_a1_compute_source_sha256':sha256(files[ARCH]).hexdigest(),
            'compute_function_ast_sha256':sha256(ast.dump(compute,include_attributes=False).encode()).hexdigest(),
            'compute_function_name':'_compute_local',
            'compute_function_positional_args':['node','state','timestamp','channels']}
    sessions=[run_lab(a,m,p,{'sender':2 if a=='original' else 0,
                            'ingress':2 if a=='original' else 0})
              for a in ('original','variant') for m in ('off','on')
              for p in PLANS if not(p=='contradictory_source' and a=='variant')]
    u={'schema':U_SCHEMA,'status':U_STATUS,
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
       'frozen_native_sources':frozen}
    return u,files


def test_real_user_report_constraint():
    """This test is synthetic, with the same frozen-status contract as uploaded v1u."""
    u,files=specimen();validate_predecessor(u,canon(u))
    r=audit_surface(u,canon(u),files)
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['actual_native_API_surface']['scheduler_entrypoint']['positional']==[
        'case','fabric','capacity','clock','plan']
    assert not r['public_live_event_hook_semantics_verified']
    assert not r['native_source_to_B_control_delivery_verified']
    assert not r['native_per_event_callback_invoked']
    assert len(r['integration_requirements_not_yet_satisfied'])==len(REQUIRED_BOUNDARY)==8
    assert not r['inherited_native_v1u_recomputation_verified_in_this_run']


def test_offline_does_not_claim_native_source():
    u,files=specimen();r=audit_surface(u,canon(u))
    assert r['source_kind']=='PREDECESSOR_BOUND_OFFLINE_CONTRACT_ONLY'
    assert not r['frozen_source_bytes_rechecked_in_this_run']
    assert r['actual_native_API_surface'] is None


@pytest.mark.parametrize('key,bad',[
 ('schema','wrong'),('status','wrong'),('source_kind','wrong'),
 ('inherited_native_v1t_recomputation_verified_in_this_run',False),
 ('native_scheduler_callback_connected',True),
 ('native_receiver_received_live_control_packets',1),
 ('native_independent_absence_certificates',1),
 ('native_authenticated_source_evidence',1),
 ('native_scored_receiver_judgments',1),('native_operator_updates',1),
 ('native_learning_proven',True),('lab_incremental_session_count',57),
 ('lab_tick_is_simulated_not_native',False),
 ('lab_ingress_is_simulated_from_posthoc_count',False),
 ('producer_posthoc_counts_withheld_from_receiver',False),
 ('lab_control_loss_fails_closed',False),('lab_queue_overflow_fails_closed',False),
 ('reference_v1t_sha256','g'*64),
 ('frozen_native_sources',{}),
])
def test_forbidden_promotion_rejected(key,bad):
    u,files=specimen();u[key]=bad
    with pytest.raises(InterventionError):audit_surface(u,canon(u),files)


@pytest.mark.parametrize('mutator',[
 lambda u: u['lab_incremental_sessions'].pop(),
 lambda u: u['lab_incremental_sessions'][0].update(native_stream_messages_delivered=1),
 lambda u: u['lab_incremental_sessions'][0]['receiver_view'].update(native_authority=True),
 lambda u: u['lab_incremental_sessions'][0]['receiver_view'].update(native_receiver=True),
 lambda u: u['lab_incremental_sessions'][0]['receiver_view'].update(receiver_scored_judgment=True),
 lambda u: u['lab_incremental_sessions'][0]['receiver_view'].update(native_absence_certificate=True),
 lambda u: u['lab_incremental_sessions'][0]['receiver_view'].update(operator_update_committed=True),
 lambda u: u['lab_incremental_sessions'][0].update(lab_clock_not_native=False),
 lambda u: u['lab_incremental_sessions'][1].update(plan='all_disclosed'),
 lambda u: u['lab_incremental_sessions'][0]['experimenter_source_counts_not_in_B_view'].update(sender=23),
])
def test_tampered_session_rejected(mutator):
    u,files=specimen();mutator(u)
    with pytest.raises(InterventionError):audit_surface(u,canon(u),files)


@pytest.mark.parametrize('field',(*PINS,ARCH))
def test_frozen_source_hash_drift_rejected(field):
    u,files=specimen();files[field]+=b'\n# mutated\n'
    with pytest.raises(InterventionError,match='sha256|SHA256'):
        audit_surface(u,canon(u),files)


@pytest.mark.parametrize('old,new',[
 ('execute_live_v0e','execute_new'),('LiveBVPlanV0e','Changed'),
 ('def _admit','def _other'),('def _compute_local','def _compute_new'),
 ('def fixture','def not_fixture'),
])
def test_missing_contract_names_rejected(old,new):
    u,files=specimen()
    field=ARCH if '_admit' in old or '_compute_local' in old else PRODUCER if 'fixture' in old else SCHED
    files[field]=files[field].replace(old.encode(),new.encode())
    if field==ARCH:u['frozen_native_sources']['frozen_a1_compute_source_sha256']=sha256(files[ARCH]).hexdigest()
    else:u['frozen_native_sources']['frozen_producer_sha256'][field]=sha256(files[field]).hexdigest()
    with pytest.raises(InterventionError):audit_surface(u,canon(u),files)


def test_callback_parameter_is_only_a_hint():
    u,files=specimen('''class LiveBVPlanV0e: pass\ndef execute_live_v0e(case,plan,on_event=None):\n    return {'forward':[]}\n''')
    r=audit_surface(u,canon(u),files)
    assert 'on_event' in r['actual_native_API_surface']['scheduler_entrypoint']['possible_callback_name_hints']
    assert r['native_per_event_callback_invoked'] is False
    assert r['public_live_event_hook_semantics_verified'] is False


def test_noncanonical_input_rejected():
    u,files=specimen()
    with pytest.raises(InterventionError):audit_surface(u,json.dumps(u).encode(),files)


def test_empty_or_extra_source_files_fail_closed():
    u,files=specimen()
    with pytest.raises(InterventionError):audit_surface(u,canon(u),{})
    f=dict(files);f['extra.py']=b'x'
    with pytest.raises(InterventionError):audit_surface(u,canon(u),f)


def test_pinned_source_reads_and_symlink_denial(tmp_path):
    u,files=specimen();root=tmp_path/'repo';root.mkdir()
    for rel,b in files.items():
        path=root/rel;path.parent.mkdir(exist_ok=True,parents=True);path.write_bytes(b)
    assert read_pinned_sources(root,u)==files
    t=root/TEST;t.unlink();t.symlink_to(root/SCHED)
    with pytest.raises(InterventionError):read_pinned_sources(root,u)


def test_cli_offline_stays_offline_and_fails_native_without_chain(tmp_path):
    u,files=specimen(); root=tmp_path/'repo';root.mkdir()
    p=tmp_path/'v1u.json';p.write_bytes(canon(u))
    out=tmp_path/'v1v.json'
    assert main(['--root',str(root),'--v1u',str(p),'--contract-only',
                 '--out',str(out)])==0
    obj=json.loads(out.read_bytes())
    assert obj['inherited_native_v1u_recomputation_verified_in_this_run'] is False
    assert obj['frozen_source_bytes_rechecked_in_this_run'] is False
    assert obj['actual_native_API_surface'] is None
    assert main(['--root',str(root),'--v1u',str(p),
                 '--out',str(tmp_path/'new.json')])==2
    assert not (tmp_path/'new.json').exists()
    assert main(['--root',str(root),'--v1u',str(p),'--contract-only',
                 '--out',str(out)])==2


def test_referenced_v1u_file_must_be_outside_repository(tmp_path):
    u,files=specimen();root=tmp_path/'repo';root.mkdir()
    p=root/'in.json';p.write_bytes(canon(u))
    assert main(['--root',str(root),'--v1u',str(p),'--contract-only',
                 '--out',str(tmp_path/'v1v.json')])==2


def test_no_native_proof_assertion_from_ast_attributes():
    u,files=specimen('''class LiveBVPlanV0e: pass\nasync def execute_live_v0e(*args, **kwargs):\n    yield 'event'\n''')
    r=audit_surface(u,canon(u),files)
    sig=r['actual_native_API_surface']['scheduler_entrypoint']
    assert sig['async_function'] and sig['has_varargs'] and sig['has_kwargs']
    assert not r['native_source_to_B_control_delivery_verified']


def test_uploaded_fixture_source_injected_cannot_rewrite_core(tmp_path):
    u,files=specimen(); f=dict(files)
    source=f[SCHED].replace(b"{'forward':[]}",b"{'forward': [1]}")
    f[SCHED]=source
    with pytest.raises(InterventionError):audit_surface(u,canon(u),f)


def _mock_native_files(tmp_path):
    import search.spk_bv_v1v_frozen_observation_surface as cli
    u,files=specimen();root=tmp_path/'repo';root.mkdir()
    for rel,blob in files.items():
        path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
    args=['--root',str(root)]
    prior={}
    for name in NAMES:
        p=tmp_path/(name+'.json')
        p.write_bytes(canon(u) if name=='v1u' else b'{}\n')
        prior[name]=p;args+=['--'+name,str(p)]
    out=tmp_path/'final.json';args+=['--out',str(out)]
    return cli,u,root,prior,out,args


def test_cli_native_mode_requires_exact_recomputation(monkeypatch,tmp_path):
    cli,u,root,prior,out,args=_mock_native_files(tmp_path)
    observed=[]
    def matched_replay(argv):
        observed.append(argv)
        Path(argv[argv.index('--out')+1]).write_bytes(prior['v1u'].read_bytes())
        return 0
    monkeypatch.setattr(cli,'umain',matched_replay)
    assert cli.main(args)==0
    assert len(observed)==1 and '--v1t' in observed[0]
    r=json.loads(out.read_bytes())
    assert r['frozen_source_bytes_rechecked_in_this_run'] is True
    assert r['inherited_native_v1u_recomputation_verified_in_this_run'] is True
    assert r['native_source_to_B_control_delivery_verified'] is False
    assert r['native_independent_absence_certificate_verified'] is False


@pytest.mark.parametrize('failure',('wrong_blob','nonzero','changed_source','changed_predecessor'))
def test_cli_native_mode_rejects_failed_chain_or_mutation(monkeypatch,tmp_path,failure):
    cli,u,root,prior,out,args=_mock_native_files(tmp_path)
    def mock_replay(argv):
        if failure=='nonzero':return 2
        Path(argv[argv.index('--out')+1]).write_bytes(
            b'{}\n' if failure=='wrong_blob' else prior['v1u'].read_bytes())
        if failure=='changed_source':
            p=root/SCHED;p.write_bytes(p.read_bytes()+b'\n# mutated\n')
        if failure=='changed_predecessor':
            p=prior['v1u'];p.write_bytes(p.read_bytes()+b'\n')
        return 0
    monkeypatch.setattr(cli,'umain',mock_replay)
    assert cli.main(args)==2
    assert not out.exists()
