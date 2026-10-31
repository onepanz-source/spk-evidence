"""BV v0j: no native v0h producer available here; synthetic adapter checks only."""
from __future__ import annotations
import json
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys

import pytest

from spk_bv_research.native_bridge_v0j import (
    NativeBridgeError, NativeMapping, bridge_packet_ndjson, SCHEMA, read_manifest,
)
from spk_bv_research.pressure_v0j import pressure_report
from spk_bv_research.evidence_cost_v0i import (
    EvidenceCostContractError, BudgetProfile, EvidenceCostLedger, Reception,
)
from spk_bv_research.stress_v0i import fixture

FIELDS = tuple(Reception.__dataclass_fields__)


def manifest():
    return {"schema": SCHEMA,
            "source_label":"explicit-synthetic-native-test",
            "field_paths": {key: ["packet", key] for key in FIELDS},
            "cost_model":"native_positive_units",
            "assumptions":["one raw line is one physical observed feedback reception"]}


def native(*receipts):
    return [{"packet": r.as_dict(), "kind": "physical-feedback", "aux": 17} for r in receipts]


def read_native(tmp_path, records, spec=None, profile=None):
    path=tmp_path / "raw.ndjson"
    path.write_text("\n".join(json.dumps(x,sort_keys=True) for x in records)+"\n", encoding="utf-8")
    return bridge_packet_ndjson(path, NativeMapping.from_dict(spec or manifest()),profile=profile)


def r(**kwargs):
    base = dict(transmission_id="t1",epoch=1,observed_tick=2,batch_tick=1,
                origin="n0",batch_id="b1",receiver="n1",context_id="c1",
                evidence_code="opaque",link_id="L0",path_id="path1",transport_units=1)
    return Reception(**(base | kwargs))


def test_one_to_one_reconciliation_and_hashes(tmp_path):
    packets=native(r(),r(transmission_id="t2",path_id="path2"))
    snap=read_native(tmp_path,packets)
    assert snap["physical_transmissions"]==snap["native_bridge"]["source_packet_rows"]==2
    assert snap["distinct_contextual_votes"]==1
    assert snap["native_bridge"]["bijective_packet_mapping"] is True
    assert "v0h-independent-witness-equivalence" in snap["native_bridge"]["claims_excluded"]


def test_native_order_does_not_change_multiset_digest(tmp_path):
    packets=native(r(),r(transmission_id="t2",batch_id="b2"))
    a=read_native(tmp_path,packets)
    b=read_native(tmp_path,list(reversed(packets)))
    assert a["native_bridge"]["source_multiset_sha256"]==b["native_bridge"]["source_multiset_sha256"]
    assert a["native_bridge"]["source_ordered_sha256"]!=b["native_bridge"]["source_ordered_sha256"]
    assert a["physical_sha256"]==b["physical_sha256"]


def test_source_change_detected_even_if_mapping_unchanged(tmp_path):
    a=read_native(tmp_path,native(r()))
    doc=native(r()); doc[0]["aux"]=18
    b=read_native(tmp_path,doc)
    assert a["physical_sha256"]==b["physical_sha256"]
    assert a["native_bridge"]["source_multiset_sha256"]!=b["native_bridge"]["source_multiset_sha256"]


def test_distinct_batches_same_tick_not_collapsed(tmp_path):
    s=read_native(tmp_path,native(r(),r(transmission_id="t2",batch_id="b2")))
    assert s["distinct_contextual_votes"]==2


@pytest.mark.parametrize("wrong", [
    lambda x: x.pop("field_paths"),
    lambda x: x["field_paths"].pop("context_id"),
    lambda x: x["field_paths"].update({"origin": ["packet", "receiver"]}),
    lambda x: x["field_paths"].update({"receiver": "n2"}),
    lambda x: x.update({"cost_model": "unverified"}),
    lambda x: x.update({"assumptions": []}),
    lambda x: x.update({"schema": "wrong"}),
    lambda x: x.update({"source_label": ""}),
])
def test_manifest_fail_closed(wrong):
    m=manifest(); wrong(m)
    with pytest.raises(NativeBridgeError):
        NativeMapping.from_dict(m)


def test_explicit_uniform_unit_assumption(tmp_path):
    m=manifest(); m["cost_model"]="uniform_abstract_unit"
    m["field_paths"]["transport_units"]=1
    docs=native(r()); del docs[0]["packet"]["transport_units"]
    snap=read_native(tmp_path,docs,m)
    assert snap["transport_units"]==1
    assert snap["native_bridge"]["cost_model"]=="uniform_abstract_unit"


def test_uniform_unit_rejects_non_unit_literal():
    m=manifest(); m["cost_model"]="uniform_abstract_unit"
    m["field_paths"]["transport_units"]=2
    with pytest.raises(NativeBridgeError): NativeMapping.from_dict(m)


@pytest.mark.parametrize("mutate",[
    lambda a: a.append(deepcopy(a[0])),
    lambda a: a.append({"packet":(r(transmission_id="t1",context_id="c2")).as_dict()}),
    lambda a: a[0]["packet"].update({"observed_tick":0}),
    lambda a: a[0]["packet"].update({"batch_id":None}),
    lambda a: a[0]["packet"].pop("receiver"),
    lambda a: a[0].pop("packet"),
])
def test_reject_native_contradictions(tmp_path,mutate):
    docs=native(r()); mutate(docs)
    with pytest.raises(NativeBridgeError): read_native(tmp_path,docs)


def test_reject_native_vote_conflict(tmp_path):
    with pytest.raises(NativeBridgeError,match="conflicting"):
        read_native(tmp_path,native(r(),r(transmission_id="t2",evidence_code="opposite")))


def test_native_byte_bounded(tmp_path):
    path=tmp_path/"native.ndjson"; path.write_text(" "+"z"*1_000_001)
    with pytest.raises(NativeBridgeError,match="line exceeds"):
        bridge_packet_ndjson(path,NativeMapping.from_dict(manifest()))


def test_blank_row_fail_closed(tmp_path):
    path=tmp_path/"native.ndjson"; path.write_text("\n")
    with pytest.raises(NativeBridgeError,match="blank"):
        bridge_packet_ndjson(path,NativeMapping.from_dict(manifest()))


def test_duplicate_native_json_keys_rejected(tmp_path):
    path=tmp_path/"raw.ndjson"
    # duplicate key anywhere (including extra metadata) is ambiguous provenance
    raw=json.dumps(native(r())[0]); raw=raw[:-1]+',"aux":999}'
    path.write_text(raw+"\n")
    with pytest.raises(NativeBridgeError,match="duplicate JSON key"):
        bridge_packet_ndjson(path,NativeMapping.from_dict(manifest()))


def test_mapping_preserves_native_absolute_values(tmp_path):
    s=read_native(tmp_path,native(r(transport_units=7,observed_tick=99,batch_tick=98)))
    assert s["transport_units"]==7
    assert s["per_tick_units"]==[{"epoch":1,"tick":99,"units":7}]


def test_mapping_memory_limit(tmp_path):
    with pytest.raises(NativeBridgeError,match="transmission-memory"):
        read_native(tmp_path,native(r(),r(transmission_id="t2")),profile=BudgetProfile(max_transmissions=1))


def test_mapping_file_read(tmp_path):
    path=tmp_path/"mapping.json"; path.write_text(json.dumps(manifest()))
    assert read_manifest(path).source_label=="explicit-synthetic-native-test"


def test_bridge_cli_good_and_error_paths(tmp_path):
    mapping=tmp_path/"m.json"; mapping.write_text(json.dumps(manifest()))
    packets=tmp_path/"p.ndjson"; packets.write_text(json.dumps(native(r())[0])+"\n")
    cmd=[sys.executable,"-m","search.spk_bv_v0j_bridge_cli","--mapping",str(mapping),
         "--packets",str(packets),"--link-capacity","L0:1"]
    proc=subprocess.run(cmd, text=True,capture_output=True)
    assert proc.returncode==0,proc.stderr
    assert json.loads(proc.stdout)["pressure"]["transport_units"]==1
    bad=subprocess.run(cmd+["--link-capacity","L0:2"],text=True,capture_output=True)
    assert bad.returncode==2 and not bad.stdout


def test_pressure_capacity_and_backlog_exact():
    l=EvidenceCostLedger()
    l.ingest_all([r(transport_units=5),r(transmission_id="t2",observed_tick=3,transport_units=1),
                  r(transmission_id="t3",observed_tick=7,transport_units=4)])
    p=pressure_report(l.snapshot(),per_link_capacity={"L0":2},global_capacity=3)
    link=p["link_curves"][0]
    assert link["peak_end_of_tick_backlog_units"]==3
    assert link["peak_backlog_tick"]==2
    assert link["idealized_clear_tick"]==8
    assert link["arrival_units"]==10
    assert p["global_curves"][0]["capacity_units_per_tick"]==3


def test_pressure_empty_tick_gap_no_iterative_scan():
    l=EvidenceCostLedger()
    l.ingest_all([r(transport_units=9), r(transmission_id="t2",observed_tick=10**12,transport_units=1)])
    report=pressure_report(l.snapshot(),per_link_capacity={"L0":3})
    assert report["link_curves"][0]["idealized_clear_tick"]==10**12


def test_pressure_epoch_custody_isolated():
    l=EvidenceCostLedger(); l.ingest_all([r(transport_units=4),r(epoch=2,transport_units=4)])
    p=pressure_report(l.snapshot(),per_link_capacity={"L0":1})
    assert len(p["link_curves"])==2
    assert all(x["peak_end_of_tick_backlog_units"]==3 for x in p["link_curves"])


def test_pressure_link_isolation():
    l=EvidenceCostLedger(); l.ingest_all([r(transport_units=5),r(transmission_id="t2",link_id="L1",transport_units=5)])
    p=pressure_report(l.snapshot(),per_link_capacity={"L0":3,"L1":10})
    assert [x["peak_end_of_tick_backlog_units"] for x in p["link_curves"]]==[2,0]


def test_pressure_budget_never_deletes_or_schedules():
    l=EvidenceCostLedger(); l.ingest(r(transport_units=10))
    before=l.snapshot(); p=pressure_report(before,per_link_capacity={"L0":1})
    assert l.snapshot()==before and p["transport_units"]==10
    assert "scheduling-equivalence" in p["excluded_claims"]


@pytest.mark.parametrize("cap",[0,-1,1.0,True,None])
def test_pressure_wrong_link_capacity(cap):
    l=EvidenceCostLedger(); l.ingest(r())
    with pytest.raises(EvidenceCostContractError):
        pressure_report(l.snapshot(),per_link_capacity={"L0":cap})


def test_pressure_missing_link_capacity():
    l=EvidenceCostLedger(); l.ingest(r())
    with pytest.raises(EvidenceCostContractError,match="missing capacity"):
        pressure_report(l.snapshot(),per_link_capacity={})


def test_pressure_tamper_total_detected():
    l=EvidenceCostLedger(); l.ingest(r())
    data=l.snapshot(); data["transport_units"]=100
    with pytest.raises(EvidenceCostContractError,match="disagree"):
        pressure_report(data,per_link_capacity={"L0":1})


def test_source_probe_does_not_execute_files(tmp_path):
    import importlib.util
    root=tmp_path; directory=root/"search"; directory.mkdir()
    file=directory/"spk_bv_v0h_malicious.py"
    target=root/"would-exist"
    file.write_text(f"from pathlib import Path\nPath({str(target)!r}).write_text('bad')\n"
                    "class ContextualReception:\n    context_id: str\n"
                    "def feedback_witness(batch_id):\n    return {'batch_id':batch_id}\n")
    proc=subprocess.run([sys.executable,"-m","search.spk_bv_v0j_probe","--root",str(root),"--compact"],
                        text=True,capture_output=True)
    assert proc.returncode==0 and not target.exists()
    data=json.loads(proc.stdout)
    assert data["files_scanned"]==1
    assert data["files"][0]["classes"][0]["name"]=="ContextualReception"
    assert data["files"][0]["functions"][0]["name"]=="feedback_witness"


def test_hashseed_witness_independent():
    cmd=[sys.executable,"-m","search.spk_bv_v0j_witness"]
    p=subprocess.run(cmd,capture_output=True,text=True,env=os.environ|{"PYTHONHASHSEED":"12"})
    q=subprocess.run(cmd,capture_output=True,text=True,env=os.environ|{"PYTHONHASHSEED":"100"})
    assert p.returncode==q.returncode==0,(p.stderr,q.stderr)
    assert p.stdout==q.stdout
    assert json.loads(p.stdout)["native_v0h_verified"] is False


def test_empty_native_trace_rejected(tmp_path):
    empty=tmp_path/"empty.ndjson"; empty.write_text("")
    with pytest.raises(NativeBridgeError,match="empty native"):
        bridge_packet_ndjson(empty,NativeMapping.from_dict(manifest()))


def test_duplicate_manifest_keys_rejected(tmp_path):
    path=tmp_path/"mapping.json"
    data=json.dumps(manifest())
    path.write_text(data[:-1]+',"cost_model":"native_positive_units"}')
    with pytest.raises(NativeBridgeError,match="duplicate JSON key"):
        read_manifest(path)


def test_pressure_tamper_per_tick_detected():
    l=EvidenceCostLedger(); l.ingest(r())
    data=l.snapshot(); data["per_tick_units"][0]["units"]=99
    with pytest.raises(EvidenceCostContractError,match="per-tick totals disagree"):
        pressure_report(data,per_link_capacity={"L0":1})
