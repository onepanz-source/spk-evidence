"""Combined SPK V5-T3i/j/k research gate: longitudinal C-owned feedback,
placebo/fixed negative controls, signed ledger and public UCI diagnostics.
No native learning and no independent new-data generalization claim.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from spk_v5_research.island_online_credit_v5t3i import OnlinePolicy,packet_for,digest
from spk_v5_research.island_regime_replay_v5t3j import trial,actual_correct,REGIMES
from spk_v5_research.island_c_owned_credit_v5t3h import ARMS,Measurement
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci

SCHEMA='spk-v5-t3ijk-bundled-closed-loop/research-v0'
SEEDS=(11,29,47,83)
PATTERNS=('shift','stationary_current','uninformative_coin','rapid_switch')


def public_uci(data_dir:Path,limit=1200):
    """Public, previously inspected UCI. C proxy via CO2, photo only post-scoring."""
    if type(limit) is not int or not 200<=limit<=5000:
        raise ValueError('UCI audit budget invalid')
    results={}
    for name in ('datatraining.txt','datatest.txt','datatest2.txt'):
        rows,raw_sha=read_authentic_uci(data_dir/name,expected_filename=name)
        ctl=OnlinePolicy(seed=414,exploration=.12)
        scored=Counter();by_arm=Counter();source_status=Counter()
        observed=0
        for i in range(1,min(len(rows),limit+1)):
            before,now=rows[i-1],rows[i]
            if ( __import__('datetime').datetime.strptime(now.stamp,'%Y-%m-%d %H:%M:%S')-
               __import__('datetime').datetime.strptime(before.stamp,'%Y-%m-%d %H:%M:%S')).total_seconds() not in (59,60,61):
                scored['excluded_bad_gap']+=1
                continue
            # real A1b usage: prior credits settle only from earlier source episodes.
            for pid,p in tuple(ctl.pending.items()):
                if p.arrival_step<=i:ctl.settle(pid,i)
            arm=ctl.decide(f'{name}:{i}',before.light,now.light,i)
            # C sensor has independent CO2 channel; no UCI photo label used for policy.
            measurement=Measurement(before.stamp,now.stamp,before.light,now.light,now.co2)
            packet=packet_for(f'{name}:{i}',arm,measurement,i)
            ctl.register(packet)
            if packet.witness['status']!='C_authored_credit_delivered':
                raise AssertionError('unexpected C-owned public sensor missing')
            source_status[packet.witness['status']]+=1
            predicted=bool(packet.witness['A_light_decision'])
            c_truth=now.co2>=600
            # Photo occupancy target is POST-HOC audit only, never an update channel.
            scored['C_proxy_success']+=predicted==c_truth
            scored['photo_label_success']+=predicted==now.occupied
            scored['static_current_C_success']+=(now.light>=200)==c_truth
            scored['static_current_photo_success']+=(now.light>=200)==now.occupied
            scored['static_persist_C_success']+=(before.light>=200 and now.light>=200)==c_truth
            scored['static_persist_photo_success']+=(before.light>=200 and now.light>=200)==now.occupied
            scored['photo_positive']+=now.occupied
            scored['C_proxy_positive']+=c_truth
            by_arm[arm]+=1;observed+=1
        for pid,p in tuple(ctl.pending.items()):ctl.settle(pid,max(limit+1,p.arrival_step))
        audit=ctl.audit()
        if audit['updates']!=observed:raise AssertionError('unaccounted public C credit')
        results[name]={'raw_original_sha256':raw_sha,'source_rows':len(rows),
           'consecutive_public_prefix_budget':limit,'admitted':observed,
           'research_registry_credit_updates':audit['updates'],
           'learned_state_sha256':digest(audit['weights']),
           'C_proxy_match_count':scored['C_proxy_success'],
           'PHOTO_occ_match_POSTHOC':scored['photo_label_success'],
           'fixed_current_C_proxy_match':scored['static_current_C_success'],
           'fixed_current_photo_match':scored['static_current_photo_success'],
           'fixed_persist_C_proxy_match':scored['static_persist_C_success'],
           'fixed_persist_photo_match':scored['static_persist_photo_success'],
           'photo_occupied':scored['photo_positive'],'C_proxy_positives':scored['C_proxy_positive'],
           'selected_arm_counts':dict(sorted(by_arm.items())),
           'excluded_nonadjacent_gaps':scored['excluded_bad_gap'],
           'C_sensor_precomputed_by_host':True,'independent_blind':False}
    return results


def report(uci_dir:Path|None=None):
    shift=[];adversarial=[];N=0
    for st in (False,True):
        for seed in SEEDS:
            d=trial(seed,400,st)
            N+=d['summaries']['learned']['total']
            shift.append({'seed':seed,'stress':st,'accuracy':{
                k:v['accuracy'] for k,v in d['summaries'].items() if k!='regimes'},
                'by_regime':d['summaries']['regimes'],
                'C_research_source_runs':d['source_executions'],
                'C_statuses':d['observed_C_origin_statuses'],
                'registry_audit':{k:v for k,v in d['policy_registry'].items() if k!='weights' and k!='updates_by_arm_context'},
                'run_transcript_sha256':d['C_paid_research_A1b_replay_sha256']})
    # Falsification cases use the same bandit parameters, with prior registered controls.
    for pattern in ('stationary_current','uninformative_coin','rapid_switch'):
        for seed in (29,47):
            d=trial(seed,400,True,pattern=pattern)
            N+=d['summaries']['learned']['total']
            adversarial.append({'pattern':pattern,'seed':seed,'accuracies':{
                k:v['accuracy'] for k,v in d['summaries'].items() if k!='regimes'},
                'C_delivered_updates':d['policy_registry']['updates'],
                'transcript_sha256':d['C_paid_research_A1b_replay_sha256']})
    shifted_mean=lambda k:round(sum(s['accuracy'][k] for s in shift)/len(shift),6)
    delta_vs_best=round(shifted_mean('learned')-max(shifted_mean(a) for a in ARMS),6)
    delta_vs_placebo=round(shifted_mean('learned')-shifted_mean('placebo'),6)
    if not (delta_vs_best>0 and delta_vs_placebo>0):
        # Negative result remains a report, not a falsified PASS.
        status='NO_ENGINEERED_SHIFT_BENEFIT'
    else:status='ENGINEERED_SHIFT_RESEARCH_FEEDBACK_BENEFIT_NOT_NATIVE'
    out={'schema':SCHEMA,'status':status,'synthetic_cases':N,
         'independent_seeds_listed_but_not_physical_independence':list(SEEDS),
         'shift':{'cases':len(shift)*1200,'scenarios':shift,'pooled_accuracy_unweighted_seed_mean':{
             k:shifted_mean(k) for k in ('learned','placebo','random','current','persist','silent')},
             'delta_learned_vs_best_fixed':delta_vs_best,
             'delta_learned_vs_placebo':delta_vs_placebo},
         'falsification_cases':adversarial,
         'public_UCI_photo_label_POSTHOC_ONLY':public_uci(uci_dir) if uci_dir else None,
         'verification':'each credited update replayed through T3h execute() + independent hash chain',
         'scope_exclusions':[
           'research host registry selects next A1b program; no native neural program update',
           'C computes +1/-1 using A1b instructions, but C CO2 bit is host-thresholded and unsignatured',
           'phase shifts and C target built by test harness; no independent environment',
           'modeled inter-episode delay is NOT native transport latency; no PE congestion integration',
           'fixed arms and placebo are engineered comparators, not preregistered unseen trials',
           'public UCI previously inspected; historical photo labels used posthoc for audit only',
           'policy fitness to C CO2 threshold may differ from photo occupancy labels',
           'no native learning, no blind validation, no guaranteed cross-context gain']}
    return out
