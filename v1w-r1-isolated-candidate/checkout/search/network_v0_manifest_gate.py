from __future__ import annotations

import argparse
import json
from pathlib import Path

from spk_network.network_v0 import (
    build_network_v0_manifest,
)


MANIFEST_PATH = Path(
    "docs/spk-network-v0-manifest.json"
)


def serialized_manifest() -> str:
    return (
        json.dumps(
            build_network_v0_manifest(),
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
            "NETWORK V0 MANIFEST FAIL: "
            f"{MANIFEST_PATH} missing"
        )

    frozen = MANIFEST_PATH.read_text()

    if frozen != generated:
        raise SystemExit(
            "NETWORK V0 MANIFEST FAIL: "
            "runtime contract differs from "
            "frozen manifest"
        )

    manifest = (
        build_network_v0_manifest()
    )

    print(
        "SPK NETWORK V0 MANIFEST GATE"
    )
    print()

    print(
        "schema:",
        manifest["schema"],
    )

    print(
        "network version:",
        manifest[
            "network_version"
        ],
    )

    print(
        "Core version:",
        manifest[
            "core_dependency"
        ][
            "core_version"
        ],
    )

    print(
        "Core IR sha256:",
        manifest[
            "core_dependency"
        ][
            "core_ir_sha256"
        ],
    )

    print(
        "differential cases:",
        manifest[
            "finite_validation"
        ][
            "historical_differential_cases"
        ],
    )

    print(
        "differential mismatches:",
        manifest[
            "finite_validation"
        ][
            "historical_differential_mismatches"
        ],
    )

    print()
    print(
        "SPK NETWORK V0 MANIFEST "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
