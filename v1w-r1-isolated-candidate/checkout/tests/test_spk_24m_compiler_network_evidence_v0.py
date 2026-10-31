"""24m contract tests: frozen compiler -> routed Network -> observer -> replay."""
from dataclasses import replace
from hashlib import sha256
import json

import pytest

from spk_compiler.network_ir_v0 import dumps_network_ir_v0
from spk_compiler.compilation_manifest_v0 import loads_compilation_manifest_v0
from spk_network.events_v0 import NetworkEventV0
from spk_network.runtime_v0 import NetworkExecutionLimitV0, run_network_v0
from spk_core.isa import CoreAcc, CoreProgram
from spk_network.model_v0 import NetworkNodeV0, NetworkV0
from search.spk_24m_compiler_network_evidence_v0 import (
    SCHEMA, _canonical, _json_tree, _payload, compile_and_run_v0,
    reference_scenario_v0, verify_and_replay_v0,
)


def sample():
    return compile_and_run_v0(**reference_scenario_v0())


def reseal(document, change):
    data = json.loads(document)
    change(data)
    data["payload_sha256"] = sha256(
        (SCHEMA + "\n" + _canonical(data["payload"])).encode()
    ).hexdigest()
    return _canonical(data)


def test_canonical_wire_projection_of_nested_runtime_tuples():
    # dataclasses.asdict preserves tuple-valued fields. JSON does not.
    from dataclasses import asdict, dataclass

    @dataclass(frozen=True)
    class Observation:
        channels: tuple[int, ...]
        nested: tuple[tuple[int, ...], ...]

    native = asdict(Observation((0, 0), ((2, 3), (5,))))
    assert native["channels"] == (0, 0)
    assert _json_tree(native) == {
        "channels": [0, 0], "nested": [[2, 3], [5]],
    }


def test_replayed_payload_compares_in_json_domain():
    # This failed in the original 24m: native tuple fields did not compare
    # equal to the JSON arrays that were actually sealed in the receipt.
    receipt = json.loads(sample())["payload"]
    regenerated = _payload(
        receipt["manifest_json"], receipt["max_batches"],
        receipt["max_events"],
    )
    assert regenerated == receipt
    assert regenerated == json.loads(_canonical(regenerated))


def expected_emission(time, node):
    return {"timestamp": time, "node_id": node, "channel": 7}


def test_real_source_to_compiler_to_runtime_result_oracle():
    p = verify_and_replay_v0(sample())
    result = p["result"]
    assert result["processed_events"] == 4
    assert result["processed_batches"] == 3
    assert result["emissions"] == [
        expected_emission(2, "A"), expected_emission(4, "B"),
        expected_emission(5, "B"),
    ]
    assert result["terminal_outputs"] == [
        expected_emission(4, "B"), expected_emission(5, "B"),
    ]


def test_explicit_observer_route_oracle_with_parallel_multiplicity():
    observations = verify_and_replay_v0(sample())["observations"]
    routes = observations["routes"]
    assert len(routes) == 3
    expected = [
        (2, "A", 7, 4, "B", 0, 2),
        (2, "A", 7, 4, "B", 0, 2),
        (2, "A", 7, 5, "B", 0, 3),
    ]
    actual = [tuple(x[k] for k in (
        "emission_timestamp", "source_node", "source_channel",
        "delivery_timestamp", "target_node", "target_channel", "delay_ticks",
    )) for x in routes]
    assert sorted(actual) == sorted(expected)


def test_observer_batch_oracle():
    batches = verify_and_replay_v0(sample())["observations"]["batches"]
    assert [(x["timestamp"], x["node_id"], x["channels"]) for x in batches] == [
        (2, "A", [0]), (4, "B", [0, 0]), (5, "B", [0]),
    ]


def test_compiler_manifest_embedded_and_roundtrips():
    p = verify_and_replay_v0(sample())
    m = loads_compilation_manifest_v0(p["manifest_json"])
    assert len(m.network.nodes) == 2
    assert len(m.network.edges) == 3
    assert m.initial_events == (NetworkEventV0(2, "A", 0),)


def test_full_source_result_equals_reconstructed_result():
    p = verify_and_replay_v0(sample())
    scenario = reference_scenario_v0()
    from spk_compiler.network_ir_v0 import loads_network_ir_v0
    raw = run_network_v0(
        loads_network_ir_v0(scenario["network_ir_json"]),
        scenario["initial_events"], max_batches=32, max_events=128,
    )
    from dataclasses import asdict
    assert _json_tree(asdict(raw)) == p["result"]


def test_evidence_canonical_and_repeatable():
    first = sample()
    assert first == sample()
    assert first == _canonical(json.loads(first))


def test_manifest_digest_is_correct():
    p = verify_and_replay_v0(sample())
    assert p["manifest_sha256"] == sha256(p["manifest_json"].encode()).hexdigest()


def test_pretty_declarative_source_yields_same_evidence():
    scenario = reference_scenario_v0()
    scenario["network_ir_json"] = json.dumps(
        json.loads(scenario["network_ir_json"]), indent=3,
    )
    assert compile_and_run_v0(**scenario) == sample()


def test_permuted_placement_order_yields_same_evidence():
    scenario = reference_scenario_v0()
    scenario["placements"] = scenario["placements"][::-1]
    assert compile_and_run_v0(**scenario) == sample()


def test_empty_event_case_is_supported():
    scenario = reference_scenario_v0()
    scenario["initial_events"] = ()
    p = verify_and_replay_v0(compile_and_run_v0(**scenario))
    assert p["result"]["processed_events"] == 0
    assert p["result"]["emissions"] == []
    assert p["observations"] == {"batches": [], "routes": []}


def test_duplicate_initial_events_keep_multiplicity():
    scenario = reference_scenario_v0()
    scenario["initial_events"] *= 2
    p = verify_and_replay_v0(compile_and_run_v0(**scenario))
    assert len(loads_compilation_manifest_v0(p["manifest_json"]).initial_events) == 2
    assert p["result"]["processed_events"] == 5
    assert p["observations"]["batches"][0]["channels"] == [0, 0]


def test_non_emitting_network_supported():
    scenario = reference_scenario_v0()
    from spk_compiler.network_ir_v0 import loads_network_ir_v0
    old = loads_network_ir_v0(scenario["network_ir_json"])
    bare = NetworkV0(nodes=tuple(NetworkNodeV0(
        node.node_id, node.config, CoreProgram((CoreAcc(1, 0),))
    ) for node in old.nodes), edges=())
    scenario["network_ir_json"] = dumps_network_ir_v0(bare)
    p = verify_and_replay_v0(compile_and_run_v0(**scenario))
    assert p["result"]["emissions"] == []
    assert p["observations"]["routes"] == []


@pytest.mark.parametrize("name,invalid", [
    ("max_batches", 0), ("max_batches", True),
    ("max_events", -1), ("max_events", 1.5),
    ("max_events", None),
])
def test_invalid_budgets_fail_closed(name, invalid):
    with pytest.raises(ValueError, match="positive integer"):
        compile_and_run_v0(**reference_scenario_v0(), **{name: invalid})


@pytest.mark.parametrize("name,limit", [("max_events", 3), ("max_batches", 2)])
def test_finite_limits_enforced(name, limit):
    with pytest.raises(NetworkExecutionLimitV0):
        compile_and_run_v0(**reference_scenario_v0(), **{name: limit})


def test_invalid_declarative_source_rejected_by_frozen_compiler():
    scenario = reference_scenario_v0()
    ir = json.loads(scenario["network_ir_json"])
    ir["network_version"] = "999"
    scenario["network_ir_json"] = _canonical(ir)
    with pytest.raises(ValueError):
        compile_and_run_v0(**scenario)


@pytest.mark.parametrize("key,value", [
    ("schema", "other"), ("version", "1"),
])
def test_wrong_evidence_header_rejected(key, value):
    bad = json.loads(sample())
    bad[key] = value
    with pytest.raises(ValueError, match="schema/version"):
        verify_and_replay_v0(_canonical(bad))


def test_duplicate_envelope_key_rejected():
    doc = sample()
    with pytest.raises(ValueError, match="duplicate JSON key"):
        verify_and_replay_v0(doc[:-1] + ',"schema":"duplicate"}')


def test_nonfinite_constant_rejected():
    doc = sample()
    with pytest.raises(ValueError, match="invalid JSON constant"):
        verify_and_replay_v0(doc[:-1] + ',"unknown":NaN}')


def test_noncanonical_payload_rejected():
    with pytest.raises(ValueError, match="canonical"):
        verify_and_replay_v0(json.dumps(json.loads(sample()), indent=2))


def test_bad_envelope_checksum_rejected():
    env = json.loads(sample())
    env["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        verify_and_replay_v0(_canonical(env))


def test_bad_manifest_digest_rejected_even_after_resealing():
    with pytest.raises(ValueError, match="manifest digest"):
        verify_and_replay_v0(reseal(sample(), lambda d:
            d["payload"].update(manifest_sha256="0" * 64)))


@pytest.mark.parametrize("field,mutator", [
    ("result", lambda p: p["result"].update(processed_events=99)),
    ("emission", lambda p: p["result"]["emissions"].pop()),
    ("state", lambda p: p["result"]["states"].clear()),
    ("batch", lambda p: p["observations"]["batches"].pop()),
    ("route", lambda p: p["observations"]["routes"].pop()),
    ("route_delay", lambda p: p["observations"]["routes"][0].update(delay_ticks=99)),
])
def test_rehashed_forged_receipts_rejected_by_real_replay(field, mutator):
    def alter(d):
        mutator(d["payload"])
    with pytest.raises(ValueError, match="replay evidence mismatch"):
        verify_and_replay_v0(reseal(sample(), alter))


@pytest.mark.parametrize("where", ["top", "payload"])
def test_unknown_fields_rejected(where):
    def alter(d):
        if where == "top":
            d["extraneous"] = 1
        else:
            d["payload"]["extraneous"] = 1
    with pytest.raises(ValueError, match="fields"):
        verify_and_replay_v0(reseal(sample(), alter))


def test_tampered_compiler_manifest_rejected_even_when_outer_hash_recomputed():
    def alter(d):
        inner = json.loads(d["payload"]["manifest_json"])
        inner["payload"]["network_ir"]["edges"][0]["delay_ticks"] = 0
        new_manifest = _canonical(inner)
        d["payload"]["manifest_json"] = new_manifest
        d["payload"]["manifest_sha256"] = sha256(new_manifest.encode()).hexdigest()
    with pytest.raises(ValueError):
        verify_and_replay_v0(reseal(sample(), alter))


def test_plain_text_is_not_a_valid_receipt():
    with pytest.raises((ValueError, json.JSONDecodeError)):
        verify_and_replay_v0("CLOSED")


def test_none_is_not_a_valid_receipt():
    with pytest.raises(TypeError):
        verify_and_replay_v0(None)


def test_observer_full_result_divergence_rejected(monkeypatch):
    from search import spk_24m_compiler_network_evidence_v0 as module
    actual = module.run_network_v0

    def divergent_runtime(*args, **kwargs):
        result = actual(*args, **kwargs)
        if kwargs.get("learning_observer") is not None:
            return replace(result, processed_events=result.processed_events + 1)
        return result

    monkeypatch.setattr(module, "run_network_v0", divergent_runtime)
    with pytest.raises(ValueError, match="observer changed"):
        module.compile_and_run_v0(**reference_scenario_v0())
