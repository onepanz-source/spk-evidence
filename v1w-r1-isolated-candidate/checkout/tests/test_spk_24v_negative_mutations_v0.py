"""Pure mutation and fail-closed harness probes; requires no frozen dependencies."""
from dataclasses import dataclass

import pytest

from search.spk_24n_differential_evidence_v0 import sha
from search.spk_24v_negative_conformance_v0 import (
    ExecutorReachedV0, ObserverInjectedFaultV0,
    _assert_no_successful_receipt, _temporarily_replace, mutation_request_v0,
)
from search.spk_24v_negative_plan_v0 import MUTATIONS


@pytest.mark.parametrize('mutation', MUTATIONS)
def test_each_rejected_request_changes_one_specified_admission_boundary(mutation):
    original = '{"valid":"fixture"}'
    pin = sha(original)
    manifest, digest, kwargs = mutation_request_v0(original, pin, mutation)
    assert mutation in MUTATIONS
    assert isinstance(kwargs, dict)
    if mutation == 'wrong_pin':
        assert manifest == original and digest != pin and len(digest) == 64
    elif mutation == 'malformed_pin':
        assert manifest == original and digest == 'Z'*64
    elif mutation == 'zero_batches':
        assert manifest == original and kwargs['max_batches'] == 0
    elif mutation == 'boolean_events':
        assert kwargs['max_events'] is True
    elif mutation in ('truncated_manifest', 'wrong_root_shape'):
        assert manifest != original and digest == sha(manifest)
    elif mutation == 'nontext_manifest':
        assert manifest == 42


def test_unknown_mutation_is_rejected():
    with pytest.raises(ValueError, match='unknown negative mutation'):
        mutation_request_v0('valid', '0'*64, 'whatever')


def test_bad_input_types_are_rejected():
    with pytest.raises(TypeError):
        mutation_request_v0(42, '0'*64, 'wrong_pin')
    with pytest.raises(TypeError):
        mutation_request_v0('valid', None, 'wrong_pin')


def test_temporary_replacement_is_restored_even_on_exception():
    class Target:
        value = 'original'
    with pytest.raises(ObserverInjectedFaultV0):
        with _temporarily_replace(Target, 'value', 'poisoned'):
            assert Target.value == 'poisoned'
            raise ObserverInjectedFaultV0('abort')
    assert Target.value == 'original'


def test_single_shot_fault_never_returns_receipt():
    class Host:
        phase = 'NEW'
        def run(self):
            self.phase = 'FAILED'
            raise ObserverInjectedFaultV0('abort')
    assert _assert_no_successful_receipt(Host(), 'fixture',
                                        (ObserverInjectedFaultV0,)) == 'ObserverInjectedFaultV0'


def test_callback_fault_without_consuming_host_is_rejected():
    class Host:
        phase = 'NEW'
        def run(self):
            raise ObserverInjectedFaultV0('abort')
    with pytest.raises(AssertionError, match='did not consume'):
        _assert_no_successful_receipt(Host(), 'fixture',
                                      (ObserverInjectedFaultV0,))


def test_silent_success_on_poisoned_host_is_rejected():
    class Host:
        phase = 'CLOSED'
        def run(self):
            return '{"status":"CLOSED"}'
    with pytest.raises(AssertionError, match='returned a receipt'):
        _assert_no_successful_receipt(Host(), 'fixture',
                                      (ObserverInjectedFaultV0,))
