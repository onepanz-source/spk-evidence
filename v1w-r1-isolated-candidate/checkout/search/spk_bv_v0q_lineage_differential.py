"""Read-only two-run field-level source-pinned audit for v0p mismatch witnesses."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from spk_bv_research.paired_runs_v0o import load_capture,pins,PairError
from spk_bv_research.feedback_lineage_v0q import audit,EXPECTED_NATIVE_SHA
from spk_bv_research.policy_identity_v0p import compute


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--capture-13',type=Path,required=True)
    p.add_argument('--capture-811',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    a=p.parse_args(argv)
    try:
        repo=a.repo.resolve(strict=True)
        out=a.out.absolute()
        if a.out.is_symlink() or a.out.exists() or not out.is_relative_to(Path('/tmp')) or out.is_relative_to(repo):
            raise PairError('output must be a new regular path under /tmp outside repository')
        left=load_capture(a.capture_13)
        right=load_capture(a.capture_811)
        if (left['native_fixture_sha256']!=EXPECTED_NATIVE_SHA or
            left['native_fixture_sha256']!=right['native_fixture_sha256'] or
            left['native_fixture']!=right['native_fixture'] or
            left['producer_pins']!=right['producer_pins'] or
            pins(repo)!=left['producer_pins']):
            raise PairError('independent capture hashes/content or source pins differ')
        previous=compute(left['native_fixture'],left['native_fixture_sha256'])
        if not previous['conserved_outcomes_all']:
            raise PairError('v0p forward outcomes no longer conserved')
        result=audit(left['native_fixture'],left['native_fixture_sha256'])
        if (result['delivery_payload_divergent_ids']!=previous['identity_joins']['feedback_delivery']['payload_mismatches'] or
            result['grant_payload_divergent_ids']!=previous['identity_joins']['feedback_grant']['payload_mismatches']):
            raise PairError('v0q per-field and v0p record-level mismatches disagree')
        result['source_pins_reverified']=True
        result['v0p_outcome_conservation_recomputed']=True
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x',encoding='utf-8') as fh:
            json.dump(result,fh,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)
            fh.write('\n')
        print(json.dumps({'status':result['status'],'divergent_ids':result['packet_ids_not_semantically_equivalent_by_same_id'],
                          'out':str(out)},sort_keys=True))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as e:
        print('BV v0q REJECTED: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
