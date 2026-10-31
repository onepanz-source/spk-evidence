"""v4ak-v4am separate-custody head witness. Research, NOT real key custody.

This module does not store signing keys or mutate the native learner. A caller
must provide a witness key and separately preserve the resulting anchor bytes
or their digest. If the storage owner controls both, there is no protection.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import json
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_disagreement_fixture_v4aeag import TEST_VIEW_KEYS
from spk_bv_research.task_escrow_store_v4ahaj import DurableEscrow, EscrowRejected

SCHEMA = 'spk-bv-external-head-witness/research-v4ak-v4am'
DOMAIN = b'SPK/BV/OUTSIDE-HEAD-WITNESS-V4AKAM\x00'
REQUIRED_REPORT_SHA = '8fd397a7b3b1cf693f1c5e3be3e78021f504609a0b2695b2bbe67e07d65f8674'
GENESIS = '0' * 64
STATUS = 'EXTERNAL_HEAD_FORK_ROLLBACK_DETECTION_LAB_ONLY_NO_TASK_TRUTH'


class AnchorRejected(ValueError):
    pass


def digest(value):
    return sha256(canon(value)).hexdigest()


def _require_hex(value):
    return type(value) is str and len(value) == 64 and all(
        ch in '0123456789abcdef' for ch in value)


def _read_pinned_report(raw):
    if type(raw) is not bytes or sha256(raw).hexdigest() != REQUIRED_REPORT_SHA:
        raise AnchorRejected('unexpected signed v4ahaj predecessor bytes')
    try:
        report = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise AnchorRejected('invalid predecessor JSON') from exc
    if (canon(report) != raw or report.get('program_adoptions') != 0 or
            report.get('native_learning_implemented') is not False or
            report.get('native_v0e_modified') is not False or
            report.get('architecture_v1_modified') is not False or
            report.get('sqlite_logical_witness', {}).get('entries') != 72 or
            report['sqlite_logical_witness'].get('persisted_unique_nonces') != 144 or
            not _require_hex(report['sqlite_logical_witness'].get('head'))):
        raise AnchorRejected('signed predecessor content or research boundary drift')
    return report


def _sign(body, key):
    if type(key) is not bytes or len(key) < 32:
        raise AnchorRejected('invalid separately provisioned witness test key')
    return hmac.new(key, DOMAIN + canon(body), 'sha256').hexdigest()


def seal_state(state, report_sha, key, *, serial=1,
               prior_anchor_sha256=GENESIS, issuer='LAB_ANCHOR_ROLE'):
    """Return signed public fixture artifact, not a trusted third-party claim."""
    if (type(state) is not dict or
            set(state) != {'entries', 'head', 'persisted_unique_nonces',
                           'parent_sha256'} or
            not _require_hex(state.get('head')) or
            not _require_hex(state.get('parent_sha256')) or
            type(state.get('entries')) is not int or state['entries'] < 0 or
            type(state.get('persisted_unique_nonces')) is not int or
            state['persisted_unique_nonces'] != 2 * state['entries'] or
            not _require_hex(report_sha) or
            type(serial) is not int or serial < 1 or
            not _require_hex(prior_anchor_sha256) or
            type(issuer) is not str or issuer != 'LAB_ANCHOR_ROLE'):
        raise AnchorRejected('malformed state or anchor serial/lineage')
    body = {'schema': SCHEMA, 'issuer': issuer, 'serial': serial,
            'previous_anchor_sha256': prior_anchor_sha256,
            'source_report_sha256': report_sha,
            'sqlite_witness': state,
            'signer_kind': 'PUBLIC_RESEARCH_FIXTURE_NO_REAL_IDENTITY'}
    return {'body': body, 'mac_sha256': _sign(body, key)}


def verify_capsule(raw, key, *, expected_anchor_sha256=None):
    if type(raw) is not bytes:
        raise AnchorRejected('anchor bytes required')
    if (expected_anchor_sha256 is not None and
            sha256(raw).hexdigest() != expected_anchor_sha256):
        raise AnchorRejected('anchor is not the independently retained version')
    try:
        capsule = json.loads(raw)
        body = capsule['body']
    except (ValueError, KeyError, TypeError) as exc:
        raise AnchorRejected('malformed anchor capsule') from exc
    if (type(capsule) is not dict or set(capsule) != {'body', 'mac_sha256'} or
            canon(capsule) != raw or type(body) is not dict or
            set(body) != {'schema', 'issuer', 'serial', 'previous_anchor_sha256',
                          'source_report_sha256', 'sqlite_witness', 'signer_kind'} or
            body['schema'] != SCHEMA or body['issuer'] != 'LAB_ANCHOR_ROLE' or
            body['signer_kind'] != 'PUBLIC_RESEARCH_FIXTURE_NO_REAL_IDENTITY' or
            type(body['serial']) is not int or body['serial'] < 1 or
            not _require_hex(body['previous_anchor_sha256']) or
            not _require_hex(body['source_report_sha256']) or
            type(capsule['mac_sha256']) is not str or
            not hmac.compare_digest(capsule['mac_sha256'], _sign(body, key))):
        raise AnchorRejected('invalid witness signature, domain, structure or custody')
    # Re-run typed validation on the witnessed SQLite state.
    seal_state(body['sqlite_witness'], body['source_report_sha256'], key,
               serial=body['serial'],
               prior_anchor_sha256=body['previous_anchor_sha256'])
    return body


def check_anchored_database(db_path, parent_sha256, capsule_raw, key,
                            *, expected_anchor_sha256=None,
                            view_keys=TEST_VIEW_KEYS):
    body = verify_capsule(capsule_raw, key,
                          expected_anchor_sha256=expected_anchor_sha256)
    if body['sqlite_witness']['parent_sha256'] != parent_sha256:
        raise AnchorRejected('signed predecessor not bound to escrow')
    try:
        with DurableEscrow.open(db_path, parent_sha256, view_keys,
                                external_head=body['sqlite_witness']['head']) as store:
            state = store.verify(external_head=body['sqlite_witness']['head'])
    except (EscrowRejected, OSError) as exc:
        raise AnchorRejected('local SQLite disagrees with separately held anchor') from exc
    if state != body['sqlite_witness']:
        raise AnchorRejected('SQLite state diverges from outside-head witness')
    return state


def seal_reported_database(report_raw, db_path, key):
    report = _read_pinned_report(report_raw)
    parent = report['signed_v4aeag_sha256']
    with DurableEscrow.open(db_path, parent, TEST_VIEW_KEYS,
                            external_head=report['sqlite_logical_witness']['head']) as store:
        state = store.verify(external_head=report['sqlite_logical_witness']['head'])
    if state != report['sqlite_logical_witness']:
        raise AnchorRejected('signed v4ahaj report and escrow state differ')
    return seal_state(state, sha256(report_raw).hexdigest(), key)
