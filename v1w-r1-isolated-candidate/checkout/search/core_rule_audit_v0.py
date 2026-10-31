from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


SOURCES = (
    Path("spk_core/canonicalize.py"),
    Path("spk_core/semantic_canonicalize.py"),
)

SPEC = Path(
    "docs/spk-core-algebra-v0.md"
)

HELPERS = {
    "_acc_channel_key",
}

ORCHESTRATORS = {
    "canonicalize_core_program",
    "abstract_normalize_once",
    "abstract_normalize_program",
    "canonicalize_core_program_semantic",
    "canonicalize_core_program_semantic_runtime",
    "canonicalize_core_program_runtime",
}


@dataclass(frozen=True)
class FunctionInfo:
    source: str
    name: str
    line: int
    end_line: int
    calls: tuple[str, ...]


def load_functions(
    path: Path,
) -> list[FunctionInfo]:
    text = path.read_text()

    tree = ast.parse(
        text,
        filename=str(path),
    )

    result = []

    for node in tree.body:
        if not isinstance(
            node,
            ast.FunctionDef,
        ):
            continue

        calls = set()

        for child in ast.walk(node):
            if not isinstance(
                child,
                ast.Call,
            ):
                continue

            func = child.func

            if isinstance(
                func,
                ast.Name,
            ):
                calls.add(
                    func.id
                )

        result.append(
            FunctionInfo(
                source=str(path),
                name=node.name,
                line=node.lineno,
                end_line=(
                    node.end_lineno
                    or node.lineno
                ),
                calls=tuple(
                    sorted(calls)
                ),
            )
        )

    return result


def parse_rule_map(
    path: Path,
) -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, str],
]:
    """
    Return:

        function -> tuple(rule ids)
        rule id  -> function

    The first mapping is intentionally many-to-one.
    """

    text = path.read_text()

    pattern = re.compile(
        r"^\|\s*"
        r"((?:L|D)-[A-Z]+-\d+)"
        r"\s*\|\s*"
        r"`([^`]+)`"
        r"\s*\|",
        re.MULTILINE,
    )

    by_function: dict[
        str,
        list[str],
    ] = defaultdict(list)

    by_rule: dict[
        str,
        str,
    ] = {}

    for match in pattern.finditer(
        text
    ):
        rule = match.group(1)
        function = match.group(2)

        if rule in by_rule:
            raise SystemExit(
                "duplicate Rule ID in specification: "
                f"{rule}"
            )

        by_rule[rule] = function
        by_function[function].append(
            rule
        )

    return (
        {
            function: tuple(rules)
            for function, rules
            in by_function.items()
        },
        by_rule,
    )


def main() -> None:
    functions = []

    for source in SOURCES:
        if not source.exists():
            raise SystemExit(
                f"missing source: {source}"
            )

        functions.extend(
            load_functions(source)
        )

    if not SPEC.exists():
        raise SystemExit(
            f"missing specification: {SPEC}"
        )

    function_map = {
        info.name: info
        for info in functions
    }

    if len(function_map) != len(functions):
        raise SystemExit(
            "duplicate implementation function name"
        )

    known = set(
        function_map
    )

    (
        rules_by_function,
        function_by_rule,
    ) = parse_rule_map(
        SPEC
    )

    mapped_functions = set(
        rules_by_function
    )

    stale_functions = sorted(
        mapped_functions - known
    )

    stale_helpers = sorted(
        HELPERS - known
    )

    stale_orchestrators = sorted(
        ORCHESTRATORS - known
    )

    overlap_rule_helper = sorted(
        mapped_functions & HELPERS
    )

    overlap_rule_orchestrator = sorted(
        mapped_functions
        & ORCHESTRATORS
    )

    overlap_helper_orchestrator = sorted(
        HELPERS
        & ORCHESTRATORS
    )

    classified = (
        mapped_functions
        | HELPERS
        | ORCHESTRATORS
    )

    unclassified = sorted(
        known - classified
    )

    internal_edges = []

    for info in functions:
        for target in info.calls:
            if target in known:
                internal_edges.append(
                    (
                        info.name,
                        target,
                    )
                )

    print(
        "SPK/CORE FORMAL RULE COVERAGE AUDIT v0"
    )
    print()

    print(
        f"implementation functions: "
        f"{len(functions)}"
    )

    print(
        f"algebraic Rule IDs: "
        f"{len(function_by_rule)}"
    )

    print(
        f"mapped rewrite functions: "
        f"{len(mapped_functions)}"
    )

    print(
        f"helpers: "
        f"{len(HELPERS)}"
    )

    print(
        f"orchestrators: "
        f"{len(ORCHESTRATORS)}"
    )

    print()

    print(
        "=" * 88
    )
    print(
        "RULE -> IMPLEMENTATION"
    )
    print(
        "=" * 88
    )

    for rule in sorted(
        function_by_rule
    ):
        function = (
            function_by_rule[rule]
        )

        print(
            f"{rule:14} "
            f"{function}"
        )

    print()

    print(
        "=" * 88
    )
    print(
        "IMPLEMENTATION -> RULES"
    )
    print(
        "=" * 88
    )

    for function in sorted(
        mapped_functions
    ):
        rules = ", ".join(
            rules_by_function[
                function
            ]
        )

        info = function_map.get(
            function
        )

        location = (
            f"{info.source}:{info.line}"
            if info
            else "MISSING"
        )

        print(
            f"{function:56} "
            f"{rules:28} "
            f"{location}"
        )

    print()

    print(
        "=" * 88
    )
    print(
        "NON-RULE FUNCTIONS"
    )
    print(
        "=" * 88
    )

    for name in sorted(
        HELPERS
    ):
        print(
            f"HELPER        {name}"
        )

    for name in sorted(
        ORCHESTRATORS
    ):
        print(
            f"ORCHESTRATOR  {name}"
        )

    print()

    print(
        "=" * 88
    )
    print(
        "INTERNAL CALL GRAPH"
    )
    print(
        "=" * 88
    )

    for source, target in sorted(
        internal_edges
    ):
        print(
            f"{source}"
            f" -> "
            f"{target}"
        )

    print()

    print(
        "=" * 88
    )
    print(
        "COVERAGE ERRORS"
    )
    print(
        "=" * 88
    )

    errors = []

    def report(
        title: str,
        values: list[str],
    ) -> None:
        if not values:
            return

        errors.append(
            title
        )

        print(
            title
        )

        for value in values:
            print(
                f"  {value}"
            )

    report(
        "UNCLASSIFIED IMPLEMENTATION FUNCTIONS",
        unclassified,
    )

    report(
        "SPEC MAPPINGS WITHOUT IMPLEMENTATION",
        stale_functions,
    )

    report(
        "DECLARED HELPERS WITHOUT IMPLEMENTATION",
        stale_helpers,
    )

    report(
        "DECLARED ORCHESTRATORS WITHOUT IMPLEMENTATION",
        stale_orchestrators,
    )

    report(
        "RULE/HELPER CLASSIFICATION OVERLAP",
        overlap_rule_helper,
    )

    report(
        "RULE/ORCHESTRATOR CLASSIFICATION OVERLAP",
        overlap_rule_orchestrator,
    )

    report(
        "HELPER/ORCHESTRATOR CLASSIFICATION OVERLAP",
        overlap_helper_orchestrator,
    )

    if not errors:
        print(
            "NONE"
        )

    print()

    print(
        "=" * 88
    )
    print(
        "SUMMARY"
    )
    print(
        "=" * 88
    )

    print(
        f"implementation functions = "
        f"{len(functions)}"
    )

    print(
        f"mapped rewrite functions = "
        f"{len(mapped_functions)}"
    )

    print(
        f"rule ids = "
        f"{len(function_by_rule)}"
    )

    print(
        f"helpers = "
        f"{len(HELPERS)}"
    )

    print(
        f"orchestrators = "
        f"{len(ORCHESTRATORS)}"
    )

    print(
        f"unclassified = "
        f"{len(unclassified)}"
    )

    print(
        f"stale mappings = "
        f"{len(stale_functions)}"
    )

    print()

    if errors:
        print(
            "AUDIT STATUS: FAIL"
        )
        raise SystemExit(1)

    print(
        "AUDIT STATUS: PASS"
    )
    print(
        "Every implementation function has an "
        "explicit formal role."
    )


if __name__ == "__main__":
    main()
