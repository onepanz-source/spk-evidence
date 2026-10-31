"""v1v provenance-denial contract hotfix: never weaken original custody."""
from pathlib import Path
import pytest
import re
from spk_native_learning_v1 import sensed_context_v1v as sensed


def _raise(message):
    raise AssertionError(message)


def test_original_identity_mismatch_typed_and_chained(monkeypatch,tmp_path):
    monkeypatch.setattr(sensed,'pin_sources',lambda root: _raise('FROZEN_PE_COMPUTATION_IDENTITY_MISMATCH'))
    with pytest.raises(sensed.SensorReject,match='^ORIGINAL_PE_PROVENANCE_DENIED$') as e:
        sensed._source_check(tmp_path)
    assert isinstance(e.value.__cause__, AssertionError)
    assert str(e.value.__cause__) == 'FROZEN_PE_COMPUTATION_IDENTITY_MISMATCH'
    assert not (tmp_path/'x.db').exists()


@pytest.mark.parametrize('message',[
    'FROZEN_MISSING:spk_architecture_v1/pe_execution_v1b.py',
    'FROZEN_DRIFT:spk_architecture_v1/pe_execution_v1b.py',
    'FROZEN_MEMORY_ADMISSION_IDENTITY_MISMATCH',
    'FROZEN_LOADED_MODULE_MISMATCH:spk_architecture_v1/pe_execution_v1b.py',
    'FROZEN_PE_COMPUTATION_IDENTITY_MISMATCH:unexpected_extension',
])
def test_unrelated_custody_assertion_is_not_swallowed(monkeypatch,tmp_path,message):
    monkeypatch.setattr(sensed,'pin_sources',lambda root: _raise(message))
    with pytest.raises(AssertionError,match='^'+re.escape(message)+'$'):
        sensed._source_check(tmp_path)


def test_unexpected_runtime_error_propagates(monkeypatch,tmp_path):
    def faulty(_):
        raise RuntimeError('PIN_CHECK_IMPLEMENTATION_ERROR')
    monkeypatch.setattr(sensed,'pin_sources',faulty)
    with pytest.raises(RuntimeError,match='PIN_CHECK_IMPLEMENTATION_ERROR'):
        sensed._source_check(tmp_path)


def test_original_import_identity_check_still_active(monkeypatch,tmp_path):
    from spk_native_learning_v1 import generalized_scheduler_v1t as runtime
    from spk_architecture_v1 import pe_execution_v1b as frozen
    monkeypatch.setattr(sensed,'pin_sources',lambda root: {sensed.SOURCE_REL:'pinned'})
    monkeypatch.setattr(runtime,'_compute_local',lambda *args: (0,False,()))
    with pytest.raises(sensed.SensorReject,match='^ORIGINAL_PE_PROVENANCE_DENIED$'):
        sensed._source_check(tmp_path)


def test_manifest_uses_patched_source_hash():
    import hashlib,json
    p=Path(sensed.__file__).resolve()
    manifest=json.loads((p.parent/'sensed_context_manifest_v1v.json').read_text())
    assert manifest['files']['spk_native_learning_v1/sensed_context_v1v.py']==hashlib.sha256(p.read_bytes()).hexdigest()
