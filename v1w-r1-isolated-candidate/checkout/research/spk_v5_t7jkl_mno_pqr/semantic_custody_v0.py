"""T7JKL research-only bound semantic receipt for frozen *structural* BV.

A 21/22 semantic output remains outside the frozen BV payload. This is a
strict cross-plane, host-authored join, NOT authentication or native semantic BV.
"""
from __future__ import annotations
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import (
    check, verify_source, BridgeRejected,
)

FORMAT='spk-v5-t7jkl-shadow-semantic-custody/v0'

def _valid_issue(issued):
    check(type(issued) is dict and set(issued)=={'id','cue','choice','version','goal'},'ISSUE_KEYS')
    check(all(type(issued[x]) is int for x in issued),'ISSUE_TYPE')
    check(issued['id']>=0 and issued['cue'] in (0,1) and issued['choice'] in (11,12)
          and issued['goal'] in (11,12) and issued['version']>=0,'ISSUE_DOMAIN')

def _emission(source,node,channel):
    selected=[x for x in source['forward']['emissions'] if x.get('node_id')==node and x.get('channel')==channel]
    check(len(selected)==1,'SEMANTIC_EMISSION_COUNT')
    return selected[0]

def compose(source,issued,*,drop_forward=False):
    """Compute A/B/C custody overlays from raw BV source, fail closed on gaps."""
    _valid_issue(issued)
    ev=verify_source(source,issued['choice'],issued['goal'],drop_forward=drop_forward)
    if drop_forward:
        return {'schema':FORMAT,'issue':dict(issued),'source_sha256':ev['source_sha256'],
                'A_packet':None,'B_packet':None,'C_receipt':None,'outcome':'ABSENT'}
    # Evidence derived from PE output and original structural BV source.
    a=_emission(source,'A',ev['A_emission'])
    assess=source['feedback']['assessments'][0]
    forwards=source['forward']['occurrences']
    deliveries=source['feedback']['deliveries']
    check(len(deliveries)==2 and len(forwards)==2,'BV_CHAIN_LENGTH')
    A={'issuer':'A','destination':'B','issue':dict(issued),'semantic_channel':ev['A_emission'],
       'source_sha256':ev['source_sha256'],'semantic_emission_sha256':digest(a),
       'assessment_sha256':digest(assess),'last_input_id':forwards[1]['id'],
       'structural_A_B_sha256':digest(deliveries[0])}
    B={'issuer':'B','destination':'C','issue_id':issued['id'],
       'A_packet_sha256':digest(A),'structural_B_C_sha256':digest(deliveries[1]),
       'source_sha256':ev['source_sha256']}
    C={'receiver':'C','issue':dict(issued),'A_packet_sha256':digest(A),
       'B_packet_sha256':digest(B),'source_sha256':ev['source_sha256'],
       'outcome':ev['A_outcome'],'C_receipt_sha256':digest({'A':A,'B':B,'issue':issued})}
    return {'schema':FORMAT,'issue':dict(issued),'source_sha256':ev['source_sha256'],
            'A_packet':A,'B_packet':B,'C_receipt':C,'outcome':ev['A_outcome']}

def verify(source,issued,received,*,drop_forward=False):
    """Verify the whole overlay, not just a digest supplied by its sender."""
    check(type(received) is dict,'ENVELOPE_TYPE')
    expected=compose(source,issued,drop_forward=drop_forward)
    check(received==expected,'SEMANTIC_CUSTODY_DRIFT')
    return expected
