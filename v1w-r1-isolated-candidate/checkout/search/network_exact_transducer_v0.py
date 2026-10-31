from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from dataclasses import dataclass
from itertools import product

from spk_core.isa import (
    ShiftDecay,
)
from spk_core.network import (
    CoreNetwork,
)
from spk_core.runtime import (
    run_core_batch,
)

from search.network_mixed_semantics_v0 import (
    DELAY_CHOICES,
    EDGE_SLOTS,
    NODE_TYPE_CHOICES,
    make_network,
    topology_name,
)


INPUT_ALPHABET = (
    0,
    1,
)

MAX_REACHABLE_STATES = 100_000


@dataclass(
    frozen=True,
    slots=True,
)
class MachineState:
    #
    # Persistent computational state.
    #
    raws: tuple[
        tuple[str, int],
        ...
    ]

    #
    # Events already scheduled by previous ticks.
    #
    # Each entry:
    #
    #     (relative_offset, node, channel, multiplicity)
    #
    # offset 0 means due at the current tick.
    #
    pending: tuple[
        tuple[int, str, int, int],
        ...
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class StepResult:
    state: MachineState

    #
    # Terminal emissions produced at the current tick:
    #
    #     (node, channel, multiplicity)
    #
    output: tuple[
        tuple[str, int, int],
        ...
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class EquivalenceResult:
    equivalent: bool

    witness: tuple[int, ...] | None = None

    left_output: tuple[
        tuple[str, int, int],
        ...
    ] | None = None

    right_output: tuple[
        tuple[str, int, int],
        ...
    ] | None = None

    explored_pairs: int = 0

    latent_raw_word: (
        tuple[int, ...] | None
    ) = None

    latent_left_raws: (
        tuple[tuple[str, int], ...]
        | None
    ) = None

    latent_right_raws: (
        tuple[tuple[str, int], ...]
        | None
    ) = None


def enumerate_networks():
    result = []

    for (
        b_type,
        c_type,
    ) in product(
        NODE_TYPE_CHOICES,
        repeat=2,
    ):
        for delays in product(
            DELAY_CHOICES,
            repeat=len(
                EDGE_SLOTS
            ),
        ):
            network = make_network(
                delays,
                b_type,
                c_type,
            )

            label = topology_name(
                delays,
                b_type,
                c_type,
            )

            result.append(
                (
                    label,
                    network,
                )
            )

    return tuple(result)


def normalize_raws(
    raw_map,
):
    return tuple(
        sorted(
            raw_map.items()
        )
    )


def normalize_pending(
    pending_counter,
):
    return tuple(
        sorted(
            (
                offset,
                node,
                channel,
                multiplicity,
            )
            for (
                offset,
                node,
                channel,
            ), multiplicity
            in pending_counter.items()
            if multiplicity
        )
    )


def raw_map(
    state: MachineState,
):
    return dict(
        state.raws
    )


def pending_counter(
    state: MachineState,
):
    result = Counter()

    for (
        offset,
        node,
        channel,
        multiplicity,
    ) in state.pending:
        result[
            (
                offset,
                node,
                channel,
            )
        ] += multiplicity

    return result


class ExactMachine:
    def __init__(
        self,
        network: CoreNetwork,
    ):
        self.network = network

        self.nodes = {
            node.name: node
            for node in network.nodes
        }

        #
        # This exact abstraction deliberately applies only to the
        # current non-temporal R/T2 fragment.
        #
        for node in network.nodes:
            for instruction in (
                node.program.instructions
            ):
                if isinstance(
                    instruction,
                    ShiftDecay,
                ):
                    raise ValueError(
                        "exact mixed-network machine "
                        "does not support ShiftDecay"
                    )

        self.outgoing = defaultdict(
            tuple
        )

        temp = defaultdict(
            list
        )

        for edge in network.edges:
            temp[
                (
                    edge.source,
                    edge.source_channel,
                )
            ].append(
                edge
            )

        self.outgoing = {
            key: tuple(value)
            for key, value
            in temp.items()
        }

        self.initial = MachineState(
            raws=normalize_raws(
                {
                    node.name: (
                        node.initial_raw
                    )
                    for node
                    in network.nodes
                }
            ),
            pending=(),
        )

        self._step_cache = {}

    def step(
        self,
        state: MachineState,
        input_symbol: int,
    ) -> StepResult:
        key = (
            state,
            input_symbol,
        )

        cached = self._step_cache.get(
            key
        )

        if cached is not None:
            return cached

        if input_symbol not in (
            0,
            1,
        ):
            raise ValueError(
                f"invalid input symbol: "
                f"{input_symbol}"
            )

        raws = raw_map(
            state
        )

        old_pending = pending_counter(
            state
        )

        due = Counter()
        next_pending = Counter()

        #
        # Advance all previously scheduled network events by one
        # logical tick.
        #
        for (
            offset,
            node,
            channel,
        ), multiplicity in (
            old_pending.items()
        ):
            if offset == 0:
                due[
                    (
                        node,
                        channel,
                    )
                ] += multiplicity
            else:
                next_pending[
                    (
                        offset - 1,
                        node,
                        channel,
                    )
                ] += multiplicity

        #
        # External binary input enters source a on channel 0.
        #
        if input_symbol:
            due[
                (
                    "a",
                    0,
                )
            ] += 1

        #
        # Convert due events to per-node batches.
        #
        node_channels = defaultdict(
            list
        )

        for (
            node,
            channel,
        ), multiplicity in due.items():
            node_channels[
                node
            ].extend(
                [channel]
                * multiplicity
            )

        terminal = Counter()

        #
        # Since every network edge has delay >= 1, execution order
        # among nodes at the same tick cannot influence another node
        # at that same tick.
        #
        for node_name in sorted(
            self.nodes
        ):
            channels = node_channels.get(
                node_name
            )

            if not channels:
                continue

            node = self.nodes[
                node_name
            ]

            result = run_core_batch(
                node.config,
                node.program,
                timestamp=0,
                channels=tuple(
                    channels
                ),
                initial_raw=raws[
                    node_name
                ],
                previous_timestamp=0,
            )

            raws[
                node_name
            ] = result.final_raw

            for (
                _,
                output_channel,
            ) in result.output.as_pairs():
                routes = self.outgoing.get(
                    (
                        node_name,
                        output_channel,
                    ),
                    (),
                )

                if not routes:
                    terminal[
                        (
                            node_name,
                            output_channel,
                        )
                    ] += 1

                    continue

                for edge in routes:
                    #
                    # State stored after this tick is relative to the
                    # NEXT tick.
                    #
                    next_pending[
                        (
                            edge.delay - 1,
                            edge.target,
                            edge.target_channel,
                        )
                    ] += 1

        next_state = MachineState(
            raws=normalize_raws(
                raws
            ),
            pending=normalize_pending(
                next_pending
            ),
        )

        output = tuple(
            sorted(
                (
                    node,
                    channel,
                    multiplicity,
                )
                for (
                    node,
                    channel,
                ), multiplicity
                in terminal.items()
                if multiplicity
            )
        )

        result = StepResult(
            state=next_state,
            output=output,
        )

        self._step_cache[
            key
        ] = result

        return result

    def reachable_states(
        self,
    ):
        seen = {
            self.initial
        }

        queue = deque(
            (
                self.initial,
            )
        )

        while queue:
            state = queue.popleft()

            for symbol in (
                INPUT_ALPHABET
            ):
                result = self.step(
                    state,
                    symbol,
                )

                target = (
                    result.state
                )

                if target in seen:
                    continue

                seen.add(
                    target
                )

                if (
                    len(seen)
                    > MAX_REACHABLE_STATES
                ):
                    raise RuntimeError(
                        "reachable-state limit "
                        "exceeded"
                    )

                queue.append(
                    target
                )

        return frozenset(
            seen
        )


def exact_equivalence(
    left: ExactMachine,
    right: ExactMachine,
) -> EquivalenceResult:
    initial_pair = (
        left.initial,
        right.initial,
    )

    #
    # Store the shortest input word reaching every product state.
    #
    words = {
        initial_pair: ()
    }

    queue = deque(
        (
            initial_pair,
        )
    )

    latent_raw_word = None
    latent_left_raws = None
    latent_right_raws = None

    explored = 0

    while queue:
        (
            left_state,
            right_state,
        ) = queue.popleft()

        word = words[
            (
                left_state,
                right_state,
            )
        ]

        explored += 1

        if (
            latent_raw_word is None
            and left_state.raws
            != right_state.raws
        ):
            latent_raw_word = word
            latent_left_raws = (
                left_state.raws
            )
            latent_right_raws = (
                right_state.raws
            )

        for symbol in (
            INPUT_ALPHABET
        ):
            left_step = left.step(
                left_state,
                symbol,
            )

            right_step = right.step(
                right_state,
                symbol,
            )

            witness = (
                word
                + (
                    symbol,
                )
            )

            if (
                left_step.output
                != right_step.output
            ):
                return EquivalenceResult(
                    equivalent=False,
                    witness=witness,
                    left_output=(
                        left_step.output
                    ),
                    right_output=(
                        right_step.output
                    ),
                    explored_pairs=explored,
                    latent_raw_word=(
                        latent_raw_word
                    ),
                    latent_left_raws=(
                        latent_left_raws
                    ),
                    latent_right_raws=(
                        latent_right_raws
                    ),
                )

            target_pair = (
                left_step.state,
                right_step.state,
            )

            if target_pair in words:
                continue

            words[
                target_pair
            ] = witness

            queue.append(
                target_pair
            )

    return EquivalenceResult(
        equivalent=True,
        explored_pairs=explored,
        latent_raw_word=(
            latent_raw_word
        ),
        latent_left_raws=(
            latent_left_raws
        ),
        latent_right_raws=(
            latent_right_raws
        ),
    )


def main() -> None:
    print(
        "SPK NETWORK EXACT TRANSDUCER v0"
    )

    networks = enumerate_networks()

    machines = tuple(
        (
            label,
            ExactMachine(
                network
            ),
        )
        for label, network
        in networks
    )

    print(
        f"typed networks: "
        f"{len(machines)}"
    )

    print(
        "input alphabet: {0,1}"
    )

    print(
        "state = persistent raw values "
        "+ finite pending-event queue"
    )

    print(
        "last_timestamp excluded: "
        "no ShiftDecay in R/T2 fragment"
    )

    print()

    #
    # Reachability census.
    #
    reachable_counts = []

    for _, machine in machines:
        reachable_counts.append(
            len(
                machine.reachable_states()
            )
        )

    print(
        "=" * 88
    )
    print(
        "REACHABLE STATE CENSUS"
    )
    print(
        "=" * 88
    )

    print(
        f"minimum reachable states: "
        f"{min(reachable_counts)}"
    )

    print(
        f"maximum reachable states: "
        f"{max(reachable_counts)}"
    )

    print(
        f"total reachable states "
        f"across network instances: "
        f"{sum(reachable_counts)}"
    )

    distribution = Counter(
        reachable_counts
    )

    print()
    print(
        "state-count distribution:"
    )

    for count in sorted(
        distribution
    ):
        print(
            f"    {count:4d}: "
            f"{distribution[count]} networks"
        )

    #
    # Exact equivalence partition.
    #
    classes = []

    comparisons = 0
    product_pairs_explored = 0

    first_latent_equivalent = None

    for (
        label,
        machine,
    ) in machines:
        placed = False

        for group in classes:
            (
                representative_label,
                representative_machine,
            ) = group[0]

            result = exact_equivalence(
                representative_machine,
                machine,
            )

            comparisons += 1
            product_pairs_explored += (
                result.explored_pairs
            )

            if not result.equivalent:
                continue

            group.append(
                (
                    label,
                    machine,
                )
            )

            placed = True

            if (
                first_latent_equivalent
                is None
                and result.latent_raw_word
                is not None
            ):
                first_latent_equivalent = (
                    representative_label,
                    label,
                    result,
                )

            break

        if not placed:
            classes.append(
                [
                    (
                        label,
                        machine,
                    )
                ]
            )

    print()
    print(
        "=" * 88
    )
    print(
        "EXACT CONTEXTUAL PARTITION"
    )
    print(
        "=" * 88
    )

    print(
        f"exact contextual classes: "
        f"{len(classes)}"
    )

    print(
        f"collapsed excess: "
        f"{len(machines) - len(classes)}"
    )

    print(
        f"equivalence comparisons: "
        f"{comparisons}"
    )

    print(
        f"product-state pairs explored: "
        f"{product_pairs_explored}"
    )

    non_singletons = [
        group
        for group in classes
        if len(group) > 1
    ]

    print(
        f"non-singleton exact classes: "
        f"{len(non_singletons)}"
    )

    print()
    print(
        "largest exact classes:"
    )

    for index, group in enumerate(
        sorted(
            classes,
            key=lambda item: (
                -len(item),
                item[0][0],
            ),
        )[:10],
        start=1,
    ):
        print(
            f"class {index}: "
            f"size={len(group)}"
        )

        for label, _ in group[:6]:
            print(
                f"    {label}"
            )

        if len(group) > 6:
            print(
                f"    ... "
                f"{len(group) - 6} more"
            )

    print()
    print(
        "=" * 88
    )
    print(
        "LATENT IMPLEMENTATION STATE"
    )
    print(
        "=" * 88
    )

    if (
        first_latent_equivalent
        is None
    ):
        print(
            "No exactly-equivalent pair with "
            "different reachable raw states "
            "was found."
        )

    else:
        (
            left_label,
            right_label,
            result,
        ) = first_latent_equivalent

        print(
            "Exactly equivalent networks with "
            "different implementation raw state:"
        )

        print()
        print(
            "network L:"
        )
        print(
            f"    {left_label}"
        )

        print(
            "network R:"
        )
        print(
            f"    {right_label}"
        )

        print()
        print(
            "input prefix reaching the "
            "raw-state difference:"
        )

        print(
            "    "
            + "".join(
                map(
                    str,
                    result.latent_raw_word,
                )
            )
        )

        print(
            f"L raw state: "
            f"{result.latent_left_raws}"
        )

        print(
            f"R raw state: "
            f"{result.latent_right_raws}"
        )

        print()
        print(
            "The full product-state exploration "
            "still proves identical outputs for "
            "every future binary input word."
        )

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

    if len(classes) != 52:
        print(
            "EXACT CLASS COUNT DIFFERS "
            "FROM HORIZON CENSUS"
        )

        raise SystemExit(1)

    print(
        "exact contextual classes: 52"
    )

    print(
        "horizon-12 classes: 52"
    )

    print(
        "EXACT MIXED-NETWORK "
        "TRANSDUCER CHECKPOINT: PASS"
    )

    print()
    print(
        "Scope:"
    )

    print(
        "- 108 declared three-node R/T2 DAG networks"
    )

    print(
        "- binary external input per logical tick"
    )

    print(
        "- positive edge delays in {1,2}"
    )

    print(
        "- terminal-output observation"
    )

    print(
        "- no ShiftDecay"
    )

    print(
        "- exact finite-state product exploration"
    )


if __name__ == "__main__":
    main()
