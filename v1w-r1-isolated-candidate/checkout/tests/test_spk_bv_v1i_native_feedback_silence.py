"""v1i bound after v1h native execution; these are synthetic contract doubles."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_network_counterfactual_v1h import SCHEMA as H_SCHEMA, STATUS as H_STATUS
from spk_bv_research.native_feedback_silence_v1i import audit,SCHEMA,STATUS
from search import spk_bv_v1i_native_feedback_silence as cli

GB=b'v1g1 synthetic pinned proof'
DB=b'v1d synthetic pinned proof'

def sha(x):return hashlib.sha256(x).hexdigest()

def fixture():
    def run(n,edges):
        return {'batches':6 if n else 2,'emissions':6 if n else 0,
                'link_grants':4 if n else 0,'occurrences':4 if n else 0,
                'terminal':2 if n else 0,'edges':edges,'states_sha256':sha(b'states'+bytes([n]))}
    o=run(1,{'A->B:7->0':2,'B->C:7->0':2});v=run(0,{})
    h={'schema':H_SCHEMA,'status':H_STATUS,'real_variant_full_fabric_replay':True,
       'experiment_kind':'PRE_EPISODE_COPY_INTERVENTION',
       'conditional_direct_A_to_C':False,
       'v1e_hypothetical_A_to_C_direct_promoted':False,
       'variant_off_on_forward_outcomes_equal':True,
       'reference_v1g1_file_sha256':sha(GB),'reference_v1d_file_sha256':sha(DB),
       'frozen_native_sources':{'sha':'frozen'},'native_fixture_sha256':sha(b'fixture'),
       'intervention':{'sender':'A','instruction_index':2,
            'original_instruction':['CMP',1],'variant_instruction':['CMP',2],
            'original_nodes_unchanged':True,
            'static_fabric_shared_immutable':True,'external_events_preserved':True},
       'native_scored_receiver_judgments':0,'native_updates_applied':0,
       'native_learning_proven':False,'network_utility_identified':False,
       'original':{'off':copy.deepcopy(o),'on':copy.deepcopy(o),
                  'off_result_sha256':sha(b'oo'),'on_result_sha256':sha(b'on')},
       'variant':{'off':copy.deepcopy(v),'on':copy.deepcopy(v),
                  'off_result_sha256':sha(b'vo'),'on_result_sha256':sha(b'vn')},
       'native_feedback_assessments':{'original_on':2,'variant_on':0},
       'native_feedback_deliveries':{'original_on':4,'variant_on':0}}
    for arm in ('off','on'):
        h[f'{arm}_variant_minus_original']={k:h['variant'][arm][k]-h['original'][arm][k]
             for k in ('batches','emissions','terminal','occurrences','link_grants')}
    return h

def run(h):
    raw=json.dumps(h,sort_keys=True).encode()
    return audit(h,raw,g_bytes=GB,d_bytes=DB)


def test_happy_boundary_and_polarity():
    h=fixture();pre=copy.deepcopy(h);r=run(h)
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['original_to_variant_network']['forward_occurrences']==[4,0]
    assert r['original_to_variant_network']['A_to_B_occurrences']==[2,0]
    assert r['original_to_variant_network']['B_to_C_occurrences']==[2,0]
    assert r['original_to_variant_network']['feedback_assessments_on']==[2,0]
    assert r['original_to_variant_network']['feedback_deliveries_on']==[4,0]
    assert [x['preferred'] for x in r['declared_policy_demonstrations']]==['ORIGINAL','VARIANT','ORIGINAL']
    assert r['variant_receiver_judgment_sign']=='UNOBSERVED_NOT_NEUTRAL_OR_POSITIVE'
    assert not r['network_utility_identified'] and not r['learning_proven']
    assert h==pre

@pytest.mark.parametrize('key,bad',[('schema','fake'),('status','fake'),
 ('real_variant_full_fabric_replay',False),('experiment_kind','ONLINE_UPDATE'),
 ('conditional_direct_A_to_C',True),('v1e_hypothetical_A_to_C_direct_promoted',True),
 ('variant_off_on_forward_outcomes_equal',False),('reference_v1g1_file_sha256','0'*64),
 ('reference_v1d_file_sha256','a'*64),('native_scored_receiver_judgments',1),
 ('native_updates_applied',1),('native_learning_proven',True),('network_utility_identified',True)])
def test_false_identity_or_learning_rejected(key,bad):
    h=fixture();h[key]=bad
    with pytest.raises(InterventionError):run(h)

@pytest.mark.parametrize('key,bad',[('sender','C'),('instruction_index',3),
 ('original_instruction',['CMP',2]),('variant_instruction',['CMP',1]),
 ('original_nodes_unchanged',False),('static_fabric_shared_immutable',False),
 ('external_events_preserved',False)])
def test_forged_intervention_rejected(key,bad):
    h=fixture();h['intervention'][key]=bad
    with pytest.raises(InterventionError):run(h)

@pytest.mark.parametrize('family,arm,key,bad',[('original','off','batches',7),
 ('original','on','occurrences',3),('original','off','terminal',0),
 ('original','off','edges',{'A->C:7->0':4}),
 ('variant','off','batches',3),('variant','on','emissions',1),
 ('variant','off','link_grants',1),('variant','on','states_sha256','broken'),
 ('variant','off','terminal',-1),('variant','off','edges',{'A->B:7->0':0})])
def test_tampered_native_footprints_rejected(family,arm,key,bad):
    h=fixture();h[family][arm][key]=bad
    with pytest.raises(InterventionError):run(h)

@pytest.mark.parametrize('key,bad',[('native_feedback_assessments',{'original_on':2,'variant_on':1}),
 ('native_feedback_deliveries',{'original_on':4,'variant_on':2}),
 ('off_variant_minus_original',{'batches':-4}),
 ('on_variant_minus_original',{'batches':-4})])
def test_tampered_native_feedback_or_deltas_rejected(key,bad):
    h=fixture();h[key]=bad
    with pytest.raises(InterventionError):run(h)


def test_reject_wrong_byte_inputs():
    h=fixture();raw=json.dumps(h).encode()
    for gb,db in [(b'forgery',DB),(GB,b'forgery'),(b'',DB),(GB,b'')]:
        with pytest.raises(InterventionError):audit(h,raw,g_bytes=gb,d_bytes=db)


def test_synthetic_determinism():
    assert run(fixture())==run(fixture())


def setup_cli(tmp_path):
    root=tmp_path/'work';root.mkdir()
    docs=[];h=fixture()
    for i,n in enumerate(cli.NAMES):
        p=tmp_path/f'{n}.json'
        p.write_bytes(json.dumps(h).encode() if n=='v1h' else GB if n=='v1g1' else DB if n=='v1d' else f'other{i}'.encode())
        docs.append(p)
    out=tmp_path/'result.json'
    args=['--root',str(root)]
    for name,path in zip(cli.NAMES,docs):args.extend(['--'+name,str(path)])
    args.extend(['--out',str(out)])
    return docs,out,args


def patch_replay(monkeypatch, write=None):
    def stub(argv):
        target=Path(argv[argv.index('--out')+1])
        inputh=Path(argv[argv.index('--v1g1')-1]) if False else Path(argv[argv.index('--v1g1')+1])
        # The reference v1h is provided to the outer CLI, not the v1h native command.
        # Test one deterministic native report returned from the experimental double.
        body=json.dumps(fixture()).encode()
        if write:body=write(body)
        target.write_bytes(body)
        return 0
    monkeypatch.setattr(cli,'hmain',stub)


def test_cli_rejects_absent_inputs(tmp_path,capsys):
    _,out,args=setup_cli(tmp_path)
    (tmp_path/'v1h.json').unlink()
    assert cli.main(args)==2 and not out.exists()
    assert 'REJECTED' in capsys.readouterr().err


def test_cli_rejects_existing_output_without_mutation(tmp_path):
    _,out,args=setup_cli(tmp_path);out.write_text('KEEP')
    assert cli.main(args)==2 and out.read_text()=='KEEP'


def test_cli_rejects_symlink_and_hardlink_alias(tmp_path):
    docs,out,args=setup_cli(tmp_path)
    docs[2].unlink();docs[2].symlink_to(docs[1])
    assert cli.main(args)==2 and not out.exists()
    docs[2].unlink();docs[2].hardlink_to(docs[1])
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_missing_native_reexecution(tmp_path):
    _,out,args=setup_cli(tmp_path)
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_native_replay_mismatch(tmp_path,monkeypatch):
    _,out,args=setup_cli(tmp_path)
    def changed(raw):return raw+b'\n'
    patch_replay(monkeypatch,write=changed)
    assert cli.main(args)==2 and not out.exists()


def test_cli_valid_replay_and_new_output(tmp_path,monkeypatch):
    docs,out,args=setup_cli(tmp_path)
    h=fixture()
    docs[0].write_bytes(json.dumps(h).encode())
    patch_replay(monkeypatch)
    assert cli.main(args)==0 and out.exists()
    res=json.loads(out.read_text())
    assert res['status']==STATUS and res['reference_v1h_sha256']==sha(docs[0].read_bytes())
    assert res['native_v1h_recomputation_verified_in_this_run'] is True
    assert cli.main(args)==2 and res==json.loads(out.read_text())


def test_cli_no_native_replay_has_no_attestation(tmp_path,monkeypatch):
    docs,out,args=setup_cli(tmp_path)
    def fail(argv):return 2
    monkeypatch.setattr(cli,'hmain',fail)
    assert cli.main(args)==2 and not out.exists()
