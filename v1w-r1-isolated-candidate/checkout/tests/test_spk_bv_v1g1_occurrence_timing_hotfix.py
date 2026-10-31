"""BV v1g.1: transport grants, representation tolerance and fail-closed checks.

These are synthetic conformance fixtures, not a native fwork execution.
"""
from __future__ import annotations

import copy
import pytest

from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_route_lineage_v1g import analyze
from tests.test_spk_bv_v1g_native_route_lineage import sample


def _with_grants(off, on):
    for arm in (off,on):
        f=arm['forward']
        f['link_grants']=[{
            'id':o['id'],'source':o['source'],'target':o['target'],
            'source_pe':o['source_pe'],'target_pe':o['target_pe'],
            'tick':o['emitted_at'],'delivered_at':o['delivered_at'], 'wait':0}
            for o in f['occurrences']]


def test_original_without_grants_keeps_strict_route_delay_contract():
    n,off,on,owners,f=sample()
    assert analyze(n,off,on,owners,v1f=f)['original_off_occurrences']==2


def test_realistic_forward_grant_join_and_parent_tuple_custody():
    n,off,on,owners,f=sample()
    _with_grants(off,on)
    for arm in (off,on):
        for o in arm['forward']['occurrences']:
            o['parents']=tuple(o['parents'])
    before=copy.deepcopy((n,off,on,owners,f))
    res=analyze(n,off,on,owners,v1f=f)
    assert res['original_off_occurrences']==2
    assert res['native_reverse_delivery_count']==2
    assert (n,off,on,owners,f)==before


def test_delivery_before_nominal_emission_plus_delay_requires_joined_grant():
    n,off,on,owners,f=sample()
    # The edge's nominal delay is two ticks, but an explicit transport grant
    # attests that the observable delivered_at tick is only +1.
    from dataclasses import replace
    n=(n[0],type(n[1])(tuple(replace(e,delay_ticks=2) for e in n[1].static_routes)),n[2])
    from spk_bv_research.off_on_v0t import snapshot
    f['native_fixture_sha256']=snapshot(n)
    for arm in (off,on):
        for o in arm['forward']['occurrences']:
            o['delay']=2
    with pytest.raises(InterventionError,match='without grant evidence'):
        analyze(n,off,on,owners,v1f=f)
    _with_grants(off,on)
    res=analyze(n,off,on,owners,v1f=f)
    assert res['off_route_multiset_equal_on']


@pytest.mark.parametrize('tamper',[
    lambda g: g.__setitem__('delivered_at', 99),
    lambda g: g.__setitem__('source','C'),
    lambda g: g.__setitem__('source_pe','P9'),
    lambda g: g.__setitem__('tick', -1),
    lambda g: g.__setitem__('tick', 20),
    lambda g: g.__setitem__('id','nonexistent'),
    lambda g: g.__setitem__('target','A'),
])
def test_grant_tamper_rejected(tamper):
    n,off,on,owners,f=sample();_with_grants(off,on)
    tamper(off['forward']['link_grants'][0])
    with pytest.raises(InterventionError):analyze(n,off,on,owners,v1f=f)


def test_duplicate_grants_rejected():
    n,off,on,owners,f=sample();_with_grants(off,on)
    off['forward']['link_grants'].append(copy.deepcopy(off['forward']['link_grants'][0]))
    with pytest.raises(InterventionError):analyze(n,off,on,owners,v1f=f)


def test_missing_grant_rejected():
    n,off,on,owners,f=sample();_with_grants(off,on)
    off['forward']['link_grants'].pop()
    with pytest.raises(InterventionError):analyze(n,off,on,owners,v1f=f)


def test_negative_emission_time_rejected_even_if_transport_joins():
    n,off,on,owners,f=sample();_with_grants(off,on)
    off['forward']['occurrences'][0]['emitted_at']=-1
    with pytest.raises(InterventionError):analyze(n,off,on,owners,v1f=f)


def test_invalid_parent_container_rejected():
    n,off,on,owners,f=sample();_with_grants(off,on)
    off['forward']['occurrences'][0]['parents']='wrong'
    with pytest.raises(InterventionError):analyze(n,off,on,owners,v1f=f)


def test_inconsistent_parent_temporal_order_still_rejected():
    n,off,on,owners,f=sample();_with_grants(off,on)
    off['forward']['occurrences'][1]['parents']=['r2']
    with pytest.raises(InterventionError):analyze(n,off,on,owners,v1f=f)


def test_report_explicitly_separates_grant_join_from_nominal_delay():
    n,off,on,owners,f=sample()
    without=analyze(n,off,on,owners,v1f=f)
    assert not without['original_forward_transport_grants_joined']
    assert without['transport_temporal_semantics']=='NOMINAL_DELAY_ONLY_NO_GRANT_EVIDENCE'
    _with_grants(off,on)
    with_grants=analyze(n,off,on,owners,v1f=f)
    assert with_grants['original_forward_transport_grants_joined']
    assert with_grants['transport_temporal_semantics']=='GRANT_JOIN_CONFIRMED_NOT_NOMINAL_DELAY_SUM'
