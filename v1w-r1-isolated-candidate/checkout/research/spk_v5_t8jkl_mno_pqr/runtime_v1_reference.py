"""T8PQR: new reference v1 execution owner, bound to unchanged frozen PE/BV.

Semantic feedback follows A->B->C INSIDE THIS V1 REFERENCE bus and reaches its
own transactional P authority; BV-v0e itself remains strictly structural.
"""
from __future__ import annotations
from pathlib import Path
import tempfile
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from .semantic_bus_v1 import dispatch
from .p_authority_v1 import PAuthorityV1


def epoch(state,cue,goal,*,drop=False,source_executor=None):
    issue=state.issue(cue,goal)
    runner=execute_raw if source_executor is None else source_executor
    source,evidence=runner(issue['choice'],goal,drop_forward=drop)
    message=dispatch(source,issue,drop=drop)
    settled=state.settle(issue,source,message,drop=drop)
    return {'issue_id':issue['id'],'context':cue,'goal':goal,'chosen':issue['choice'],
        'policy_version':issue['version'],'verdict':settled['outcome'],
        'P_write':settled['P_written'],'reference_grant_id':settled['grant_id'],
        'source_sha256':digest(source), 'semantic_v1_digest':digest(message) if message else None,
        'structural_BV_delivered':evidence['reverse_A_B_C']}


def trial(*,learn=True,phases=4,drop=False,reopen_every=12,source_executor=None):
    with tempfile.TemporaryDirectory(prefix='spk-t8-v1ref-') as tmp:
        state=PAuthorityV1(Path(tmp)/'P.sqlite',learn=learn)
        rows=[]
        for phase in range(phases):
            for n in range(24):
                cue=n%2
                goal=(11 if cue==0 else 12) if phase%2==0 else (12 if cue==0 else 11)
                rows.append(epoch(state,cue,goal,drop=drop,source_executor=source_executor))
                if reopen_every and len(rows)%reopen_every==0:state.reopen()
        audit=state.audit();state.close()
    return {'episodes':len(rows),'successes':sum(r['verdict']=='IMPROVED' for r in rows),
        'failed':sum(r['verdict']=='WORSENED' for r in rows),
        'reference_v1_semantic_receipts':sum(r['semantic_v1_digest'] is not None for r in rows),
        'reference_v1_P_grants':audit['reference_grants'],
        'reference_v1_P_writes':audit['reference_P_writes'],
        'native_SPK_P_grants':0,'native_SPK_BV_semantic':0,
        'source_rows_sha256':digest([r['source_sha256'] for r in rows]),
        'row_digest':digest(rows),'audit':audit}
