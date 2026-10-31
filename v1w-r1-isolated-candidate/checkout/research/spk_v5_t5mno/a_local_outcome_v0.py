"""Pure A-local synthetic goal observation model, strictly research only.

The source is a host-installed Python policy/profile; not an authenticated
sensor, trusted execution environment, causal intervention, or BV credit.
Crucially the function accepts no C sign, C assessment, source fault or relay.
"""
from __future__ import annotations

class LocalAError(ValueError): pass

def require(condition,code):
    if not condition:raise LocalAError(code)

def synthetic_A_observation(case_index):
    require(type(case_index) is int and 0<=case_index<180,'INVALID_LOCAL_CASE')
    # Fixed *A-local* target and prior condition, never computed from C output.
    target, before=10,6
    after=(8,4,6)[case_index%3]
    return {'case_index':case_index,'goal':target,'before':before,'after':after,
            'lineage':'A_LOCAL_SYNTHETIC_HOST_PROVISIONED'}

def evaluate_observation(observation):
    require(type(observation) is dict and set(observation)=={'case_index','goal','before','after','lineage'},'A_OBSERVATION_SCHEMA')
    require(type(observation['case_index']) is int and 0<=observation['case_index']<180,'A_CASE')
    for key in ('goal','before','after'):
        require(type(observation[key]) is int and 0<=observation[key]<=100,'A_MEASUREMENT_'+key)
    require(observation['lineage']=='A_LOCAL_SYNTHETIC_HOST_PROVISIONED','A_LINEAGE')
    before=abs(observation['goal']-observation['before'])
    after=abs(observation['goal']-observation['after'])
    sign=(1 if after<before else -1 if after>before else 0)
    return {'assessment':sign,'error_before':before,'error_after':after,
            'outcome':('IMPROVED' if sign==1 else 'WORSENED' if sign==-1 else 'UNCHANGED')}
