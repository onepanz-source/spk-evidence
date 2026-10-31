"""Read-only v0r semantic-signature pairing from already captured native v0o runs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from spk_bv_research.paired_runs_v0o import load_capture, pins, PairError
from spk_bv_research.feedback_lineage_v0q import audit, EXPECTED_NATIVE_SHA
from spk_bv_research.policy_identity_v0p import compute
from spk_bv_research.semantic_pairing_v0r import compare


def main(argv=None):
    cli=argparse.ArgumentParser()
    cli.add_argument('--capture-13',type=Path,required=True)
    cli.add_argument('--capture-811',type=Path,required=True)
    cli.add_argument('--out',type=Path,required=True)
    cli.add_argument('--repo',type=Path,default=Path.cwd())
    a=cli.parse_args(argv)
    try:
        repo=a.repo.resolve(strict=True)
        parent=a.out.parent.resolve(strict=True)
        target=parent / a.out.name
        if (a.out.is_symlink() or a.out.exists() or
            not target.is_relative_to(Path('/tmp')) or target.is_relative_to(repo)):
            raise PairError('new output required under /tmp outside repository')
        c1=load_capture(a.capture_13)
        c2=load_capture(a.capture_811)
        if (c1['native_fixture_sha256'] != EXPECTED_NATIVE_SHA or
            c1['native_fixture_sha256'] != c2['native_fixture_sha256'] or
            c1['native_fixture'] != c2['native_fixture'] or
            c1['producer_pins'] != c2['producer_pins'] or
            pins(repo) != c1['producer_pins']):
            raise PairError('native source pins, fixture or independent captures mismatch')
        fixture = c1['native_fixture']
        inherited = compute(fixture, c1['native_fixture_sha256'])
        observed = audit(fixture, c1['native_fixture_sha256'])
        if not inherited['conserved_outcomes_all']:
            raise PairError('v0p conserved forward outcomes not verified')
        if sorted(observed['delivery_payload_divergent_ids']) != sorted(inherited['identity_joins']['feedback_delivery']['payload_mismatches']):
            raise PairError('v0p/v0q disagree on feedback delivery mismatches')
        if sorted(observed['grant_payload_divergent_ids']) != sorted(inherited['identity_joins']['feedback_grant']['payload_mismatches']):
            raise PairError('v0p/v0q disagree on feedback grant mismatches')
        report = compare(fixture,c1['native_fixture_sha256'])
        report['source_pins_reverified'] = True
        report['inherited_v0p_outcome_conservation'] = True
        report['inherited_v0q_field_audit'] = True
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x', encoding='utf-8') as fh:
            json.dump(report,fh,sort_keys=True,ensure_ascii=True,indent=2,allow_nan=False)
            fh.write('\n')
        print(json.dumps({
            'status':report['status'],
            'structural_pairing':report['complete_unambiguous_structural_pairing'],
            'matched':report['unique_cross_policy_pair_count'],
            'relabelled':len(report['relabelled_packet_pairs']),
            'ambiguous_groups':report['ambiguous_signature_groups'],
            'output':str(target),
        },sort_keys=True))
        return 0
    except (ValueError,OSError,TypeError,KeyError,IndexError) as ex:
        print('BV v0r REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
