from __future__ import annotations

from contextlib import contextmanager

import spk_core.canonicalize as canon

from spk_core.canonicalize import (
    canonicalize_core_program_runtime,
)
from spk_core.rules import (
    RuleLayer,
    RuleValidity,
    helper_names,
)

from search.core_temporal_normalize_v0 import (
    CONFIG,
    programs,
)


DOMAIN_HELPERS = helper_names(
    validity=RuleValidity.DOMAIN,
    layer=RuleLayer.CORE,
)


def _identity(
    instructions,
    *args,
    **kwargs,
):
    return instructions


@contextmanager
def legacy_runtime_profile():
    """
    Historical oracle used before the production runtime
    canonicalization profile existed.
    """

    originals = {}

    for name in DOMAIN_HELPERS:
        originals[name] = getattr(
            canon,
            name,
        )

        setattr(
            canon,
            name,
            _identity,
        )

    try:
        yield

    finally:
        for name, original in (
            originals.items()
        ):
            setattr(
                canon,
                name,
                original,
            )


def main():
    print(
        "SPK CORE RUNTIME PROFILE "
        "EQUIVALENCE v0"
    )

    checked = 0
    mismatches = 0
    first = None

    for source in programs():
        with legacy_runtime_profile():
            old = canon.canonicalize_core_program(
                source,
                CONFIG,
            )

        new = (
            canonicalize_core_program_runtime(
                source,
                CONFIG,
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
        f"profile mismatches: "
        f"{mismatches}"
    )

    if first is not None:
        print(
            "FIRST FAILURE:"
        )

        print(first)

        raise SystemExit(1)

    print()
    print(
        "RUNTIME PROFILE EQUIVALENCE "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
