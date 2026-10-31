"""Experimental owned C state used by the multi-receiver PE fragment.

Keeps the old T6 model-only receiver evaluation unchanged; replaces the
external MultiPolicy state with SQLite transactional owned P state.
This is not the native SPK architecture memory state or native BV scheduler.
"""
from __future__ import annotations
import random
import tempfile
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import require,LoopBoundary,digest
from research.spk_v5_t6jkl_mno_pqr.async_multi_v0 import make_votes,scenario
from .owned_state_v0 import OwnedCState

def scenario_owned(*,learn=True,phases=4,conflict_contexts=(),mode='ordered',seed=7,
             drop_mod=0,budget=8,reopen_each_batch=False):
    """Matched model-internal experiment: same goals/episodes/schedule for control.

    Phases 0/2 and 1/3 have opposing A/D goals. Each phase has 24 choices;
    each 4-decision batch issues two per context before delivering any vote.
    """
    require(type(phases) is int and 1<=phases<=8,'BAD_PHASE_COUNT')
    require(type(seed) is int and 0<=seed<2**32,'BAD_SEED')
    require(mode in ('ordered','reverse','jitter'),'BAD_DELIVERY_MODE')
    require(type(drop_mod) is int and 0<=drop_mod<=20,'BAD_DROP_RATE')
    require(type(conflict_contexts) is tuple and all(type(c) is int and c in (0,1) for c in conflict_contexts),'BAD_CONFLICT_SCOPE')
    temporary=tempfile.TemporaryDirectory(prefix='spk-t6-state-')
    policy=OwnedCState(Path(temporary.name)/'owner-C.sqlite',learn=learn,budget=budget)
    rng=random.Random(seed)
    rows=[];delivered={'RECEIVED':0,'UPDATED':0,'HELD':0,'CONFLICT_HELD':0,'IMPROVED_HELD':0}
    stale_rejects=0;expiry_rejects=0;dropped=0;abandoned=0
    for phase in range(phases):
        for group in range(6):
            tick=(phase*6+group)*10
            upcoming=[];events=[]
            for pos,cue in enumerate((0,1,0,1)):
                dec=policy.choose(cue,tick)
                envelopes=make_votes(dec,phase,conflict_contexts)
                success=sum(v['vote']['outcome']=='IMPROVED' for v in envelopes)
                rows.append({'phase':phase,'group':group,'id':dec['id'],'cue':cue,'choice':dec['choice'],
                    'A_goal':envelopes[0]['vote']['goal_raw'],'D_goal':envelopes[1]['vote']['goal_raw'],
                    'joint_success':int(success==2),'A_success':int(envelopes[0]['vote']['outcome']=='IMPROVED'),
                    'D_success':int(envelopes[1]['vote']['outcome']=='IMPROVED')})
                upcoming.append(dec)
                for j,env in enumerate(envelopes):
                    if drop_mod and (dec['id']*2+j+1)%drop_mod==0:
                        dropped+=1;continue
                    if mode=='ordered':arrival=tick+5+j
                    elif mode=='reverse':arrival=tick+6-j
                    else:arrival=tick+4+rng.randrange(0,4)
                    events.append((arrival,dec['id'],j,env))
            if mode=='reverse':events.sort(key=lambda a:(a[0],-a[1],a[2]))
            elif mode=='jitter':events.sort(key=lambda a:(a[0],(-1 if a[2] else 1)*a[1],a[2]))
            else:events.sort(key=lambda a:(a[0],a[1],a[2]))
            for arrival,did,_,env in events:
                try:
                    code=policy.submit(env,arrival);delivered[code]+=1
                except LoopBoundary as exc:
                    if str(exc)=='OBSOLETE_POLICY_VERSION':stale_rejects+=1
                    elif str(exc)=='EXPIRED_OR_PREMATURE':expiry_rejects+=1
                    else:raise
            abandoned+=policy.close_batch()
            if reopen_each_batch:policy.reopen()
    audit=policy.audit()
    result={'audit':audit,'scenario':{'learn':learn,'phases':phases,'conflict_contexts':list(conflict_contexts),
            'mode':mode,'seed':seed,'drop_mod':drop_mod,'budget':budget},
            'episodes':len(rows),'A_successes':sum(r['A_success'] for r in rows),
            'D_successes':sum(r['D_success'] for r in rows),
            'joint_successes':sum(r['joint_success'] for r in rows),
            'updates':policy.updates,'judgments':policy.judged,'conflicts':policy.conflicts,
            'stale_rejections':stale_rejects,'expiry_rejections':expiry_rejects,
            'dropped':dropped,'abandoned':abandoned,'delivered':delivered,
            'versions':dict(policy.versions),'final_policy':dict(policy.table),
            'rows_sha256':digest(rows),'rows':rows,'transcripts_sha256':digest(policy.transcripts)}

    policy.close()
    temporary.cleanup()
    return result
