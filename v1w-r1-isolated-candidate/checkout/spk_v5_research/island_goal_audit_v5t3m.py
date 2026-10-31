"""V5-T3m: posthoc C-credit / independent PHOTO-goal discordance on public UCI.

PHOTO occupancy is outside A/C/learning; its use for reporting is explicitly
posthoc. No cryptographic escrow, untouched holdout or authoritative sensor
identity is established by this module. The existing T3h A1b C instructions
are used to calculate the signed C verdict for every selected program.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from spk_v5_research.island_online_credit_v5t3i import OnlinePolicy,packet_for,digest
from spk_v5_research.island_c_owned_credit_v5t3h import Measurement
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci
from spk_v5_research.island_real_transition_v5t3d import ALLOWED_GAPS_SECONDS

SCHEMA='spk-v5-t3m-public-proxy-credit-vs-photo-goal/research-v0'
EXPECTED_SHA={
 'datatraining.txt':'b2c4d0ce2b9e4e453c476f7125ef31aeec2d1f5c7f5572d0e80de3df6521ab56',
 'datatest.txt':'1b92c7c1b2838963464fa891a610cf3c5db4becb7189189b29b330107a584c7f',
 'datatest2.txt':'d026d1bd5aeccd4aff4f3b3710d48e40613bd5fc370db7e61bbdcaa50d985095',
}

def one_public(path:Path, *, max_pairs=1200):
    if type(max_pairs) is not int or not 100<=max_pairs<=1500:
        raise ValueError('invalid fixed public sample budget')
    if not isinstance(path,Path) or path.name not in EXPECTED_SHA:
        raise ValueError('invalid public UCI source')
    rows,sha=read_authentic_uci(path,expected_filename=path.name)
    if sha!=EXPECTED_SHA[path.name]:
        raise ValueError('unexpected original source SHA; test fixture substitution rejected')
    ctl=OnlinePolicy(seed=414,exploration=.12)
    counts=Counter(); by_day=defaultdict(Counter); by_context=defaultdict(Counter)
    trace=[]
    for idx in range(1,min(len(rows),max_pairs+1)):
        before,now=rows[idx-1],rows[idx]
        gap=(datetime.strptime(now.stamp,'%Y-%m-%d %H:%M:%S')-
             datetime.strptime(before.stamp,'%Y-%m-%d %H:%M:%S')).total_seconds()
        if gap not in ALLOWED_GAPS_SECONDS:
            counts['rejected_gap']+=1
            continue
        for pid,p in tuple(ctl.pending.items()):
            if p.arrival_step<=idx:ctl.settle(pid,idx)
        arm=ctl.decide(f'{path.name}:{idx}',before.light,now.light,idx)
        m=Measurement(before.stamp,now.stamp,before.light,now.light,now.co2)
        packet=packet_for(f'{path.name}:{idx}',arm,m,idx)
        ctl.register(packet)
        if packet.witness['status']!='C_authored_credit_delivered':
            raise AssertionError('expected intact original-UCI research A1b feedback')
        # The outside PHOTO label is consulted only after A's actual decision and
        # C-authored credit have been committed. NEVER feed it to the registry.
        predicted=bool(packet.witness['A_light_decision'])
        cbit=now.co2>=600
        photo=now.occupied
        received=packet.witness['A_consumed_credit']
        assert received==(1 if predicted==cbit else -1)
        wrong_cbit=(cbit!=photo)
        values={'episodes':1,'proxy_mismatch_photo':int(wrong_cbit),
          'local_correct':int(predicted==cbit),'photo_correct':int(predicted==photo),
          'reward_positive':int(received==1),'reward_negative':int(received==-1),
          'misleading_positive':int(received==1 and predicted!=photo),
          'misleading_negative':int(received==-1 and predicted==photo),
          'goal_positive':int(photo),'proxy_positive':int(cbit),
          'fixed_current_photo_correct':int((now.light>=200)==photo),
          'fixed_persist_photo_correct':int(((before.light>=200) and (now.light>=200))==photo)}
        for counter in (counts,by_day[now.stamp[:10]],by_context[f'{int(before.light>=200)}{int(now.light>=200)}']):
            counter.update(values)
        # Source-level trace binds the decisions and C verdicts, but NOT photo labels.
        trace.append((idx,arm,packet.packet_id,received,predicted))
    for pid,p in tuple(ctl.pending.items()):ctl.settle(pid,max(max_pairs+1,p.arrival_step))
    audit=ctl.audit()
    assert audit['updates']==counts['episodes'] and audit['pending']==0
    assert counts['proxy_mismatch_photo']==counts['misleading_positive']+counts['misleading_negative']
    return {'schema':SCHEMA,'name':path.name,'source_sha256':sha,
      'source_rows':len(rows),'consecutive_public_prefix_budget':max_pairs,
      'counts':dict(sorted(counts.items())),
      'by_day':{k:dict(sorted(v.items())) for k,v in sorted(by_day.items())},
      'by_A_light_context':{k:dict(sorted(v.items())) for k,v in sorted(by_context.items())},
      'A1b_C_authored_credit_admitted':audit['updates'],
      'C_only_policy_head_sha256':audit['head_sha256'],
      'C_only_policy_weights_sha256':digest(audit['weights']),
      'A_C_transcript_without_photo_sha256':digest(trace),
      'goal_labels_consulted_posthoc':True,'photo_label_in_policy':False,
      'native_BV_source_authentication':False,'blind':False}


def public_audit(directory:Path,max_pairs=1200):
    if not isinstance(directory,Path) or directory.is_symlink() or not directory.is_dir():
        raise ValueError('invalid public input directory')
    files=[one_public(directory/name,max_pairs=max_pairs) for name in EXPECTED_SHA]
    total=Counter()
    for file in files:total.update(file['counts'])
    return {'schema':SCHEMA,'status':'PUBLIC_GOAL_PROXY_DISCORDANCE_POSTHOC',
       'files':files,'pooled':dict(sorted(total.items())),
       'posthoc_not_blind':True,'photo_labels_never_in_learner':True}
