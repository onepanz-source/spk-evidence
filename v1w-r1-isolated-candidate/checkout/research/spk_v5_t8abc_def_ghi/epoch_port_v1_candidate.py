"""T8GHI: candidate interface integrated at research epoch boundary only."""
from __future__ import annotations
from pathlib import Path
import tempfile
from research.spk_v5_t7abc_def_ghi.epoch_state_v0 import EpochState
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from .semantic_packet_v1_candidate import make_packet
from .p_admission_v1_candidate import evaluate,settle_research


def single(store,cue,goal,*,drop=False):
    issue=store.issue(cue,goal)
    raw,source_evidence=execute_raw(issue['choice'],goal,drop_forward=drop)
    if not drop:
        packet=make_packet(raw,issue)
        admission=evaluate(raw,issue,packet)
        committed=settle_research(store,raw,issue,packet,admission)
    else:
        # Cannot manufacture semantic BV receipt for a missing C->A path.
        packet=None;admission=None
        committed=store.settle(issue,source_evidence)
    return {'issue':issue,'A_outcome':source_evidence['A_outcome'],
        'C_updated':committed['updated'],
        'native_P_write':False,'native_BV_semantic':False,
        'semantic_packet_digest':digest(packet) if packet else None,
        'admission_digest':digest(admission) if admission else None,
        'source_sha256':source_evidence['source_sha256'],
        'structural_BV':source_evidence['reverse_A_B_C']}


def trial(*,learn=True,phases=4,drop=False):
    with tempfile.TemporaryDirectory(prefix='spk-t8-candidate-') as tmp:
        store=EpochState(Path(tmp)/'P.sqlite',learn=learn)
        rows=[]
        for phase in range(phases):
            for n in range(24):
                cue=n%2
                goal=(11 if cue==0 else 12) if phase%2==0 else (12 if cue==0 else 11)
                rows.append(single(store,cue,goal,drop=drop))
                if n in (11,23):store.reopen()
        audit=store.audit();store.close()
    return {'episodes':len(rows),'successes':sum(r['A_outcome']=='IMPROVED' for r in rows),
       'updates':audit['updates'],'source_rows_digest':digest([r['source_sha256'] for r in rows]),
       'semantic_packet_count':sum(r['semantic_packet_digest'] is not None for r in rows),
       'candidate_request_count':sum(r['admission_digest'] is not None for r in rows),
       'native_grants':0,'native_semantic_BV_deliveries':0,'native_P_writes':0,
       'audit':audit,'rows_digest':digest(rows)}
