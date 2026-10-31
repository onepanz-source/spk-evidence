"""SPK T6JKL/MNO/PQR: two recipient simulated PE and bounded asynchronous feedback.

Host-authored, research-only graph. Runs frozen _compute_local for C, B,
A and D, A/D reverse, B reverse and C reverse. A/D goals change with
synthetic plant phase. No full frozen BV, native learning or attestation.
"""
from __future__ import annotations
from dataclasses import dataclass
import copy
import random
from research.spk_v5_t6abc_def_ghi.loop_v0 import (LoopBoundary, pe,emit_single,digest,require)

GOALS_PHASES=({0:5,1:11},{0:11,1:5})
OTHER={5:11,11:5}
CHOICES=(11,12)
RECEIVERS=('A','D')
OUTCOMES=('IMPROVED','WORSENED')
# A and D are separate logical receiver PE contexts, not trusted sensor devices.
FEEDBACK_CHANNEL={('A','IMPROVED'):41,('A','WORSENED'):42,
                  ('D','IMPROVED'):44,('D','WORSENED'):45}

class MultiPolicy:
    def __init__(self,learn:bool=True,budget:int=8):
        require(type(learn) is bool and type(budget) is int and 0<=budget<=32,'POLICY_ARGS')
        self.learn=learn
        self.table={0:12,1:11}
        self.versions={0:0,1:0}
        self.budget={0:budget,1:budget}
        self.pending={}
        self.next_id=0
        self.completed=set()
        self.updates=0
        self.judged=0
        self.conflicts=0
        self.stale=0
        self.accepted_votes=0
        self.rejections={}
        self.transcripts=[]

    def choose(self,cue,issue_tick):
        require(type(cue) is int and cue in (0,1),'BAD_CUE')
        require(type(issue_tick) is int and 0<=issue_tick<9000,'ISSUE_TICK')
        did=self.next_id;self.next_id+=1
        selected=self.table[cue]
        pe_out=emit_single('C',0,0,selected,issue_tick)
        d={'id':did,'cue':cue,'choice':selected,'version':self.versions[cue],
           'issue_tick':issue_tick,'C_emit':list(pe_out['emissions'])}
        d['decision_sha256']=digest(d)
        self.pending[did]={'decision':d,'votes':{}}
        return copy.deepcopy(d)

    def submit(self,env,arrival_tick):
        """Atomic validation and reception. Vote custody is C-local, untrusted host.

        A duplicate, wrong PE channel, expired or obsolete version never
        updates C's policy. No source-authentication claim is made.
        """
        require(type(arrival_tick) is int and 0<=arrival_tick<10000,'ARRIVAL_TICK')
        require(type(env) is dict and set(env)=={'vote','vote_sha256','relay_channel','relay_sha256'},'ENVELOPE_SCHEMA')
        v=env['vote']
        require(type(v) is dict and set(v)=={'id','cue','version','issue_tick','receiver','decision_sha256',
            'observed_raw','goal_raw','outcome','feedback_channel'},'VOTE_SCHEMA')
        require(type(v['id']) is int,'BAD_ID')
        did=v['id']
        require(did not in self.completed and did in self.pending,'NO_PENDING_OR_REPLAY')
        entry=self.pending[did];d=entry['decision']
        require(type(v['cue']) is int and v['cue']==d['cue'] and type(v['version']) is int and
                v['version']==d['version'] and type(v['issue_tick']) is int and v['issue_tick']==d['issue_tick'] and
                v['decision_sha256']==d['decision_sha256'],'DECISION_BINDING')
        require(d['version']==self.versions[d['cue']],'OBSOLETE_POLICY_VERSION')
        require(d['issue_tick']+3<=arrival_tick<=d['issue_tick']+7,'EXPIRED_OR_PREMATURE')
        receiver=v['receiver'];require(type(receiver) is str and receiver in RECEIVERS,'BAD_RECEIVER')
        require(receiver not in entry['votes'],'DUPLICATE_RECEIVER_VOTE')
        require(type(v['observed_raw']) is int and v['observed_raw'] in (5,11),'BAD_MEASUREMENT')
        require(type(v['goal_raw']) is int and v['goal_raw'] in (5,11),'BAD_GOAL')
        require(type(v['outcome']) is str and v['outcome'] in OUTCOMES,'BAD_OUTCOME')
        ch=FEEDBACK_CHANNEL[(receiver,v['outcome'])]
        require(v['feedback_channel']==ch,'CHANNEL_OUTCOME_MISMATCH')
        require(env['vote_sha256']==digest(v),'VOTE_DIGEST_DRIFT')
        require(type(env['relay_channel']) is int and env['relay_channel']==ch+10,'RELAY_CHANNEL_DRIFT')
        require(env['relay_sha256']==digest({'vote_sha256':env['vote_sha256'],'relay_channel':env['relay_channel']}),'RELAY_DIGEST_DRIFT')
        arrival=emit_single('C-return-'+receiver,env['relay_channel'],env['relay_channel'],ch+20,arrival_tick)
        require(arrival['emissions']==(ch+20,),'C_RETURN_PE_NO_EMISSION')
        entry['votes'][receiver]=copy.deepcopy(v)
        self.accepted_votes+=1
        if len(entry['votes'])!=2:
            return 'RECEIVED'
        require(set(entry['votes'])==set(RECEIVERS),'QUORUM_DUPLICITY')
        a,b=(entry['votes'][r]['outcome'] for r in RECEIVERS)
        self.judged+=1
        if a!=b:self.conflicts+=1
        result='HELD'
        if a==b=='WORSENED' and self.learn and self.budget[d['cue']]>0:
            cue=d['cue'];self.table[cue]=11 if self.table[cue]==12 else 12
            self.versions[cue]+=1;self.budget[cue]-=1;self.updates+=1
            result='UPDATED'
        elif a!=b:result='CONFLICT_HELD'
        elif a==b=='IMPROVED':result='IMPROVED_HELD'
        self.completed.add(did);del self.pending[did]
        self.transcripts.append({'id':did,'cue':d['cue'],'votes':[a,b],'result':result,
            'policy_version_after':self.versions[d['cue']]})
        return result

    def close_batch(self):
        unfinished=len(self.pending)
        self.completed.update(self.pending)
        self.pending.clear()
        return unfinished


def objective(phase,cue,receiver,conflict_contexts=()):
    require(type(phase) is int and phase>=0 and type(cue) is int and cue in (0,1),'OBJECTIVE_SCOPE')
    require(receiver in RECEIVERS,'RECEIVER_SCOPE')
    value=GOALS_PHASES[phase%2][cue]
    return OTHER[value] if receiver=='D' and cue in conflict_contexts else value


def make_votes(decision,phase,conflict_contexts=()):
    """Two receiver measurements computed via frozen PE, not copied outcomes."""
    cue=decision['cue'];choice=decision['choice'];tick=decision['issue_tick']
    input_ch=1 if choice==11 else 2
    b=emit_single('B-forward',input_ch,input_ch,31 if choice==11 else 32,tick+1)
    require(b['emissions']==(31 if choice==11 else 32,),'B_FORWARD_PE')
    input_to_receiver=(3,) if choice==11 else (4,)
    packets=[]
    for receiver in RECEIVERS:
        actual=pe(receiver,(('ACC',(5,3)),('ACC',(11,4))),tick+2,input_to_receiver)
        goal=objective(phase,cue,receiver,conflict_contexts)
        outcome='IMPROVED' if actual['raw']==goal else 'WORSENED'
        ch=FEEDBACK_CHANNEL[(receiver,outcome)]
        emitted=emit_single(receiver+'-return',50,50,ch,tick+3)
        relay=emit_single('B-return-'+receiver,ch,ch,ch+10,tick+4)
        require(emitted['emissions']==(ch,) and relay['emissions']==(ch+10,),'PE_RETURN_PATH')
        vote={'id':decision['id'],'cue':cue,'version':decision['version'],
              'issue_tick':tick,'receiver':receiver,'decision_sha256':decision['decision_sha256'],
              'observed_raw':actual['raw'],'goal_raw':goal,'outcome':outcome,'feedback_channel':ch}
        vsha=digest(vote);envelope={'vote':vote,'vote_sha256':vsha,'relay_channel':ch+10,
                      'relay_sha256':digest({'vote_sha256':vsha,'relay_channel':ch+10})}
        packets.append(envelope)
    return packets


def reseal(vote):
    """ATTACKER FACILITY: the host can reconstruct a coherent forged receipt."""
    ch=FEEDBACK_CHANNEL[(vote['receiver'],vote['outcome'])]
    vote=copy.deepcopy(vote);vote['feedback_channel']=ch
    sha=digest(vote)
    return {'vote':vote,'vote_sha256':sha,'relay_channel':ch+10,
            'relay_sha256':digest({'vote_sha256':sha,'relay_channel':ch+10})}


def scenario(*,learn=True,phases=4,conflict_contexts=(),mode='ordered',seed=7,
             drop_mod=0,budget=8):
    """Matched model-internal experiment: same goals/episodes/schedule for control.

    Phases 0/2 and 1/3 have opposing A/D goals. Each phase has 24 choices;
    each 4-decision batch issues two per context before delivering any vote.
    """
    require(type(phases) is int and 1<=phases<=8,'BAD_PHASE_COUNT')
    require(type(seed) is int and 0<=seed<2**32,'BAD_SEED')
    require(mode in ('ordered','reverse','jitter'),'BAD_DELIVERY_MODE')
    require(type(drop_mod) is int and 0<=drop_mod<=20,'BAD_DROP_RATE')
    require(type(conflict_contexts) is tuple and all(type(c) is int and c in (0,1) for c in conflict_contexts),'BAD_CONFLICT_SCOPE')
    policy=MultiPolicy(learn,budget)
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
    return {'scenario':{'learn':learn,'phases':phases,'conflict_contexts':list(conflict_contexts),
            'mode':mode,'seed':seed,'drop_mod':drop_mod,'budget':budget},
            'episodes':len(rows),'A_successes':sum(r['A_success'] for r in rows),
            'D_successes':sum(r['D_success'] for r in rows),
            'joint_successes':sum(r['joint_success'] for r in rows),
            'updates':policy.updates,'judgments':policy.judged,'conflicts':policy.conflicts,
            'stale_rejections':stale_rejects,'expiry_rejections':expiry_rejects,
            'dropped':dropped,'abandoned':abandoned,'delivered':delivered,
            'versions':dict(policy.versions),'final_policy':dict(policy.table),
            'rows_sha256':digest(rows),'rows':rows,'transcripts_sha256':digest(policy.transcripts)}
