from __future__ import annotations

from contextlib import contextmanager

import spk_core.canonicalize as core
import spk_core.semantic_canonicalize as semantic

from spk_core.rules import (
    RuleLayer,
    RuleValidity,
    helper_names,
)

from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic_runtime,
)

from search.core_temporal_normalize_v0 import (
    CONFIG,
    programs,
)


CORE_DOMAIN = helper_names(
    validity=RuleValidity.DOMAIN,
    layer=RuleLayer.CORE,
)

SEMANTIC_DOMAIN = helper_names(
    validity=RuleValidity.DOMAIN,
    layer=RuleLayer.SEMANTIC,
)


def _core_identity(
    instructions,
    *args,
    **kwargs,
):
    return instructions


def _semantic_identity(
    *args,
    **kwargs,
):
    #
    # Semantic DOMAIN helpers are either:
    #
    #   helper(program)
    #   helper(config, program)
    #
    return args[-1]


@contextmanager
def legacy_runtime_profile():
    originals = []

    for name in CORE_DOMAIN:
        original = getattr(
            core,
            name,
        )

        originals.append(
            (
                core,
                name,
                original,
            )
        )

        setattr(
            core,
            name,
            _core_identity,
        )

    for name in SEMANTIC_DOMAIN:
        original = getattr(
            semantic,
            name,
        )

        originals.append(
            (
                semantic,
                name,
                original,
            )
        )

        setattr(
            semantic,
            name,
            _semantic_identity,
        )

    try:
        yield

    finally:
        for (
            module,
            name,
            original,
        ) in reversed(originals):
            setattr(
                module,
                name,
                original,
            )


def main():
    print(
        "SPK SEMANTIC RUNTIME PROFILE "
        "EQUIVALENCE v0"
    )

    checked = 0
    mismatches = 0
    first = None

    for source in programs():
        with legacy_runtime_profile():
            old = (
                semantic
                .canonicalize_core_program_semantic(
                    source,
                    config=CONFIG,
                )
            )

        new = (
            canonicalize_core_program_semantic_runtime(
                source,
                config=CONFIG,
            )
        )

        checked += 1

        if (
            old.instructions
            == new.instructions
        ):
            continue

        mismatches += 1

        if first is None:
            first = (
                source,
                old,
                new,
            )

    print(
        f"programs checked: {checked}"
    )

    print(
        f"Core DOMAIN helpers: "
        f"{len(CORE_DOMAIN)}"
    )

    print(
        f"semantic DOMAIN helpers: "
        f"{len(SEMANTIC_DOMAIN)}"
    )

    print(
        f"profile mismatches: "
        f"{mismatches}"
    )

    if first is not None:
        print()
        print(
            "FIRST FAILURE:"
        )

        print(first)

        raise SystemExit(1)

    print()
    print(
        "SEMANTIC RUNTIME PROFILE "
        "EQUIVALENCE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
