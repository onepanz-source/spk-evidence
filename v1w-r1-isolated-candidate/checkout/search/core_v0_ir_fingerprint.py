from __future__ import annotations

import hashlib
from itertools import product

from spk_core.core_v0 import (
    CORE_V0_IR_SHA256,
)
from spk_core.ir_v0 import (
    dumps_core_ir_v0,
    loads_core_ir_v0,
)
from spk_core.isa import CoreProgram
from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic_runtime,
)

from search.core_rule_soundness_v0 import (
    CONFIG,
    PROGRAM_POOL,
)


MAX_DEPTH = 5


def programs():
    for depth in range(
        1,
        MAX_DEPTH + 1,
    ):
        for instructions in product(
            PROGRAM_POOL,
            repeat=depth,
        ):
            yield CoreProgram(
                tuple(instructions)
            )


def normalize(
    program: CoreProgram,
) -> CoreProgram:
    return (
        canonicalize_core_program_semantic_runtime(
            program,
            config=CONFIG,
        )
    )


def main():
    syntactic = 0
    normal_forms = set()

    for program in programs():
        syntactic += 1
        normal_forms.add(
            normalize(
                program
            )
        )

    serialized = []

    roundtrip_failures = 0

    for normal_form in normal_forms:
        text = dumps_core_ir_v0(
            CONFIG,
            normal_form,
        )

        (
            parsed_config,
            parsed_program,
        ) = loads_core_ir_v0(
            text
        )

        if (
            parsed_config != CONFIG
            or parsed_program != normal_form
        ):
            roundtrip_failures += 1

        serialized.append(
            text
        )

    serialized.sort()

    payload = (
        "\n".join(serialized)
        + "\n"
    ).encode(
        "utf-8"
    )

    digest = hashlib.sha256(
        payload
    ).hexdigest()

    print(
        "SPK CORE V0 IR FINGERPRINT"
    )
    print()

    print(
        "syntactic programs:",
        syntactic,
    )
    print(
        "distinct runtime NFs:",
        len(normal_forms),
    )
    print(
        "serialized IR documents:",
        len(serialized),
    )
    print(
        "roundtrip failures:",
        roundtrip_failures,
    )
    print(
        "sha256:",
        digest,
    )

    if syntactic != 19607:
        raise SystemExit(
            "CORE V0 IR FINGERPRINT FAIL: "
            f"unexpected corpus size {syntactic}"
        )

    if len(normal_forms) != 2499:
        raise SystemExit(
            "CORE V0 IR FINGERPRINT FAIL: "
            f"unexpected NF count "
            f"{len(normal_forms)}"
        )

    if roundtrip_failures:
        raise SystemExit(
            "CORE V0 IR FINGERPRINT FAIL: "
            f"{roundtrip_failures} "
            "roundtrip failures"
        )

    if digest != CORE_V0_IR_SHA256:
        raise SystemExit(
            "CORE V0 IR FINGERPRINT FAIL: "
            f"{digest} != "
            f"{CORE_V0_IR_SHA256}"
        )

    print()
    print(
        "SPK CORE V0 IR FINGERPRINT "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
