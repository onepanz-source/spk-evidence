"""V5-T3a external task ingress and two-stage shadow evaluation.

No live independent dataset is bundled. The label from UCI photos is delivered
as an EXTERNAL reference observation at C, not an endogenous neuron judgment.
Pilot and evaluation use separate public files, but public labels are NOT blind.
Frozen Architecture A1b is invoked for each chosen episode. No native learning.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from random import Random

from spk_v5_research.island_endogenous_demand_v5t2c import (
    DemandEpisode, observe_closed_episode, evaluate_candidate,
)
from spk_v5_research.island_objective_v5t1 import CANDIDATES, Episode

SCHEMA = 'spk-v5-t3a-public-uci-external-task/research-v0'
PROVENANCE = 'UCI Occupancy Detection, doi:10.24432/C5X01N, CC BY 4.0'
UCI_URL = 'https://archive.ics.uci.edu/dataset/357/occupancy-detection'
FEATURE_FIELDS = ('date', 'Temperature', 'Humidity', 'Light', 'CO2', 'HumidityRatio', 'Occupancy')
FEATURE_LIGHT_LUX = 200.0
FEATURE_CO2_PPM = 600.0
PILOT_ROWS = 180
EVALUATION_ROWS = 60
BASELINE = 'overemit'


@dataclass(frozen=True)
class DatasetRow:
    stamp: str
    light: float
    co2: float
    occupied: bool


def sha_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def read_uci(path: Path, *, expected_filename: str) -> tuple[tuple[DatasetRow, ...], str]:
    """Strict, bounded, immutable raw input. Reject overlapping/duplicate clocks.

    The id index is intentionally excluded from the neuron's observations.
    """
    if not isinstance(path, Path) or path.is_symlink() or not path.is_file() or path.name != expected_filename:
        raise ValueError('wrong or unsafe public dataset input')
    size = path.stat().st_size
    if not 120 < size < 2_000_000:
        raise ValueError('empty or unbounded raw dataset')
    raw = path.read_bytes()
    if b'\x00' in raw:
        raise ValueError('invalid binary file')
    try:
        s = raw.decode('utf-8-sig')
        reader = csv.DictReader(s.splitlines(), strict=True)
        if reader.fieldnames is None or not set(FEATURE_FIELDS).issubset(reader.fieldnames) or len(set(reader.fieldnames))!=len(reader.fieldnames):
            raise ValueError('missing UCI fields or duplicate header')
        out = []
        last = None
        for item in reader:
            if None in item or not all(item.get(field) is not None for field in FEATURE_FIELDS):
                raise ValueError('malformed CSV row')
            stamp = item['date'].strip().strip('"')
            parsed = datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S')
            if last is not None and parsed <= last:
                raise ValueError('duplicate or nonmonotone source timestamps')
            last = parsed
            light, co2 = float(item['Light']), float(item['CO2'])
            if not (0 <= light <= 200_000 and 0 < co2 <= 100_000):
                raise ValueError('invalid observed sensor measurements')
            if item['Occupancy'].strip() not in ('0','1'):
                raise ValueError('invalid external binary target')
            out.append(DatasetRow(stamp,light,co2,item['Occupancy'].strip()=='1'))
            if len(out)>25000:
                raise ValueError('unexpected unbounded source records')
    except (ValueError, UnicodeError, TypeError, OverflowError) as exc:
        raise ValueError(f'rejected source CSV: {exc}') from exc
    if len(out)<30:
        raise ValueError('too few temporal source records')
    return tuple(out),sha_bytes(raw)


def downsample(rows: tuple[DatasetRow,...], requested: int) -> tuple[DatasetRow,...]:
    """Index-based, deterministic, label-agnostic and order-preserving."""
    if type(requested) is not int or requested<3 or len(rows)<requested:
        raise ValueError('invalid sample horizon')
    idx = [(i*len(rows))//requested for i in range(requested)]
    if len(set(idx))!=requested:
        raise ValueError('sample collision')
    return tuple(rows[i] for i in idx)


def to_demand_episode(row: DatasetRow, *, index: int) -> DemandEpisode:
    """Fixed threshold adapter from observed sensors; not selected on labels.

    Feature light: C0 if >=200 lux, otherwise C1.
    Second pulse P iff observed CO2 >=600 ppm. These are proxies, not an
    assumed physical or biological equivalence to occupancy.
    """
    if type(row) is not DatasetRow or type(index) is not int or index < 0:
        raise ValueError('invalid row identity')
    tick = 10 * (index + 1)
    events = ((tick, 0 if row.light >= FEATURE_LIGHT_LUX else 1),)
    if row.co2 >= FEATURE_CO2_PPM:
        events += ((tick+1,2),)
    # Photographic Occupancy enters ONLY C's later environment reference pulse.
    return DemandEpisode(Episode(f'uci-{index:05}',events),row.occupied,
                         (2 if row.light >= FEATURE_LIGHT_LUX else 0) + int(row.co2 >= FEATURE_CO2_PPM))


def balanced_schedule(n: int, *, seed: int) -> tuple[str,...]:
    if type(n) is not int or n <= 0 or n % len(CANDIDATES):
        raise ValueError('pilot must have matched action opportunities')
    rng = Random(seed)
    actions=[]
    for _ in range(n//len(CANDIDATES)):
        group=list(CANDIDATES)
        rng.shuffle(group)
        actions.extend(group)
    return tuple(actions)


def fit_shadow(records: tuple[DemandEpisode,...], actions: tuple[str,...]) -> dict:
    """Observed-reward explore-then-commit: never tests unchosen actions."""
    if not records or len(records)!=len(actions):
        raise ValueError('invalid one-arm exploration')
    counts={c:0 for c in CANDIDATES}
    sums={c:0 for c in CANDIDATES}
    for ep,action in zip(records,actions):
        if action not in CANDIDATES:
            raise ValueError('unauthorized research candidate')
        receipt=observe_closed_episode(ep,action)
        if receipt.local_reward is None:
            raise ValueError('UCI reward observation missing; abort training')
        counts[action]+=1
        sums[action]+=receipt.local_reward
    if any(counts[c]==0 for c in CANDIDATES):
        raise ValueError('no support for an experimental arm')
    winner=max(CANDIDATES,key=lambda c:(sums[c]/counts[c],-CANDIDATES.index(c)))
    return {'selected':winner,'chosen_counts':counts,'reward_sums':sums,
            'mean_reward':{c:sums[c]/counts[c] for c in CANDIDATES},
            'native_program_updates':0}


def pilot(rows: tuple[DatasetRow,...], raw_sha: str) -> dict:
    chosen=downsample(rows,PILOT_ROWS)
    records=tuple(to_demand_episode(row,index=i) for i,row in enumerate(chosen))
    actions=balanced_schedule(len(chosen),seed=357052)
    fit=fit_shadow(records,actions)
    return {
        'schema':SCHEMA,'phase':'pilot','status':'PUBLIC_DATA_PILOT_NO_BLIND_CLAIM',
        'provenance':PROVENANCE,'source_url':UCI_URL,
        'source_filename':'datatraining.txt','source_sha256':raw_sha,
        'source_total_rows':len(rows),'selected_rows':len(chosen),
        'source_stamps_sha256':sha_bytes(canonical({'stamps':[r.stamp for r in chosen]})),
        'selected_label_count':sum(r.occupied for r in chosen),
        'pilot_first_stamp':rows[0].stamp,'pilot_last_stamp':rows[-1].stamp,
        'fixed_feature_adapter':{'light_ge_lux':FEATURE_LIGHT_LUX,'co2_ge_ppm':FEATURE_CO2_PPM},
        'action_schedule_sha256':sha_bytes(canonical({'chosen_arms':actions})),
        'learner':fit,'program_adoptions':0,'native_engine_modified':False,
        'observational_task_oracle':'photograph-derived occupancy enters C as external reference at closure',
        'claims_excluded':['no true blind holdout','not endogenous island reward',
          'no actual BV reverse reward into A','no integrated PE/link-cost accounting for this UCI adapter',
          'no native learning or network architecture promotion'],
    }


def evaluate(rows: tuple[DatasetRow,...], raw_sha: str, pilot_certificate: dict) -> dict:
    """Selection frozen by pilot certificate, before evaluative labels enter.

    This is *public test-set* evaluation, not blinded custodian evidence.
    The evaluator can compare all arms post-selection; only chosen arm reaches
    the learner; no test or counterfactuals are used to select/revise it.
    """
    if (type(pilot_certificate) is not dict or pilot_certificate.get('schema')!=SCHEMA or
        pilot_certificate.get('phase')!='pilot' or
        pilot_certificate.get('status')!='PUBLIC_DATA_PILOT_NO_BLIND_CLAIM' or
        pilot_certificate.get('source_filename')!='datatraining.txt' or
        type(pilot_certificate.get('learner')) is not dict or
        pilot_certificate['learner'].get('selected') not in CANDIDATES or
        pilot_certificate.get('fixed_feature_adapter')!={'light_ge_lux':FEATURE_LIGHT_LUX,'co2_ge_ppm':FEATURE_CO2_PPM} or
        pilot_certificate.get('program_adoptions')!=0 or pilot_certificate.get('native_engine_modified') is not False):
        raise ValueError('missing/altered/falsified pilot certificate')
    if raw_sha==pilot_certificate['source_sha256']:
        raise ValueError('evaluation uses identical raw pilot data')
    if not (type(pilot_certificate.get('pilot_last_stamp')) is str and
            datetime.strptime(rows[0].stamp, '%Y-%m-%d %H:%M:%S') >
            datetime.strptime(pilot_certificate['pilot_last_stamp'], '%Y-%m-%d %H:%M:%S')):
        raise ValueError('evaluation not temporally separated from pilot')
    fit=pilot_certificate['learner']
    if (fit.get('native_program_updates') != 0 or
        set(fit.get('chosen_counts',{}))!=set(CANDIDATES) or
        set(fit.get('reward_sums',{}))!=set(CANDIDATES) or
        any(type(fit['chosen_counts'][c]) is not int or fit['chosen_counts'][c]<=0 or
            type(fit['reward_sums'][c]) is not int or
            abs(fit['reward_sums'][c])>fit['chosen_counts'][c] for c in CANDIDATES) or
        sum(fit['chosen_counts'].values())!=PILOT_ROWS or
        fit['selected']!=max(CANDIDATES,key=lambda c:(fit['reward_sums'][c]/fit['chosen_counts'][c],-CANDIDATES.index(c)))):
        raise ValueError('internally inconsistent pilot choice')
    sample=downsample(rows,EVALUATION_ROWS)
    records=tuple(to_demand_episode(row,index=i) for i,row in enumerate(sample))
    # Here labels are external auditor truth, NOT an endogenous B/C observation.
    # Evaluate counterfactuals after policy selection to bound interpretation.
    chosen=pilot_certificate['learner']['selected']
    metrics={c:evaluate_candidate(records,c) for c in CANDIDATES}
    return {
        'schema':SCHEMA,'phase':'evaluation','status':'PUBLIC_UCI_EVALUATION_NOT_BLIND',
        'provenance':PROVENANCE,'source_url':UCI_URL,
        'source_filename':'datatest2.txt','source_sha256':raw_sha,
        'pilot_certificate_sha256':sha_bytes(canonical(pilot_certificate)),
        'pilot_source_sha256':pilot_certificate['source_sha256'],
        'source_total_rows':len(rows),'selected_rows':len(sample),
        'evaluation_occupied':sum(r.occupied for r in sample),
        'selected_policy_frozen':chosen,
        'selected_error':metrics[chosen]['error'],
        'baseline_error':metrics[BASELINE]['error'],
        'post_selection_counterfactual_audit_ONLY':metrics,
        'native_program_updates':0,'blind_holdout_claim':False,
        'independent_public_task_origin':True,'endogenous_BV_reward_established':False,
        'claims_excluded':['public test labels are accessible, not blinded',
            'oracle-assisted outcome at C is not autonomous local island reward',
            'pilot source provenance supplied by caller; no external secure custody',
            'frozen architecture and native BV unchanged',
            'no statistical learning guarantee or production promotion'],
    }
