"""Read-only, evidence-preserving validator for SPK Back Validation Contract v0.

This is NOT an optimizer, online backpropagation, or an A3d/A4c adapter.
Validation is structural/causal, NOT a proof that a local metric predicts global
utility. Callers must independently establish observation and metric provenance.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

SCHEMA = "spk-back-validation-trace/v0"
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class BVContractRejected(ValueError):
    pass


def _reject(message):
    raise BVContractRejected(message)


def _fields(obj, required, where):
    if type(obj) is not dict or set(obj) != set(required):
        _reject(f"{where}: expected exactly {', '.join(required)}")


def _ident(value, where):
    if type(value) is not str or not 1 <= len(value) <= 128 or not value.isascii() or not value.isprintable():
        _reject(f"{where}: invalid identifier")


def _digest(value, where):
    if type(value) is not str or _HEX.fullmatch(value) is None:
        _reject(f"{where}: expected lowercase SHA-256")


def _uint(value, where):
    if type(value) is not int or value < 0:
        _reject(f"{where}: expected nonnegative integer")


def _positive(value, where):
    if type(value) is not int or value < 1:
        _reject(f"{where}: expected positive integer")


def _bounded(value, where, minimum, maximum):
    if type(value) not in (float, int) or not math.isfinite(value) or not minimum <= value <= maximum:
        _reject(f"{where}: expected finite number in [{minimum},{maximum}]")


def _array(value, where):
    if type(value) is not list:
        _reject(f"{where}: expected array")


def _unique_map(records, where):
    table = {}
    for item in records:
        if type(item) is not dict or type(item.get("id")) is not str:
            _reject(f"{where}: record missing id")
        _ident(item["id"], where)
        if item["id"] in table:
            _reject(f"{where}: duplicate record id")
        table[item["id"]] = item
    return table


def canonical(obj):
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise BVContractRejected("noncanonical JSON value") from exc


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("ascii")).hexdigest()


def strict_loads(text):
    if type(text) is not str:
        _reject("JSON document must be text")

    def pairs(items):
        obj = {}
        for name, value in items:
            if name in obj:
                _reject(f"duplicate JSON field: {name}")
            obj[name] = value
        return obj

    def bad_constant(value):
        _reject(f"invalid JSON numeric literal: {value}")

    try:
        doc = json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, TypeError) as exc:
        raise BVContractRejected("invalid JSON document") from exc
    # Accept whitespace and pretty JSON, but never duplicate keys or NaN.
    return doc


def validate_trace(doc):
    _fields(doc, ("schema", "epoch", "topology_sha256", "budgets", "contexts", "edges",
                  "occurrences", "assessments", "propagations", "proposals"), "trace")
    if doc["schema"] != SCHEMA:
        _reject("unsupported contract schema")
    _uint(doc["epoch"], "epoch")
    _digest(doc["topology_sha256"], "topology_sha256")
    budget = doc["budgets"]
    _fields(budget, ("max_nodes", "max_edges", "max_contexts", "max_occurrences", "max_assessments", "max_propagations", "max_proposals", "max_hops", "max_parents"), "budgets")
    for key, val in budget.items():
        _positive(val, key)
    for group in ("contexts", "edges", "occurrences", "assessments", "propagations", "proposals"):
        _array(doc[group], group)
        if group != "contexts" and len(doc[group]) > budget["max_" + group]:
            _reject(f"{group}: budget exceeded")
    if not doc["contexts"]:
        _reject("empty context registry")
    if len(doc["contexts"]) > budget["max_contexts"]:
        _reject("context budget exceeded")
    contexts = _unique_map(doc["contexts"], "contexts")
    for c in doc["contexts"]:
        _fields(c, ("id", "node_id", "program_sha256", "features_sha256",
                    "extractor_sha256", "window_start", "window_end"), "context")
        _ident(c["node_id"], "node_id")
        for k in ("program_sha256", "features_sha256", "extractor_sha256"):
            _digest(c[k], k)
        _uint(c["window_start"], "window_start")
        _uint(c["window_end"], "window_end")
        if c["window_end"] < c["window_start"]:
            _reject("invalid context observation window")
    # Active neuron programs cannot change within one execution epoch.
    programs_by_node = {}
    for c in doc["contexts"]:
        if c["node_id"] in programs_by_node and programs_by_node[c["node_id"]] != c["program_sha256"]:
            _reject("active program changes within epoch")
        programs_by_node[c["node_id"]] = c["program_sha256"]
    known_nodes = set(programs_by_node)
    if len(known_nodes) > budget["max_nodes"]:
        _reject("node budget exceeded")
    edges = _unique_map(doc["edges"], "edges")
    for edge in doc["edges"]:
        _fields(edge, ("id", "source", "target", "source_channel", "target_channel", "delay_ticks"), "edge")
        if (type(edge["source"]) is not str or type(edge["target"]) is not str
                or edge["source"] not in known_nodes or edge["target"] not in known_nodes):
            _reject("topology edge references unknown node")
        for key in ("source_channel", "target_channel"):
            _uint(edge[key], key)
        _positive(edge["delay_ticks"], "delay_ticks")
    topology = {"nodes": sorted(known_nodes), "edges": sorted(doc["edges"], key=lambda x: x["id"])}
    if digest(topology) != doc["topology_sha256"]:
        _reject("topology digest does not match declared nodes and edges")
    occ = _unique_map(doc["occurrences"], "occurrences")
    for o in doc["occurrences"]:
        _fields(o, ("id", "source", "target", "emitted_at", "delivered_at",
                    "parent_ids", "source_program_sha256", "source_context_id", "edge_id",
                    "source_channel", "target_channel"), "occurrence")
        _ident(o["source"], "source")
        _ident(o["target"], "target")
        if type(o["source_context_id"]) is not str or o["source_context_id"] not in contexts:
            _reject("route uses unknown source context")
        owner = contexts[o["source_context_id"]]
        if owner["node_id"] != o["source"]:
            _reject("source context belongs to different node")
        if type(o["edge_id"]) is not str or o["edge_id"] not in edges:
            _reject("routed occurrence references unknown topology edge")
        edge = edges[o["edge_id"]]
        if (edge["source"] != o["source"] or edge["target"] != o["target"]
                or edge["source_channel"] != o["source_channel"]
                or edge["target_channel"] != o["target_channel"]):
            _reject("routed occurrence does not match declared topology edge")
        _uint(o["emitted_at"], "emitted_at")
        _uint(o["delivered_at"], "delivered_at")
        if o["delivered_at"] < o["emitted_at"] + edge["delay_ticks"]:
            _reject("delivery precedes edge minimum delay")
        if (o["source_program_sha256"] != owner["program_sha256"]
                or owner["window_end"] > o["emitted_at"]):
            _reject("source program/context window mismatch")
        _array(o["parent_ids"], "parent_ids")
        if any(type(x) is not str for x in o["parent_ids"]):
            _reject("invalid parent reference")
        if len(o["parent_ids"]) > budget["max_parents"]:
            _reject("parent-reference budget exceeded")
        if len(o["parent_ids"]) != len(set(o["parent_ids"])):
            _reject("duplicate causal parent")
        for pid in o["parent_ids"]:
            if type(pid) is not str or pid not in occ:
                _reject("unknown causal parent")
            parent = occ[pid]
            if parent["target"] != o["source"] or parent["delivered_at"] > o["emitted_at"]:
                _reject("parent occurrence not delivered to producer before emission")
    assessments = _unique_map(doc["assessments"], "assessments")
    for a in doc["assessments"]:
        _fields(a, ("id", "occurrence_id", "observer", "observed_at", "observer_context_id",
                    "metric_id", "metric_policy_sha256", "evidence_sha256", "status",
                    "value", "confidence", "reason"), "assessment")
        if type(a["occurrence_id"]) is not str or a["occurrence_id"] not in occ:
            _reject("assessment unknown event")
        o = occ[a["occurrence_id"]]
        if a["observer"] != o["target"]:
            _reject("feedback did not originate at destination")
        _uint(a["observed_at"], "observed_at")
        if a["observed_at"] < o["delivered_at"]:
            _reject("feedback generated before delivery")
        if type(a["observer_context_id"]) is not str or a["observer_context_id"] not in contexts:
            _reject("unknown assessment context")
        context = contexts[a["observer_context_id"]]
        if (context["node_id"] != a["observer"] or
                context["window_end"] > a["observed_at"]):
            _reject("observer context/window mismatch")
        _ident(a["metric_id"], "metric_id")
        _digest(a["metric_policy_sha256"], "metric_policy_sha256")
        _digest(a["evidence_sha256"], "evidence_sha256")
        if a["status"] == "OBSERVED":
            _bounded(a["value"], "value", -1, 1)
            _bounded(a["confidence"], "confidence", 0, 1)
            if a["reason"] is not None:
                _reject("observed assessment may not supply abstention reason")
        elif a["status"] == "ABSTAIN":
            if a["value"] is not None or a["confidence"] is not None:
                _reject("abstention must not be interpreted as score zero")
            _ident(a["reason"], "abstention reason")
        else:
            _reject("unrecognized assessment status")
    propagations = _unique_map(doc["propagations"], "propagations")
    routed_feedback = set()
    for p in doc["propagations"]:
        _fields(p, ("id", "assessment_id", "path"), "propagation")
        if type(p["assessment_id"]) is not str or p["assessment_id"] not in assessments:
            _reject("propagation refers to unknown assessment")
        _array(p["path"], "path")
        if not 2 <= len(p["path"]) <= budget["max_hops"]:
            _reject("propagation exceeds hop budget or lacks upstream step")
        if any(type(x) is not str for x in p["path"]):
            _reject("invalid propagation reference")
        if len(p["path"]) != len(set(p["path"])):
            _reject("causal propagation loops within path")
        if p["path"][0] != assessments[p["assessment_id"]]["occurrence_id"]:
            _reject("propagation not anchored to assessed event")
        for child_id, parent_id in zip(p["path"], p["path"][1:]):
            if child_id not in occ or parent_id not in occ[child_id]["parent_ids"]:
                _reject("propagation does not follow causal parents")
        # Deduplicate fan-in so one assessment does not count twice at an ancestor.
        target = (p["assessment_id"], p["path"][-1])
        if target in routed_feedback:
            _reject("duplicate assessment delivery to same ancestor")
        routed_feedback.add(target)
    # Paths are evidence, not independent votes. Multiple paths ending at the
    # same upstream node convey at most one assessment delivery to that node.
    propagation_receivers = {(p["assessment_id"], occ[p["path"][-1]]["source"])
                             for p in doc["propagations"]}
    direct_receivers = {(a["id"], occ[a["occurrence_id"]]["source"])
                        for a in doc["assessments"]}
    proposals = _unique_map(doc["proposals"], "proposals")
    for p in doc["proposals"]:
        _fields(p, ("id", "proposer", "from_program_sha256", "candidate_sha256",
                    "proposer_context_id", "assessment_ids", "propagation_ids", "status"), "proposal")
        if type(p["status"]) is not str or p["status"] != "STAGED_UNVERIFIED":
            _reject("v0 does not certify or promote candidates")
        if type(p["proposer_context_id"]) is not str or p["proposer_context_id"] not in contexts:
            _reject("unknown proposal context")
        pctx = contexts[p["proposer_context_id"]]
        if pctx["node_id"] != p["proposer"]:
            _reject("proposal context owner mismatch")
        _digest(p["candidate_sha256"], "candidate_sha256")
        if (p["from_program_sha256"] != pctx["program_sha256"]
                or p["candidate_sha256"] == p["from_program_sha256"]):
            _reject("proposal is stale, context-mismatched or unchanged")
        for key, registry in (("assessment_ids", assessments), ("propagation_ids", propagations)):
            _array(p[key], key)
            if any(type(x) is not str for x in p[key]):
                _reject("invalid proposal evidence reference")
            if len(p[key]) != len(set(p[key])):
                _reject("duplicate proposal evidence reference")
            for evidence_id in p[key]:
                if evidence_id not in registry:
                    _reject("proposal refers to unknown evidence")
                if key == "assessment_ids":
                    a = assessments[evidence_id]
                    if (a["status"] != "OBSERVED" or
                            occ[a["occurrence_id"]]["source"] != p["proposer"]):
                        _reject("proposal cites inaccessible or abstaining direct evidence")
                else:
                    route = propagations[evidence_id]
                    if occ[route["path"][-1]]["source"] != p["proposer"]:
                        _reject("proposal cites feedback not delivered to proposer")
    return {
        "status": "STRUCTURAL_PASS",
        "schema": SCHEMA,
        "epoch": doc["epoch"],
        "occurrences": len(occ),
        "assessments": len(assessments),
        "propagations": len(propagations),
        "unique_propagated_receivers": len(propagation_receivers),
        "unique_total_feedback_receivers": len(propagation_receivers | direct_receivers),
        "proposals": len(proposals),
        "trace_sha256": digest(doc),
        "claims_excluded": ("global-benefit", "causal-credit", "metric-truth", "learning", "promotion", "host-security"),
    }
