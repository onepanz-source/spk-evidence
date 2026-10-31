from __future__ import annotations

from spk_core.core_v0 import (
    CORE_V0_IR_SHA256,
    CORE_V0_VERSION,
)

from .model_v0 import (
    NETWORK_V0_VERSION,
)


NETWORK_V0_SCHEMA = (
    "spk-network-manifest/v0"
)


def build_network_v0_manifest() -> dict:
    """
    Frozen SPK/Network v0 semantic contract.

    Network v0 composes frozen Core v0 programs.
    Learning callbacks are observational only and define
    no learning/update semantics.
    """

    return {
        "schema": NETWORK_V0_SCHEMA,
        "network_version": (
            NETWORK_V0_VERSION
        ),

        "core_dependency": {
            "core_version": (
                CORE_V0_VERSION
            ),
            "core_ir_sha256": (
                CORE_V0_IR_SHA256
            ),
        },

        "composition": {
            "node_type": "NetworkNodeV0",
            "edge_type": "NetworkEdgeV0",
            "core_program_requires_runtime_nf": True,
            "parallel_edges_preserve_multiplicity": True,
            "structural_cycles_allowed": True,
            "edge_delay_ticks_positive": True,
        },

        "events": {
            "event_type": "NetworkEventV0",
            "batch_type": "NetworkBatchV0",
            "batch_key": [
                "timestamp",
                "node_id",
            ],
            "multiplicity_preserved": True,
            "canonical_channel_order": True,
        },

        "runtime": {
            "entry_point": "run_network_v0",
            "persistent_node_state": [
                "raw",
                "last_timestamp",
            ],
            "guard_transient_per_batch": True,
            "routing_is_strictly_causal": True,
            "execution_limits": [
                "max_batches",
                "max_events",
            ],
        },

        "learning_interface": {
            "observer_type": (
                "NetworkLearningObserverV0"
            ),
            "route_observation": (
                "NetworkRouteObservationV0"
            ),
            "batch_observation": (
                "NetworkBatchObservationV0"
            ),
            "read_only": True,
            "defines_learning_rule": False,
            "defines_weight_update": False,
            "defines_reward_semantics": False,
        },

        "finite_validation": {
            "historical_differential_cases": 180,
            "historical_differential_mismatches": 0,
            "claim_scope": (
                "finite declared compatibility corpus; "
                "not a universal network-equivalence proof"
            ),
        },

        "gates": [
            "search/core_v0_final_gate_v0.sh",
            "search/network_v0_differential_gate.py",
            "search/network_v0_final_gate_v0.sh",
        ],
    }
