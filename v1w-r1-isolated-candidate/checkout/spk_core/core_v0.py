from __future__ import annotations

from .rules import (
    RULE_SPECS,
)


CORE_V0_SCHEMA = "spk-core-manifest/v0"
CORE_V0_VERSION = "0"

CORE_V0_IR_SHA256 = (
    "910ae1338a211257bee41c4d53ce55b78532a71ce23b3bd4d3d6a683455dce94"
)


def build_core_v0_manifest() -> dict:
    """
    Machine-readable semantic contract for SPK/Core v0.

    This manifest deliberately distinguishes:

    - declared language / runtime semantics;
    - rewrite classification;
    - finite validation baselines.

    Finite validation results are evidence for the declared corpus,
    not universal termination or confluence proofs.
    """

    rules = []

    for spec in RULE_SPECS:
        rules.append(
            {
                "rule_ids": list(
                    spec.rule_ids
                ),
                "helper": spec.helper,
                "validity": (
                    spec.validity.value
                ),
                "layer": (
                    spec.layer.value
                ),
                "domain_premise": (
                    None
                    if spec.domain_premise is None
                    else spec.domain_premise.value
                ),
            }
        )

    return {
        "schema": CORE_V0_SCHEMA,
        "core_version": CORE_V0_VERSION,

        "algebra": {
            "event_basis": [
                "MERGE",
                "DELAY",
            ],
            "state_basis": [
                "ACC",
                "DECAY",
                "CMP",
                "EMIT",
                "RESET",
            ],
            "combined_basis": [
                "MERGE",
                "DELAY",
                "ACC",
                "DECAY",
                "CMP",
                "EMIT",
                "RESET",
            ],
        },

        "isa": {
            "program": "CoreProgram",
            "config": {
                "type": "CoreConfig",
                "fields": [
                    "state_bits",
                    "fractional_bits",
                ],
            },
            "instructions": [
                "ShiftDecay",
                "CoreAcc",
                "CoreCmp",
                "CoreEmit",
                "CoreReset",
            ],
            "state": {
                "raw": "unsigned fixed-point integer",
                "guard": "transient boolean",
            },
        },

        "runtime": {
            "batching": (
                "all events sharing one timestamp "
                "form one batch"
            ),
            "shared_batch_delta": True,
            "shared_channel_counts": True,
            "initial_previous_timestamp": 0,
            "guard_resets_false_each_batch": True,
            "event_multiplicity_preserved": True,
            "overflow_is_observable": True,
            "observables": [
                "output",
                "final_raw",
                "final_guard",
                "last_timestamp",
            ],
        },

        "rewrite_system": {
            "runtime_class": "L",
            "domain_class": "D",
            "runtime_judgement": (
                "top |- lhs ==runtime rhs"
            ),
            "domain_judgement": (
                "Gamma_r |- lhs == rhs"
            ),
            "domain_default": "fail_closed",
            "domain_premise_kinds": [
                "source_defined",
                "target_defined",
                "both_defined",
                "abstract_bound",
            ],
            "rules": rules,
        },

        "canonicalization": {
            "runtime_profile": (
                "runtime rules only"
            ),
            "full_profile_without_evidence": (
                "domain rules remain disabled"
            ),
            "domain_activation": (
                "explicit verified evidence "
                "or explicit unchecked proof/search bypass"
            ),
        },

        "finite_validation": {
            "runtime_nf_depth5": {
                "max_depth": 5,
                "syntactic_programs": 19607,
                "distinct_runtime_normal_forms": 2499,
                "termination_failures": 0,
                "idempotence_failures": 0,
                "pass_cycles": 0,
                "fork_joinability_mismatches": 0,
                "residual_helper_edges": 0,
                "ir_v0_sha256": CORE_V0_IR_SHA256,
            },
            "claim_scope": (
                "finite depth<=5 declared corpus; "
                "not a universal termination or "
                "confluence proof"
            ),
        },

        "gates": [
            "search/core_phase3_final_gate_v0.sh",
            "search/core_domain_premises_final_gate_v0.sh",
        ],
    }
