"""Independent process capture/replay for BV v0e live dual-event pilot."""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path

from spk_backvalidation_v0.contract_v0 import canonical, digest, strict_loads
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, LiveBVRejected, execute_live_v0e)
from spk_backvalidation_v0.a3d_shared_grants_v0d import actual_a3d_v0d
from spk_backvalidation_v0.simulator_evidence_v0b import NEW, OLD
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d

SCHEMA='spk-bv-live-dual-evidence/v0e'
FROZEN='5af99cd1f4d603bf0c8e1557a6561c107765fdb5'


def fixture(program=NEW,ticks=(1,3),**kwargs):
    case,fabric,(tp,pp,mp,lp),_=actual_a3d_v0d(program,ticks,
        pe_slots=2,link_slots=1,fabric_slots=1,inflight=4,**kwargs)
    return case,fabric,(tp,replace(pp,fabric_slots_per_tick=3),mp,lp)


def capture():
    case,fabric,plans=fixture()
    offline=execute_causal_transport_v1d(case,fabric,*plans,max_batches=128,max_events=256)
    disabled=execute_live_v0e(case,fabric,*plans,LiveBVPlanV0e(enabled=False))
    if (disabled['forward']['terminal'] != offline['result']['terminal_outputs'] or
        [(p['tick'],p['source']) for p in disabled['forward']['link_grants']] !=
        [(p['tick'],p['source_node']) for p in offline['transport']['link_grants']]):
        raise LiveBVRejected('live BV-disabled fixture disagrees with frozen A3d')
    forward_first=execute_live_v0e(case,fabric,*plans,LiveBVPlanV0e(priority='forward-first'))
    feedback_first=execute_live_v0e(case,fabric,*plans,LiveBVPlanV0e(priority='feedback-first'))
    if not (len(forward_first['forward']['link_grants'])==4 and
            len(feedback_first['forward']['link_grants'])==4 and
            len(forward_first['feedback']['link_grants'])==4 and
            len(feedback_first['feedback']['link_grants'])==4 and
            [e['timestamp'] for e in forward_first['forward']['terminal']]==[3,5] and
            [e['timestamp'] for e in feedback_first['forward']['terminal']]==[3,7]):
        raise LiveBVRejected('no evidenced live feedback-induced delay')
    bcase,bfabric,bplans=fixture(OLD)
    baseline=execute_live_v0e(bcase,bfabric,*bplans,LiveBVPlanV0e())
    if baseline['feedback']['link_grants'] or baseline['forward']['terminal']:
        raise LiveBVRejected('spurious BV observation on baseline')
    return {'schema':SCHEMA,'frozen_commit':FROZEN,
            'scope':'three-neuron shared-credit dual-event research executor',
            'bv_disabled_a3d_link_grants':len(offline['transport']['link_grants']),
            'bv_disabled_a3d_terminal':offline['result']['terminal_outputs'],
            'bv_disabled_live_digest':digest(disabled),
            'forward_first':forward_first,'feedback_first':feedback_first,
            'negative_baseline':{'forward':len(baseline['forward']['link_grants']),
                                 'feedback':len(baseline['feedback']['link_grants'])},
            'claims_excluded':['frozen-A3d-live-execution','A3d-full-equivalence',
                'independent-runtime-oracle','runtime-authorization','N-node','distributed-clock',
                'adaptive-learning','global-causal-credit','hardware-energy']}


def seal():
    payload=capture()
    return canonical({'payload':payload,'payload_sha256':digest(payload)})


def verify(raw):
    v=strict_loads(raw)
    if (type(v) is not dict or set(v)!={'payload','payload_sha256'} or
        canonical(v)!=raw or digest(v['payload'])!=v['payload_sha256']):
        raise LiveBVRejected('noncanonical or mismatched evidence envelope')
    if v!=strict_loads(seal()):
        raise LiveBVRejected('independent source-backed live replay mismatch')
    p=v['payload']
    return {'status':'LIVE_DUAL_EVENT_REPLAY_PASS','evidence_sha256':digest(v),
            'forward_grants':len(p['feedback_first']['forward']['link_grants']),
            'feedback_grants':len(p['feedback_first']['feedback']['link_grants']),
            'forward_first_terminal_ticks':[x['timestamp'] for x in p['forward_first']['forward']['terminal']],
            'feedback_first_terminal_ticks':[x['timestamp'] for x in p['feedback_first']['forward']['terminal']],
            'note':'NEW research runtime; frozen A3d remains unmodified'}


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write');group.add_argument('--verify')
    args=parser.parse_args()
    if args.write:
        p=Path(args.write);p.write_text(seal(),encoding='utf-8')
        print(canonical({'status':'WRITTEN','file':p.name}))
    else:
        print(canonical(verify(Path(args.verify).read_text(encoding='utf-8'))))

if __name__=='__main__':main()
