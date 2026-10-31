"""Cumulative T5PQR + T5STU + T5VWX gated research experiment.

This is a research stress test of causal identifiability, NOT native credit.
It uses the user's exact archived T5MNO report and source-pinned ancestors.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from .causal_contract_v0 import CausalBoundary,need,canonical,digest,validate_source,observational_twins,intervention_pairs,research_feedback
from .feedback_process_v0 import issue,relay,receive
from research.spk_v5_t5mno import t5mno

SCHEMA='spk-v5-t5pqr-stu-vwx-cumulative-causal-shadow/research-v0'
STATUS='THREE_RESEARCH_GATES_CAUSAL_IDENTIFIABILITY_SIMULATED_INTERVENTION_SHADOW_FEEDBACK'
T5MNO_SHA='1eb6a4b43297cc8c111fb1811d00954ac119e2a9c604407785ec54059ee78706'

def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _worker(root,role,input_value,folder):
    inp=folder/f'{role}_input.json';out=folder/f'{role}_output.json'
    inp.write_bytes((json.dumps(input_value,sort_keys=True,indent=2)+'\n').encode())
    run=subprocess.run([sys.executable,'-m','research.spk_v5_t5pqr_stu_vwx.feedback_process_v0',
                        '--role',role,'--input',str(inp),'--output',str(out)],
                       cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    need(run.returncode==0,'WORKER_'+role+'_FAILED_'+run.stderr[-250:])
    return json.loads(out.read_bytes())

def run(root,strict_source_pins=True):
    root=Path(root)
    source=root/'research/spk_v5_t5pqr_stu_vwx/reference/t5mno-A-local-outcome.json'
    need(source.is_file() and not source.is_symlink(),'MISSING_T5MNO_REFERENCE')
    need(sha_file(source)==T5MNO_SHA,'T5MNO_SOURCE_PIN_DRIFT')
    old=json.loads(source.read_bytes())
    need(old['status']=='A_LOCAL_JUDGMENT_STRUCTURAL_NOT_SENSOR_AUTHENTICATED_OR_CAUSAL' and
         old['promotion_allowed'] is False and old['native_BV_credit']==0 and old['native_learning'] is False,
         'ANCESTOR_RESEARCH_ONLY_ASSERTIONS')
    need(old['A_local_structural_judgments']==180 and old['A_paired_research_outcomes']==72 and old['A_research_guard_candidates']==24,'ANCESTOR_COUNTS_DRIFT')
    rows=old['rows'];validate_source(rows)
    need(digest(rows)==old['rows_sha256'],'ANCESTOR_ROWS_SHA_DRIFT')
    # Independent re-execution of prior research-only logic, checked byte-for-byte.
    regenerated=t5mno.audit(root,full_source_pins=strict_source_pins)
    regen_bytes=(json.dumps(regenerated,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    need(hashlib.sha256(regen_bytes).hexdigest()==T5MNO_SHA,'ANCESTOR_REEXECUTION_DRIFT')
    need(canonical(regenerated)==canonical(old),'ANCESTOR_SEMANTIC_DRIFT')
    source_pins=t5mno.t5jkl.custody(root,strict_source_pins)
    need(source_pins==old['pins'] and source_pins['original_source_pins']==12,'SOURCE_CUSTODY_DRIFT')
    # T5PQR: two opposed counterfactual models are observationally equivalent.
    worlds=observational_twins(rows)
    need(worlds[0]['illustrative_effect']==1 and worlds[1]['illustrative_effect']==-1,'CAUSAL_WORLD_DIVERGENCE_MISSING')
    need(worlds[0]['observed_rows_sha256']==worlds[1]['observed_rows_sha256'],'OBSERVED_DATA_DIFFER')
    # T5STU: intentionally generated paired synthetic intervention, truth only inside simulator.
    trials=intervention_pairs(rows)
    need(trials['synthetic_effect_counts']=={'-1':8,'0':8,'2':8},'SIMULATED_EFFECT_DRIFT')
    need(trials['mean_synthetic_paired_effect_numerator']==8 and trials['mean_synthetic_paired_effect_denominator']==24,'MODEL_EFFECT_DRIFT')
    # T5VWX: send eligible shadow messages A -> relay B -> C via three separate processes.
    feedback=research_feedback(rows)
    need(len(feedback)==24,'SHADOW_COUNT_DRIFT')
    with tempfile.TemporaryDirectory(prefix='spk-t5cumulative-') as d:
        folder=Path(d)
        a=_worker(root,'A',feedback,folder)
        b=_worker(root,'B',a,folder)
        c=_worker(root,'C',b,folder)
    need(c['received']==24 and c['research_feedback_outcomes']=={'IMPROVED':8,'UNCHANGED':8,'WORSENED':8},'C_RECEIVER_COUNTS')
    need(c['C_native_credit_applied']==0 and c['C_native_learning_steps']==0 and c['promotion_allowed'] is False,'FALSE_NATIVE_CREDIT')
    # Fail-closed adversarial cases.
    attacks={}
    for label,modify,stage in [
        ('replay_duplicate',lambda x: x['entries'].append(copy.deepcopy(x['entries'][0])),'B'),
        ('payload_tamper',lambda x: x['entries'][0]['a_entry']['packet'].update(a_outcome='WORSENED' if x['entries'][0]['a_entry']['packet']['a_outcome']!='WORSENED' else 'IMPROVED'),'B'),
        ('relay_digest_tamper',lambda x: x['entries'][0].update(B_relay_sha256='0'*64),'B'),
        ('faked_native_credit',lambda x: x.update(native_BV_credit=1),'B'),
        ('faked_sensor',lambda x: x['entries'][0]['a_entry']['packet'].update(sensor_authenticated=True),'B'),
        ('faked_causality',lambda x: x['entries'][0]['a_entry']['packet'].update(causally_attributed_to_C=True),'B'),
    ]:
        altered=copy.deepcopy(b)
        modify(altered)
        rejected=False
        try:receive(altered)
        except CausalBoundary:rejected=True
        need(rejected,'ATTACK_NOT_REJECTED_'+label)
        attacks[label]='REJECTED'
    # Host reconstructs a FRESH valid A ledger, with a forged A outcome,
    # and B/C accept it: proves lack of authentic independent A authority.
    forged=copy.deepcopy(feedback)
    forged[0]['a_outcome']='WORSENED' if forged[0]['a_outcome']!='WORSENED' else 'IMPROVED'
    forged[0]['a_observation_sha256']='f'*64
    counterfeit=receive(relay(issue(forged)))
    need(counterfeit['received']==24 and counterfeit['research_feedback_sha256']!=c['research_feedback_sha256'],'HOST_REWRITE_NOT_ACCEPTED')
    need(sum(v=='REJECTED' for v in attacks.values())==6,'ATTACK_REJECTION_COUNT')
    need(t5mno.t5jkl.custody(root,strict_source_pins)==source_pins,'SOURCE_PINS_CHANGED')
    return {'schema':SCHEMA,'status':STATUS,'source_T5MNO_sha256':T5MNO_SHA,
            'T5MNO_reexecuted_byte_exact':True,'source_pins':source_pins,'original_source_pin_count':12,
            'T5PQR':{'cases':180,'two_opposed_causal_worlds_fit_all_observed_data':True,
                     'observed_outcome_vector_sha256':worlds[0]['observed_rows_sha256'],
                     'positive_world_potential_sha256':worlds[0]['unobserved_potential_outcome_sha256'],
                     'negative_world_potential_sha256':worlds[1]['unobserved_potential_outcome_sha256'],
                     'world_illustrative_effects':[1,-1],
                     'real_C_effect_identifiable_from_T5MNO':False},
            'T5STU':{'model_only_twin_trials':24,'simulated_arms':48,
                     'model_effect_counts':trials['synthetic_effect_counts'],
                     'simulated_paired_effect_numerator':trials['mean_synthetic_paired_effect_numerator'],
                     'simulated_paired_effect_denominator':trials['mean_synthetic_paired_effect_denominator'],
                     'trial_record_sha256':digest(trials['trials']),'native_C_interventions':0,
                     'authenticated_sensor_observations':0,'real_C_effect_identified':False},
            'T5VWX':{'research_A_feedback_messages':24,'B_relay_messages':24,'C_receiver_messages':c['received'],
                     'C_receiver_outcomes':c['research_feedback_outcomes'],
                     'three_process_separation':True,
                     'A_end_sha256':c['A_end_sha256'],'B_end_sha256':c['B_end_sha256'],
                     'C_feedback_sha256':c['research_feedback_sha256'],
                     'negative_attacks':attacks,'host_reconstructed_fresh_ledger_accepted':True,
                     'host_reconstructed_C_feedback_sha256':counterfeit['research_feedback_sha256'],
                     'C_native_credit_applied':0,'C_native_learning_steps':0},
            'new_original_BV_scheduler_calls':0,'new_original_PE_compute_calls':0,
            'C_native_authority_authenticated':False,'A_sensor_authenticated':False,
            'real_C_causal_attribution_proven':False,'native_BV_credit':0,'native_learning':False,
            'promotion_allowed':False,
            'limits':['Opposite causal effects generate the same 180 observed T5MNO rows: observational non-identifiability',
                      'The paired interventions use a host-authored synthetic causal plant, not real C actions or A sensor readings',
                      'The host selects candidate cases using archived cross-plane metadata and may replace A observations',
                      'A, B and C are separate host-controlled Python processes, not independent authenticated neuronal authorities',
                      'Host-forged fresh A ledgers remain acceptable to C; research-only messages MUST NOT update native state']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    try:
        need(not args.out.exists(),'OUTPUT_EXISTS')
        r=run(args.root,True)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes((json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
        print('T5PQR/STU/VWX',STATUS)
        print('Causal opposite models 2 | simulated matched pairs 24 | shadow feedback 24 | rejected attacks 6 | host forgery ACCEPTED | NATIVE BV CREDIT 0')
        print('SHA256',sha_file(args.out))
    except (CausalBoundary,ValueError,AssertionError,TypeError,KeyError,OSError,ImportError,subprocess.TimeoutExpired) as ex:
        raise SystemExit('T5 CUMULATIVE FAIL CLOSED: '+str(ex))
if __name__=='__main__':main()
