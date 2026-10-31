from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)

from spk_core.canonicalize import (
    canonicalize_core_program,
)

from search.core_temporal_normalize_v0 import (
    normalize_temporal,
    programs,
)

from search.core_temporal_core_interaction_v0 import (
    fixed_point,
    program_key,
    step_ct,
    step_tc,
)

from search.core_temporal_quotient_alignment_v0 import (
    alternating_orbit,
)


def instruction_label(
    instruction,
):
    name = type(
        instruction
    ).__name__

    return (
        f"{name}"
        f"{instruction!r}"
    )


def adjacent_swap(
    left,
    right,
):
    """
    Return the single adjacent swap separating two programs,
    if that is the only difference.
    """

    a = left.instructions
    b = right.instructions

    if len(a) != len(b):
        return None

    differences = [
        index
        for index, (
            x,
            y,
        ) in enumerate(
            zip(
                a,
                b,
            )
        )
        if x != y
    ]

    if len(differences) != 2:
        return None

    i, j = differences

    if j != i + 1:
        return None

    if (
        a[i] == b[j]
        and a[j] == b[i]
    ):
        return (
            a[i],
            a[j],
        )

    return None


def canonical_swap_pattern(
    pair,
):
    if pair is None:
        return (
            "non-adjacent-or-structural",
        )

    left, right = pair

    labels = sorted(
        (
            repr(left),
            repr(right),
        )
    )

    return tuple(
        labels
    )


def build_partition_data():
    records = []

    tc_to_ct = defaultdict(
        set
    )

    ct_to_tc = defaultdict(
        set
    )

    edge_sources = defaultdict(
        list
    )

    tc_objects = {}
    ct_objects = {}

    for source in programs():
        (
            tc,
            _,
            tc_cycle,
        ) = fixed_point(
            source,
            step_tc,
        )

        (
            ct,
            _,
            ct_cycle,
        ) = fixed_point(
            source,
            step_ct,
        )

        if (
            tc_cycle is not None
            or ct_cycle is not None
        ):
            raise AssertionError(
                "unexpected composite cycle"
            )

        tc_key = program_key(
            tc
        )

        ct_key = program_key(
            ct
        )

        tc_objects[
            tc_key
        ] = tc

        ct_objects[
            ct_key
        ] = ct

        tc_to_ct[
            tc_key
        ].add(
            ct_key
        )

        ct_to_tc[
            ct_key
        ].add(
            tc_key
        )

        edge_sources[
            (
                tc_key,
                ct_key,
            )
        ].append(
            source
        )

        records.append(
            (
                source,
                tc,
                ct,
            )
        )

    return (
        records,
        tc_to_ct,
        ct_to_tc,
        edge_sources,
        tc_objects,
        ct_objects,
    )


def anomalous_components(
    tc_to_ct,
    ct_to_tc,
):
    graph = defaultdict(
        set
    )

    for tc_key, ct_keys in (
        tc_to_ct.items()
    ):
        for ct_key in ct_keys:
            left = (
                "TC",
                tc_key,
            )

            right = (
                "CT",
                ct_key,
            )

            graph[
                left
            ].add(
                right
            )

            graph[
                right
            ].add(
                left
            )

    seeds = {
        node
        for node, neighbors
        in graph.items()
        if len(neighbors) > 1
    }

    seen = set()
    components = []

    for seed in sorted(
        seeds,
        key=repr,
    ):
        if seed in seen:
            continue

        component = set()
        queue = deque(
            (
                seed,
            )
        )

        while queue:
            node = queue.popleft()

            if node in component:
                continue

            component.add(
                node
            )

            for neighbor in graph[
                node
            ]:
                if (
                    neighbor
                    not in component
                ):
                    queue.append(
                        neighbor
                    )

        seen.update(
            component
        )

        components.append(
            frozenset(
                component
            )
        )

    return tuple(
        components
    )


def collect_unique_cycles():
    cycles = {}

    for phase in (
        "C",
        "T",
    ):
        for source in programs():
            result = alternating_orbit(
                source,
                phase,
            )

            if (
                result["kind"]
                != "cycle"
            ):
                continue

            program_keys = frozenset(
                result[
                    "distinct_programs"
                ]
            )

            cycles.setdefault(
                program_keys,
                (
                    phase,
                    source,
                    result,
                ),
            )

    return cycles


def main():
    print(
        "SPK CORE / TEMPORAL "
        "CRITICAL PAIR CENSUS v0"
    )

    (
        records,
        tc_to_ct,
        ct_to_tc,
        edge_sources,
        tc_objects,
        ct_objects,
    ) = build_partition_data()

    print(
        f"source programs: "
        f"{len(records)}"
    )

    print()

    #
    # --------------------------------------------------------------
    # Partition anomalies.
    # --------------------------------------------------------------
    #
    print(
        "=" * 88
    )
    print(
        "PARTITION SPLITS"
    )
    print(
        "=" * 88
    )

    tc_splits = {
        key: values
        for key, values
        in tc_to_ct.items()
        if len(values) > 1
    }

    ct_splits = {
        key: values
        for key, values
        in ct_to_tc.items()
        if len(values) > 1
    }

    print(
        f"T->C split classes: "
        f"{len(tc_splits)}"
    )

    print(
        f"C->T split classes: "
        f"{len(ct_splits)}"
    )

    components = (
        anomalous_components(
            tc_to_ct,
            ct_to_tc,
        )
    )

    print(
        f"anomalous bipartite components: "
        f"{len(components)}"
    )

    for index, component in enumerate(
        components,
        start=1,
    ):
        tc_nodes = sorted(
            (
                key
                for side, key
                in component
                if side == "TC"
            ),
            key=repr,
        )

        ct_nodes = sorted(
            (
                key
                for side, key
                in component
                if side == "CT"
            ),
            key=repr,
        )

        print()
        print(
            f"component {index}:"
        )

        print(
            f"    T->C nodes: "
            f"{len(tc_nodes)}"
        )

        print(
            f"    C->T nodes: "
            f"{len(ct_nodes)}"
        )

        tc_index = {
            key: i
            for i, key
            in enumerate(
                tc_nodes
            )
        }

        ct_index = {
            key: i
            for i, key
            in enumerate(
                ct_nodes
            )
        }

        print()
        print(
            "    T->C representatives:"
        )

        for key in tc_nodes:
            print(
                f"        TC"
                f"{tc_index[key]} = "
                f"{tc_objects[key].instructions}"
            )

        print()
        print(
            "    C->T representatives:"
        )

        for key in ct_nodes:
            print(
                f"        CT"
                f"{ct_index[key]} = "
                f"{ct_objects[key].instructions}"
            )

        print()
        print(
            "    source mapping edges:"
        )

        for tc_key in tc_nodes:
            for ct_key in (
                tc_to_ct[
                    tc_key
                ]
            ):
                if ct_key not in (
                    ct_index
                ):
                    continue

                sources = edge_sources[
                    (
                        tc_key,
                        ct_key,
                    )
                ]

                print(
                    f"        TC"
                    f"{tc_index[tc_key]}"
                    f" -> CT"
                    f"{ct_index[ct_key]}"
                    f": "
                    f"{len(sources)} "
                    f"source programs"
                )

                for source in (
                    sources[:6]
                ):
                    print(
                        f"            "
                        f"{source.instructions}"
                    )

                if len(sources) > 6:
                    print(
                        f"            ... "
                        f"{len(sources) - 6} "
                        f"more"
                    )

    #
    # --------------------------------------------------------------
    # Actual alternating critical pairs.
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "TWO-CYCLE CRITICAL PAIRS"
    )
    print(
        "=" * 88
    )

    cycles = (
        collect_unique_cycles()
    )

    print(
        f"unique cycles: "
        f"{len(cycles)}"
    )

    swap_patterns = Counter()

    non_swap_cycles = 0

    cycle_rows = []

    for (
        program_keys,
        (
            phase,
            source,
            result,
        ),
    ) in cycles.items():
        if (
            len(
                result[
                    "distinct_programs"
                ]
            )
            != 2
        ):
            non_swap_cycles += 1
            continue

        keys = list(
            result[
                "distinct_programs"
            ]
        )

        #
        # Reconstruct the two programs from the union of known
        # representatives.
        #
        known = {}

        known.update(
            tc_objects
        )

        known.update(
            ct_objects
        )

        left = known.get(
            keys[0]
        )

        right = known.get(
            keys[1]
        )

        if (
            left is None
            or right is None
        ):
            #
            # Fall back by searching the finite source set and applying
            # the normalizers once.
            #
            for candidate in programs():
                options = (
                    candidate,
                    canonicalize_core_program(
                        candidate
                    ),
                    normalize_temporal(
                        candidate
                    ),
                )

                for option in options:
                    known[
                        program_key(
                            option
                        )
                    ] = option

            left = known[
                keys[0]
            ]

            right = known[
                keys[1]
            ]

        swap = adjacent_swap(
            left,
            right,
        )

        if swap is None:
            non_swap_cycles += 1

        pattern = (
            canonical_swap_pattern(
                swap
            )
        )

        swap_patterns[
            pattern
        ] += 1

        cycle_rows.append(
            (
                pattern,
                left,
                right,
                source,
            )
        )

    print(
        f"non-adjacent/structural cycles: "
        f"{non_swap_cycles}"
    )

    print()
    print(
        "critical-pair pattern census:"
    )

    for pattern, count in sorted(
        swap_patterns.items(),
        key=lambda item: (
            -item[1],
            repr(item[0]),
        ),
    ):
        print(
            f"    {count:3d} x "
            f"{pattern}"
        )

    print()
    print(
        "all unique cycles:"
    )

    for index, (
        pattern,
        left,
        right,
        source,
    ) in enumerate(
        sorted(
            cycle_rows,
            key=lambda row: (
                repr(
                    row[0]
                ),
                repr(
                    row[1].instructions
                ),
            ),
        ),
        start=1,
    ):
        print()
        print(
            f"cycle {index}:"
        )

        print(
            f"    pattern="
            f"{pattern}"
        )

        print(
            f"    A="
            f"{left.instructions}"
        )

        print(
            f"    B="
            f"{right.instructions}"
        )

        print(
            f"    witness source="
            f"{source.instructions}"
        )

    #
    # --------------------------------------------------------------
    # Checkpoint.
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "CHECKPOINT"
    )
    print(
        "=" * 88
    )

    print(
        f"partition anomaly components: "
        f"{len(components)}"
    )

    print(
        f"unique alternating cycles: "
        f"{len(cycles)}"
    )

    print(
        f"critical-pair patterns: "
        f"{len(swap_patterns)}"
    )

    print()
    print(
        "CRITICAL PAIR CENSUS: PASS"
    )

    print(
        "Diagnostic only: no rewrite "
        "orientation changed."
    )


if __name__ == "__main__":
    main()
