"""Offline, read-only contextual credit *evidence* experiment.

This module evaluates externally supplied, structurally paired simulator rollouts.
It DOES NOT capture causal reality, generate neural programs, learn, authorize,
or promote a change. The independent simulator capture and reset are future work.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

from spk_backvalidation_v0.contract_v0 import digest

SCHEMA = "spk-bv-contextual-credit/v0a"
_BASELINE_TAG = "spk-architecture-bounded-reference-v1"
_BASELINE_COMMIT = "5af99cd1f4d603bf0c8e1557a6561c107765fdb5"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
COST_FIELDS = ("operations", "memory_accesses", "spike_messages", "feedback_messages", "candidate_eval_operations")

class CreditEvidenceRejected(ValueError):
    pass


def deny(message):
    raise CreditEvidenceRejected(message)


def exact(obj, fields, label):
    if type(obj) is not dict or set(obj) != set(fields):
        deny(f"{label}: incorrect fields")


def ident(s, label):
    if type(s) is not str or _ID.fullmatch(s) is None:
        deny(f"{label}: invalid identifier")


def sha(s, label):
    if type(s) is not str or _DIGEST.fullmatch(s) is None:
        deny(f"{label}: invalid digest")


def number(x, label, low=None, high=None):
    if type(x) not in (int, float) or not math.isfinite(x):
        deny(f"{label}: non-finite or invalid numeric value")
    if low is not None and x < low or high is not None and x > high:
        deny(f"{label}: out of bounds")


def integer(x, label, low=0):
    if type(x) is not int or x < low:
        deny(f"{label}: invalid integer")


def array(a, label):
    if type(a) is not list:
        deny(f"{label}: expected array")


def unique_mapping(values, label):
    array(values, label)
    table = {}
    for v in values:
        if type(v) is not dict:
            deny(f"{label}: invalid record")
        ident(v.get("id"), f"{label}.id")
        if v["id"] in table:
            deny(f"{label}: duplicate id")
        table[v["id"]] = v
    return table


def weighted_cost(cost, weights, max_cost):
    exact(cost, COST_FIELDS, "cost")
    for k in COST_FIELDS:
        integer(cost[k], f"cost.{k}")
    total = sum(cost[k] * weights[k] for k in COST_FIELDS)
    if not math.isfinite(total) or total > max_cost:
        deny("weighted resource cost exceeds budget")
    return total


def validate_feedback(items, max_receivers):
    array(items, "feedback")
    if len(items) > max_receivers:
        deny("feedback receiver budget exceeded")
    result = {}
    for item in items:
        exact(item, ("observer", "status", "score", "reason"), "feedback record")
        obs = item["observer"]
        ident(obs, "feedback observer")
        if obs in result:
            deny("duplicate feedback receiver is not an independent vote")
        if item["status"] == "OBSERVED":
            number(item["score"], "feedback score", -1, 1)
            if item["reason"] is not None:
                deny("observed feedback cannot carry abstention reason")
            result[obs] = item["score"]
        elif item["status"] == "ABSTAIN":
            if item["score"] is not None:
                deny("abstention cannot be numeric zero")
            ident(item["reason"], "abstention reason")
            result[obs] = None
        else:
            deny("unrecognized feedback status")
    return result


def exact_sign_pvalue(positive, negative):
    """Two-sided exact binomial sign diagnostic; ties excluded.

    Interpretable statistically only if trial pairs are independently sampled
    and registered before observations. This verifier does not attest that.
    """
    n = positive + negative
    if n == 0:
        return None
    k = min(positive, negative)
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def direction(deltas, minimum_pairs, alpha, min_gain):
    if len(deltas) < minimum_pairs:
        return "UNAVAILABLE", None, None
    mean = sum(deltas) / len(deltas)
    pos = sum(d > 0 for d in deltas)
    neg = sum(d < 0 for d in deltas)
    pvalue = exact_sign_pvalue(pos, neg)
    if pvalue is not None and pvalue <= alpha:
        if mean >= min_gain:
            return "POSITIVE", mean, pvalue
        if mean <= -min_gain:
            return "NEGATIVE", mean, pvalue
    return "INCONCLUSIVE", mean, pvalue


def evaluate_credit(doc):
    """Validate and summarize pre-paired external trials. No mutations."""
    exact(doc, ("schema", "baseline_tag", "baseline_commit", "topology_sha256", "policy", "program", "contexts", "trial_pairs"), "report")
    if (doc["schema"] != SCHEMA or doc["baseline_tag"] != _BASELINE_TAG
            or doc["baseline_commit"] != _BASELINE_COMMIT):
        deny("unsupported schema or frozen baseline pin")
    sha(doc["topology_sha256"], "topology")
    p = doc["policy"]
    exact(p, ("global_metric_id", "global_metric_policy_sha256", "local_metric_id",
              "local_metric_policy_sha256", "minimum_pairs", "alpha_ppm", "minimum_mean_gain",
              "max_mean_extra_cost", "max_pairs", "max_receivers", "max_cost_per_arm", "cost_weights"), "policy")
    for k in ("global_metric_id", "local_metric_id"):
        ident(p[k], k)
    for k in ("global_metric_policy_sha256", "local_metric_policy_sha256"):
        sha(p[k], k)
    integer(p["minimum_pairs"], "minimum_pairs", 8)
    integer(p["alpha_ppm"], "alpha_ppm", 1)
    if p["alpha_ppm"] > 100000:
        deny("alpha_ppm > 0.1")
    number(p["minimum_mean_gain"], "minimum_mean_gain", 0.000001, 2)
    number(p["max_mean_extra_cost"], "max_mean_extra_cost", 0)
    integer(p["max_pairs"], "max_pairs", 1)
    integer(p["max_receivers"], "max_receivers", 1)
    number(p["max_cost_per_arm"], "max_cost_per_arm", 0)
    exact(p["cost_weights"], COST_FIELDS, "cost_weights")
    for k in COST_FIELDS:
        number(p["cost_weights"][k], f"cost_weights.{k}", 0)
    if not any(p["cost_weights"].values()):
        deny("all cost weights zero")
    program = doc["program"]
    exact(program, ("node_id", "baseline_sha256", "candidate_sha256"), "program")
    ident(program["node_id"], "program.node_id")
    sha(program["baseline_sha256"], "baseline program")
    sha(program["candidate_sha256"], "candidate program")
    if program["baseline_sha256"] == program["candidate_sha256"]:
        deny("candidate program is unchanged")
    contexts = unique_mapping(doc["contexts"], "contexts")
    if not contexts:
        deny("no contexts")
    for c in contexts.values():
        exact(c, ("id", "pre_treatment_features_sha256", "extractor_sha256"), "context")
        sha(c["pre_treatment_features_sha256"], "pre-treatment features")
        sha(c["extractor_sha256"], "extractor")
    pairmap = unique_mapping(doc["trial_pairs"], "trial_pairs")
    if not pairmap or len(pairmap) > p["max_pairs"]:
        deny("trial-pair budget exhausted or empty")
    by_context = defaultdict(list)
    seen_seeds = set()
    seen_traces = set()
    for pair in doc["trial_pairs"]:
        exact(pair, ("id", "context_id", "seed", "initial_state_sha256", "input_sha256",
                     "baseline", "candidate"), "trial pair")
        ctx = pair["context_id"]
        if type(ctx) is not str or ctx not in contexts:
            deny("unknown pre-treatment context")
        integer(pair["seed"], "trial seed")
        key = (ctx, pair["seed"])
        if key in seen_seeds:
            deny("repeated seed is not an independent trial")
        seen_seeds.add(key)
        sha(pair["initial_state_sha256"], "initial state")
        sha(pair["input_sha256"], "input")
        arms = {}
        for name, expected in (("baseline", program["baseline_sha256"]), ("candidate", program["candidate_sha256"])):
            arm = pair[name]
            exact(arm, ("program_sha256", "trace_sha256", "global_score", "feedback", "cost"), name)
            sha(arm["trace_sha256"], "trace evidence")
            if arm["trace_sha256"] in seen_traces:
                deny("trace evidence reused across trials or arms")
            seen_traces.add(arm["trace_sha256"])
            if arm["program_sha256"] != expected:
                deny("program identity mismatch")
            if arm["global_score"] is not None:
                number(arm["global_score"], "global score", -1, 1)
            feedback = validate_feedback(arm["feedback"], p["max_receivers"])
            cost = weighted_cost(arm["cost"], p["cost_weights"], p["max_cost_per_arm"])
            arms[name] = (arm["global_score"], feedback, cost)
        if pair["baseline"]["trace_sha256"] == pair["candidate"]["trace_sha256"]:
            deny("distinct interventions reuse a single trace digest")
        by_context[ctx].append(arms)
    alpha = p["alpha_ppm"] / 1_000_000
    rows = []
    for ctx in sorted(contexts):
        trials = by_context.get(ctx, [])
        global_delta, local_delta, extra_cost = [], [], []
        pairs_local_complete, pairs_global_complete = 0, 0
        for arms in trials:
            old, new = arms["baseline"], arms["candidate"]
            extra_cost.append(new[2] - old[2])
            if old[0] is not None and new[0] is not None:
                global_delta.append(new[0] - old[0])
                pairs_global_complete += 1
            receivers = set(old[1]) | set(new[1])
            complete = [new[1][j] - old[1][j] for j in receivers
                        if j in old[1] and j in new[1]
                        and old[1][j] is not None and new[1][j] is not None]
            # Descriptive per-trial majority SIGN, never pool raw scores from
            # potentially uncalibrated observers or count paths as votes.
            if complete:
                positive = sum(d > 0 for d in complete)
                negative = sum(d < 0 for d in complete)
                local_delta.append((positive > negative) - (negative > positive))
                pairs_local_complete += 1
        gd, gm, gp = direction(global_delta, p["minimum_pairs"], alpha, p["minimum_mean_gain"])
        ld, lm, lp = direction(local_delta, p["minimum_pairs"], alpha, 0.000001)
        cost_delta = sum(extra_cost) / len(extra_cost) if extra_cost else None
        if gd == "UNAVAILABLE":
            decision = "GLOBAL_UNAVAILABLE"
        elif gd == "NEGATIVE" and ld == "POSITIVE":
            decision = "LOCAL_GLOBAL_CONFLICT"
        elif gd == "NEGATIVE":
            decision = "GLOBAL_REGRESSION"
        elif gd == "POSITIVE" and cost_delta > p["max_mean_extra_cost"] + 1e-9:
            decision = "COST_BLOCKED"
        elif gd == "POSITIVE":
            decision = "EVIDENCE_FOR_FURTHER_VERIFICATION"
        else:
            decision = "INCONCLUSIVE"
        rows.append({
            "context_id": ctx, "pairs": len(trials),
            "global_complete": pairs_global_complete, "local_complete": pairs_local_complete,
            "global_direction": gd, "local_direction": ld,
            "mean_global_delta": round(gm, 9) if gm is not None else None,
            "mean_local_majority_sign": round(lm, 9) if lm is not None else None,
            "global_sign_pvalue": round(gp, 12) if gp is not None else None,
            "local_sign_pvalue": round(lp, 12) if lp is not None else None,
            "mean_extra_weighted_cost": round(cost_delta, 9) if cost_delta is not None else None,
            "decision": decision,
        })
    return {
        "status": "OFFLINE_PAIRED_EVIDENCE_ONLY",
        "schema": SCHEMA,
        "baseline_commit": _BASELINE_COMMIT,
        "trial_pairs": len(pairmap),
        "context_results": rows,
        "report_sha256": digest(doc),
        "excluded_claims": ("causal-transport-authenticity", "randomization-attested", "global-generalization",
                            "independent-trials-attested", "learning", "promotion", "hardware-energy"),
    }
