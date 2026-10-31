"""SPK 24v: fail-closed negative admission and observer fault isolation.

A test-only, single-threaded harness. NEVER invoke on a live shared process:
it temporarily replaces observer callbacks / the 24t executor to prove boundary
behavior. Frozen SPK code and earlier SPK modules are not modified on disk.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24v_negative_plan_v0 import (
    MUTATIONS, SCHEMA as PLAN_SCHEMA, checked_catalog_v0, identity_v0,
    negative_plan_v0, observer_plan_v0, route_plan_v0,
    budget_observer_plan_v0, summary_v0,
)

SCHEMA = 'spk-cross-layer-negative-conformance-evidence/v0'


class ExecutorReachedV0(AssertionError):
    """A rejected request reached the frozen execution boundary."""


class ObserverInjectedFaultV0(RuntimeError):
    """Deliberate test fault, not a claimed frozen Network exception class."""


@contextmanager
def _temporarily_replace(owner, method, replacement):
    original = getattr(owner, method)
    setattr(owner, method, replacement)
    try:
        yield
    finally:
        setattr(owner, method, original)


def mutation_request_v0(manifest, pin, mutation):
    """Build intentionally rejected requests; pure and deterministic."""
    if type(manifest) is not str or type(pin) is not str:
        raise TypeError('expected real manifest text and digest')
    kw = {'max_batches': 128, 'max_events': 4096}
    if mutation == 'wrong_pin':
        return manifest, '0'*64, kw
    if mutation == 'malformed_pin':
        return manifest, 'Z'*64, kw
    if mutation == 'zero_batches':
        return manifest, pin, {'max_batches': 0, 'max_events': 4096}
    if mutation == 'boolean_events':
        return manifest, pin, {'max_batches': 128, 'max_events': True}
    if mutation == 'truncated_manifest':
        return '{', sha('{'), kw
    if mutation == 'wrong_root_shape':
        return '[]', sha('[]'), kw
    if mutation == 'nontext_manifest':
        return 42, pin, kw
    raise ValueError('unknown negative mutation: ' + str(mutation))


def _assert_no_successful_receipt(instance, label, error_types):
    """Fail unless a deliberately poisoned single-shot host aborts shut."""
    try:
        instance.run()
    except error_types as ex:
        if instance.phase != 'FAILED':
            raise AssertionError(label + ': fault did not consume the host') from ex
        return type(ex).__name__
    raise AssertionError(label + ': poisoned host returned a receipt')


def _negative_admission_report(cases, manifests):
    from search import spk_24t_diagnostic_manifest_host_v0 as host
    rows = []
    def forbidden(*args, **kwargs):
        raise ExecutorReachedV0('admission reached frozen executor')
    # Contract expects validation before any _attempt. If our guard is invoked
    # do NOT treat that as an ordinary admission failure.
    with _temporarily_replace(host, '_attempt', forbidden):
        for cid, _ in cases:
            manifest, pin = manifests[cid]
            rejected = []
            for mutation in MUTATIONS:
                text, digest, opts = mutation_request_v0(manifest, pin, mutation)
                try:
                    host.execute_manifest_v0(text, digest, **opts)
                except ExecutorReachedV0:
                    raise
                except (ValueError, TypeError, KeyError, AttributeError) as ex:
                    rejected.append([mutation, type(ex).__name__])
                else:
                    raise AssertionError(f'{cid}/{mutation}: invalid request accepted')
            rows.append({'case_id': cid, 'rejections': rejected})
    return rows


def _observer_fault_report(manifests):
    from search import spk_24t_diagnostic_manifest_host_v0 as host
    from search import spk_24p_network_application_host_v0 as backend
    cls = backend._PassiveRecorder
    rows = []

    def throw_batch(self, entry):
        raise ObserverInjectedFaultV0('injected on_batch failure')

    def drop_batch(self, entry):
        return None

    def throw_route(self, entry):
        raise ObserverInjectedFaultV0('injected on_route failure')

    def drop_route(self, entry):
        return None

    def probe(cid, method, replacement, kind, accepted_errors):
        manifest, pin = manifests[cid]
        instance = host.DiagnosticReferenceHostV0(manifest, pin)
        with _temporarily_replace(cls, method, replacement):
            err = _assert_no_successful_receipt(instance, cid + '/' + kind,
                                                accepted_errors)
        # A DIFFERENT host instance must remain capable of normal execution.
        # No rollback of the failed instance is claimed or attempted.
        clean = host.execute_manifest_v0(manifest, pin)
        if clean['status'] != 'CLOSED':
            raise AssertionError(cid + ': clean reference host did not close')
        return {'kind': kind, 'error': err}

    for cid in observer_plan_v0():
        rows.append({'case_id': cid, 'faults': [
            probe(cid, 'on_batch', throw_batch, 'throw_batch',
                  (ObserverInjectedFaultV0,)),
            probe(cid, 'on_batch', drop_batch, 'drop_batch',
                  (AssertionError,)),
        ]})
    for cid in route_plan_v0():
        rows.append({'case_id': cid, 'faults': [
            probe(cid, 'on_route', throw_route, 'throw_route',
                  (ObserverInjectedFaultV0,)),
            probe(cid, 'on_route', drop_route, 'drop_route',
                  (AssertionError,)),
        ]})
    return rows


def _budget_observer_report(manifests):
    from search import spk_24t_diagnostic_manifest_host_v0 as host
    rows = []
    real = host._attempt
    def spoof_observer(net, events, budgets, *, observed):
        status, value, watcher = real(net, events, budgets, observed=observed)
        if observed and status == 'LIMIT_REACHED' and value == 'max_events':
            return status, 'max_batches', watcher
        return status, value, watcher
    with _temporarily_replace(host, '_attempt', spoof_observer):
        for cid in budget_observer_plan_v0():
            manifest, pin = manifests[cid]
            instance = host.DiagnosticReferenceHostV0(manifest, pin)
            try:
                instance.run(max_events=1, max_batches=128)
            except AssertionError as ex:
                if 'observer changed selected failure reason' not in str(ex):
                    raise
                if instance.phase != 'FAILED':
                    raise AssertionError(cid + ': host not consumed by corrupted observer')
                rows.append(cid)
            else:
                raise AssertionError(cid + ': mismatching observer failure reason accepted')
    return rows


def _unexpected_runtime_report(manifests):
    from search import spk_24p_network_application_host_v0 as backend
    from search import spk_24t_diagnostic_manifest_host_v0 as host
    rows = []
    def abnormal(*args, **kwargs):
        raise ObserverInjectedFaultV0('injected unrelated Network failure')
    representative = tuple(cid for cid in observer_plan_v0()
                           if cid.split('/')[1] == 'single')
    if len(representative) != 6:
        raise AssertionError('expected six independent profile representatives')
    with _temporarily_replace(backend, 'run_network_v0', abnormal):
        for cid in representative:
            manifest, pin = manifests[cid]
            instance = host.DiagnosticReferenceHostV0(manifest, pin)
            err = _assert_no_successful_receipt(
                instance, cid + '/unrelated_runtime_failure',
                (ObserverInjectedFaultV0,))
            rows.append({'case_id': cid, 'exception': err})
    return rows


def _compiler_negative_report(cases):
    from search.spk_24u_cross_layer_v0 import _architecture_v0
    from search.spk_24o_extended_differential_v0 import to_frozen_v0
    from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
    from spk_compiler.pe_admission_v0 import NodePlacementV0
    from spk_compiler.resource_admission_v0 import ResourceProfileV0
    arch = _architecture_v0()
    eligible = set(budget_observer_plan_v0())
    rows = []
    for cid, case in cases:
        if cid not in eligible:
            continue
        _, events = to_frozen_v0(case)
        try:
            compile_network_ir_v0(
                network_ir_json='{', initial_events=events,
                resource_profile=ResourceProfileV0(), architecture=arch,
                placements=tuple(NodePlacementV0(n.node_id, f'PE{i}')
                                 for i, n in enumerate(case.nodes)))
        except (ValueError, TypeError, KeyError, AttributeError) as ex:
            rows.append({'case_id': cid, 'rejection': type(ex).__name__})
        else:
            raise AssertionError(cid + ': malformed source IR compiled')
    return rows


def report_v0():
    """Re-executed report: no failure is counted merely because an exception occurred."""
    from search.spk_24u_cross_layer_v0 import compile_case_v0
    cases = checked_catalog_v0()
    manifests = {cid: compile_case_v0(case) for cid, case in cases}
    admission = _negative_admission_report(cases, manifests)
    observer = _observer_fault_report(manifests)
    budget = _budget_observer_report(manifests)
    abnormal = _unexpected_runtime_report(manifests)
    compiler = _compiler_negative_report(cases)
    if (len(admission) != 216 or len(observer) != 41 or len(budget) != 36
            or len(abnormal) != 6 or len(compiler) != 36):
        raise AssertionError('negative integration coverage incomplete')
    return {
        'schema': SCHEMA, 'plan_sha256': identity_v0(),
        'plan_summary': summary_v0(),
        'source_manifest_count': len(manifests),
        'rejected_before_executor': sum(len(r['rejections']) for r in admission),
        'observer_callback_faults': sum(len(r['faults']) for r in observer),
        'observer_budget_corruptions': len(budget),
        'unrelated_runtime_abortions': len(abnormal),
        'compiler_source_rejections': len(compiler),
        'admission': admission, 'observer': observer,
        'budget_observer': budget, 'unrelated_runtime': abnormal,
        'compiler': compiler,
    }


def seal_v0():
    payload = report_v0()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) !=
            {'schema', 'payload', 'payload_sha256'} or
            obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('24v noncanonical evidence')
    payload = obj['payload']
    if sha(SCHEMA + '\n' + canonical(payload)) != obj['payload_sha256']:
        raise ValueError('24v evidence checksum mismatch')
    if report_v0() != payload:
        raise ValueError('24v evidence replay mismatch')
    return {
        'status': 'PASS', 'source_manifest_count': payload['source_manifest_count'],
        'rejected_before_executor': payload['rejected_before_executor'],
        'observer_callback_faults': payload['observer_callback_faults'],
        'observer_budget_corruptions': payload['observer_budget_corruptions'],
        'unrelated_runtime_abortions': payload['unrelated_runtime_abortions'],
        'compiler_source_rejections': payload['compiler_source_rejections'],
        'plan_sha256': payload['plan_sha256'],
        'evidence_sha256': sha(document),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        document = seal_v0()
        args.write.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
