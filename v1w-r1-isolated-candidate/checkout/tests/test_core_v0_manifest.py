from __future__ import annotations

import json
from pathlib import Path

from spk_core.core_v0 import (
    CORE_V0_SCHEMA,
    CORE_V0_VERSION,
    build_core_v0_manifest,
)


MANIFEST_PATH = Path(
    "docs/spk-core-v0-manifest.json"
)


def frozen_manifest():
    return json.loads(
        MANIFEST_PATH.read_text()
    )


def test_core_v0_manifest_matches_runtime_contract():
    assert (
        frozen_manifest()
        == build_core_v0_manifest()
    )


def test_core_v0_identity_is_frozen():
    manifest = frozen_manifest()

    assert (
        manifest["schema"]
        == CORE_V0_SCHEMA
        == "spk-core-manifest/v0"
    )

    assert (
        manifest["core_version"]
        == CORE_V0_VERSION
        == "0"
    )


def test_core_v0_basis_is_frozen():
    manifest = frozen_manifest()

    assert manifest[
        "algebra"
    ][
        "combined_basis"
    ] == [
        "MERGE",
        "DELAY",
        "ACC",
        "DECAY",
        "CMP",
        "EMIT",
        "RESET",
    ]


def test_core_v0_runtime_nf_baseline_is_frozen():
    baseline = frozen_manifest()[
        "finite_validation"
    ][
        "runtime_nf_depth5"
    ]

    assert (
        baseline[
            "syntactic_programs"
        ]
        == 19607
    )

    assert (
        baseline[
            "distinct_runtime_normal_forms"
        ]
        == 2499
    )

    assert (
        baseline[
            "termination_failures"
        ]
        == 0
    )

    assert (
        baseline[
            "idempotence_failures"
        ]
        == 0
    )

    assert (
        baseline[
            "pass_cycles"
        ]
        == 0
    )

    assert (
        baseline[
            "fork_joinability_mismatches"
        ]
        == 0
    )

    assert (
        baseline[
            "residual_helper_edges"
        ]
        == 0
    )


def test_core_v0_domain_is_fail_closed():
    manifest = frozen_manifest()

    assert (
        manifest[
            "rewrite_system"
        ][
            "domain_default"
        ]
        == "fail_closed"
    )
