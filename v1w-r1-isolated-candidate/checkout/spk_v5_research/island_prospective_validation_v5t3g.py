"""V5-T3g prospective source-commit and late-label audit, RESEARCH ONLY.

No independent escrow, no blinding guarantee, no native BV reward or learning.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from collections import defaultdict
from math import comb, isfinite
import re

from spk_v5_research.island_successor_competition_v5t3e import native_boolean_truth_table, metrics

SCHEMA='spk-v5-t3g-prospective-public-audit/research-v0'
COMMIT_SCHEMA='spk-v5-t3g-unlabelled-input-commit/v0'
STATUS_PASS='PROSPECTIVE_SCREEN_SIGNAL_ONLY_NO_CAUSAL_RL'
STATUS_FAIL='PROSPECTIVE_SCREEN_NO_SUPPORT'
STATUS_INSUFFICIENT='PROSPECTIVE_SCREEN_INSUFFICIENT_DAY_BLOCKS'
MIN_DAY_BLOCKS=10
MIN_PAIRS_PER_DAY=60
MIN_DISCORDANT_DAYS=8
MIN_MEAN_IMPROVEMENT=0.005
MAX_FN_RATE_UPLIFT=0.01
MAX_SIGN_P=0.05
TIME_START=datetime(2026,10,22,tzinfo=timezone.utc)
STAMP=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
SOURCE_ID=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{3,63}$')
KNOWN_UCI={
    '1b92c7c1b2838963464fa891a610cf3c5db4becb7189189b29b330107a584c7f',
    'd026d1bd5aeccd4aff4f3b3710d48e40613bd5fc370db7e61bbdcaa50d985095',
    'b2c4d0ce2b9e4e453c476f7125ef31aeec2d1f5c7f5572d0e80de3df6521ab56',
}

def source_bytes(path:Path)->tuple[bytes,str]:
    p=Path(path)
    if p.is_symlink() or not p.is_file():
        raise ValueError('unsafe or missing source file')
    b=p.read_bytes()
    if not b or len(b)>64_000_000 or b'\x00' in b:
        raise ValueError('missing, oversized or binary source')
    return b,sha256(b).hexdigest()


def stamp_parse(value:str)->datetime:
    if not STAMP.fullmatch(value):
        raise ValueError('timestamp must use exact UTC YYYY-MM-DDTHH:MM:SSZ')
    d=datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    if d < TIME_START:
        raise ValueError('prospective source timestamp precedes protocol cutoff')
    return d


def read_features(path:Path)->tuple[tuple[tuple[str,datetime,float],...],str]:
    import io
    raw,digest=source_bytes(path)
    if digest in KNOWN_UCI:
        raise ValueError('publicly inspected UCI source is not prospective')
    try:
        f=io.StringIO(raw.decode('utf-8',errors='strict'),newline='')
        reader=csv.reader(f,strict=True)
        if next(reader,None)!=['timestamp_utc','light_lux']:
            raise ValueError('feature header must be timestamp_utc,light_lux ONLY')
        items=[]
        for cells in reader:
            if len(cells)!=2:
                raise ValueError('invalid feature row or concealed columns')
            stamp,bright=cells
            d=stamp_parse(stamp)
            x=float(bright)
            if not isfinite(x) or not (0<=x<=200_000):
                raise ValueError('invalid physical light measurement')
            if items and d<=items[-1][1]:
                raise ValueError('source measurements not strictly time ordered')
            items.append((stamp,d,x))
        if len(items)<(MIN_DAY_BLOCKS*(MIN_PAIRS_PER_DAY+1)):
            raise ValueError('insufficient prospective sensor rows')
        return tuple(items),digest
    except (UnicodeError,csv.Error,OverflowError) as err:
        raise ValueError('invalid feature encoding/CSV') from err


def read_labels(path:Path)->tuple[dict[str,bool],str]:
    import io
    raw,digest=source_bytes(path)
    try:
        reader=csv.reader(io.StringIO(raw.decode('utf-8',errors='strict'),newline=''),strict=True)
        if next(reader,None)!=['timestamp_utc','occupied']:
            raise ValueError('label header must be timestamp_utc,occupied ONLY')
        labels={};prev=None
        for cells in reader:
            if len(cells)!=2 or cells[1] not in ('0','1'):
                raise ValueError('invalid occupancy label row')
            d=stamp_parse(cells[0])
            if prev is not None and d<=prev:
                raise ValueError('labels duplicated or nonchronological')
            labels[cells[0]]=(cells[1]=='1')
            prev=d
        return labels,digest
    except (UnicodeError,csv.Error,OverflowError) as err:
        raise ValueError('invalid label encoding/CSV') from err


def admitted_pairs(items):
    perday=defaultdict(list)
    for before,after in zip(items,items[1:]):
        if (after[1]-before[1]).total_seconds() not in (59,60,61):
            continue
        perday[after[1].date().isoformat()].append((before,after))
    return dict(sorted(perday.items()))


def precommit(rows,digest,source_id,protocol_sha):
    if not SOURCE_ID.fullmatch(source_id):
        raise ValueError('source identifier must be 4-64 safe chars')
    days=admitted_pairs(rows)
    qualified=[day for day,v in days.items() if len(v)>=MIN_PAIRS_PER_DAY]
    if len(qualified)<MIN_DAY_BLOCKS:
        raise ValueError('requires at least ten calendar days with 60 real adjacent pairs each')
    return {'schema':COMMIT_SCHEMA,'source_id_operator_asserted':source_id,
        'unlabelled_source_sha256':digest,'rows':len(rows),
        'first':rows[0][0],'last':rows[-1][0],
        'eligible_pairs':sum(map(len,days.values())),
        'eligible_days_with_60_pairs':len(qualified),
        'protocol_sha256':protocol_sha,
        'candidate_frozen':'persist','primary_baseline_frozen':'current',
        'label_bytes_seen_during_precommit':False,
        'source_provenance_independently_attested':False,
        'claim':'FEATURE_COMMIT_ONLY_NOT_BLIND_NOT_INDEPENDENT_CUSTODY'}


def exact_one_sided_sign_p(wins:int,losses:int):
    n=wins+losses
    return round(sum(comb(n,i) for i in range(wins,n+1))/(2**n),10) if n else None


def evaluate(rows,features_sha,labels,labels_sha,commit,protocol_sha):
    if (type(commit)!=dict or commit.get('schema')!=COMMIT_SCHEMA or
        commit.get('protocol_sha256')!=protocol_sha or
        commit.get('unlabelled_source_sha256')!=features_sha or
        commit.get('candidate_frozen')!='persist' or
        commit.get('primary_baseline_frozen')!='current' or
        commit.get('label_bytes_seen_during_precommit') is not False or
        commit.get('source_provenance_independently_attested') is not False or
        commit.get('claim')!='FEATURE_COMMIT_ONLY_NOT_BLIND_NOT_INDEPENDENT_CUSTODY'):
        raise ValueError('tampered or wrong precommit')
    expected=precommit(rows,features_sha,commit.get('source_id_operator_asserted',''),protocol_sha)
    if expected!=commit:
        raise ValueError('precommit metadata does not reconstruct from raw features')
    if labels_sha==features_sha or set(labels)!=set(x[0] for x in rows):
        raise ValueError('labels do not match the committed measurement instants')
    truth=native_boolean_truth_table()
    buckets=admitted_pairs(rows)
    day_records=[]; fullcurrent=[]; fullpersist=[]; fulllabel=[]
    for day,pairs in buckets.items():
        curr=[];persist=[]; y=[]
        for before,after in pairs:
            pat=f'{int(before[2]>=200)}{int(after[2]>=200)}'
            pred=truth[pat]
            # Source A1b truth table is calculated without labels. They are read only here.
            curr.append(pred['current']); persist.append(pred['persist']); y.append(labels[after[0]])
        if not y:
            continue
        mc=metrics(curr,y);mp=metrics(persist,y)
        if len(y)>=MIN_PAIRS_PER_DAY:
            group='occupied_day' if any(y) else 'empty_day'
            day_records.append({'utc_day':day,'kind_posthoc_by_external_labels':group,
                'n':len(y),'positives':sum(y),'current_errors':mc['errors'],
                'persist_errors':mp['errors'],
                'current_fn':mc['fn'],'persist_fn':mp['fn'],
                'net_errors_avoided':mc['errors']-mp['errors'],
                'paired_error_rate_delta':round((mc['errors']-mp['errors'])/len(y),9)})
        fullcurrent.extend(curr);fullpersist.extend(persist);fulllabel.extend(y)
    occ=[x for x in day_records if x['kind_posthoc_by_external_labels']=='occupied_day']
    empty=[x for x in day_records if x['kind_posthoc_by_external_labels']=='empty_day']
    positive_days=sum(x['net_errors_avoided']>0 for x in occ)
    negative_days=sum(x['net_errors_avoided']<0 for x in occ)
    discordant_days=positive_days+negative_days
    mean=round(sum(x['paired_error_rate_delta'] for x in occ)/len(occ),9) if occ else None
    fn_current=sum(x['current_fn'] for x in occ)
    fn_persist=sum(x['persist_fn'] for x in occ)
    positive_obs=sum(x['positives'] for x in occ)
    fn_uplift=round((fn_persist-fn_current)/positive_obs,9) if positive_obs else None
    sign_p=exact_one_sided_sign_p(positive_days,negative_days)
    eligible=(len(occ)>=MIN_DAY_BLOCKS and discordant_days>=MIN_DISCORDANT_DAYS)
    success=(eligible and mean>=MIN_MEAN_IMPROVEMENT and sign_p<=MAX_SIGN_P and
        fn_uplift<=MAX_FN_RATE_UPLIFT)
    status=(STATUS_INSUFFICIENT if not eligible else STATUS_PASS if success else STATUS_FAIL)
    return {'schema':SCHEMA,'status':status,'source_id_operator_asserted':commit['source_id_operator_asserted'],
        'source_provenance_independently_attested':False,'independent_blind_holdout':False,
        'source_sha256':features_sha,'labels_sha256':labels_sha,
        'precommit_metadata':commit,'protocol_sha256':protocol_sha,
        'A1b_four_pattern_truth_table_verified':truth,
        'frozen_candidate':'persist','frozen_static_comparator':'current',
        'target':'external occupied STATE at time t, prior light at t-1',
        'aggregate':{'current':metrics(fullcurrent,fulllabel),
                     'persist':metrics(fullpersist,fulllabel)},
        'primary_occupied_days':{'qualified_days':len(occ),'wins':positive_days,
            'losses':negative_days,'ties':len(occ)-discordant_days,
            'mean_day_error_rate_improvement':mean,'one_sided_day_sign_p_descriptive':sign_p,
            'fn_rate_uplift':fn_uplift,'discordant_days':discordant_days,
            'minimum_occupied_days':MIN_DAY_BLOCKS,'minimum_discordant_days':MIN_DISCORDANT_DAYS,
            'required_minimum_mean_improvement':MIN_MEAN_IMPROVEMENT,
            'required_maximum_fn_uplift':MAX_FN_RATE_UPLIFT,
            'required_maximum_sign_p':MAX_SIGN_P,
            'screen_supports_predeclared_direction':bool(success)},
        'secondary_empty_days':{'qualified_days':len(empty),
            'net_errors_avoided':sum(x['net_errors_avoided'] for x in empty)},
        'day_blocks':day_records,
        'claims_excluded':['not an independent custody or cryptographically hidden blind test',
            'no endogenous neuron-to-neuron semantic reward',
            'no native local learner or program update',
            'no independent-day assumption established by a day-level sign p-value',
            'no randomization or causal learning superiority demonstrated',
            'operator attests real new independent data; code cannot verify provenance',
            'all program behavior is equivalent to fixed Boolean light thresholds']}
