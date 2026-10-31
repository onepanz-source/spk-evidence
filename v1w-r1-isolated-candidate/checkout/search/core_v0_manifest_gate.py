from __future__ import annotations

import argparse
import json
from pathlib import Path

from spk_core.core_v0 import (
    build_core_v0_manifest,
)


MANIFEST_PATH = Path(
    "docs/spk-core-v0-manifest.json"
)


def serialized_manifest() -> str:
    return (
        json.dumps(
            build_core_v0_manifest(),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "explicitly replace the frozen "
            "Core v0 manifest"
        ),
    )

    args = parser.parse_args()

    generated = serialized_manifest()

    if args.write:
        MANIFEST_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        MANIFEST_PATH.write_text(
            generated
        )

        print(
            "WROTE",
            MANIFEST_PATH,
        )

        return

    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"CORE V0 MANIFEST FAIL: "
            f"{MANIFEST_PATH} missing"
        )

    frozen = MANIFEST_PATH.read_text()

    if frozen != generated:
        print(
            "CORE V0 MANIFEST FAIL: "
            "runtime contract differs from "
            "frozen manifest"
        )

        print()
        print(
            "If the semantic change is intentional, "
            "review it first and then regenerate with:"
        )
        print()
        print(
            "  python -m "
            "search.core_v0_manifest_gate --write"
        )

        raise SystemExit(1)

    manifest = (
        build_core_v0_manifest()
    )

    rule_specs = (
        manifest[
            "rewrite_system"
        ][
            "rules"
        ]
    )

    rule_ids = sum(
        len(
            spec[
                "rule_ids"
            ]
        )
        for spec in rule_specs
    )

    runtime_specs = sum(
        spec[
            "validity"
        ] == "runtime"
        for spec in rule_specs
    )

    domain_specs = sum(
        spec[
            "validity"
        ] == "domain"
        for spec in rule_specs
    )

    print(
        "SPK CORE V0 MANIFEST GATE"
    )
    print()

    print(
        "schema:",
        manifest[
            "schema"
        ],
    )
    print(
        "version:",
        manifest[
            "core_version"
        ],
    )
    print(
        "rule specs:",
        len(rule_specs),
    )
    print(
        "rule ids:",
        rule_ids,
    )
    print(
        "runtime specs:",
        runtime_specs,
    )
    print(
        "domain specs:",
        domain_specs,
    )

    print()

    print(
        "depth<=5 corpus:",
        manifest[
            "finite_validation"
        ][
            "runtime_nf_depth5"
        ][
            "syntactic_programs"
        ],
    )

    print(
        "runtime NFs:",
        manifest[
            "finite_validation"
        ][
            "runtime_nf_depth5"
        ][
            "distinct_runtime_normal_forms"
        ],
    )

    print()
    print(
        "SPK CORE V0 MANIFEST "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
