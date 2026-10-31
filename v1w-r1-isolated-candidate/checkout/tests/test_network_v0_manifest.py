from __future__ import annotations

import json
from pathlib import Path

from spk_core.core_v0 import (
    CORE_V0_IR_SHA256,
)
from spk_network.network_v0 import (
    NETWORK_V0_SCHEMA,
    build_network_v0_manifest,
)


MANIFEST_PATH = Path(
    "docs/spk-network-v0-manifest.json"
)


def frozen_manifest():
    return json.loads(
        MANIFEST_PATH.read_text()
    )


def test_network_v0_manifest_matches_contract():
    assert (
        frozen_manifest()
        == build_network_v0_manifest()
    )


def test_network_v0_identity_is_frozen():
    manifest = frozen_manifest()

    assert (
        manifest["schema"]
        == NETWORK_V0_SCHEMA
        == "spk-network-manifest/v0"
    )

    assert (
        manifest["network_version"]
        == "0"
    )


def test_network_v0_is_bound_to_frozen_core():
    manifest = frozen_manifest()

    assert (
        manifest[
            "core_dependency"
        ][
            "core_ir_sha256"
        ]
        == CORE_V0_IR_SHA256
        == (
            "910ae1338a211257bee41c4d53ce55b78532a71ce23b3bd4d3d6a683455dce94"
        )
    )


def test_network_v0_learning_is_observational_only():
    learning = frozen_manifest()[
        "learning_interface"
    ]

    assert learning["read_only"] is True
    assert (
        learning[
            "defines_learning_rule"
        ]
        is False
    )
    assert (
        learning[
            "defines_weight_update"
        ]
        is False
    )
    assert (
        learning[
            "defines_reward_semantics"
        ]
        is False
    )
