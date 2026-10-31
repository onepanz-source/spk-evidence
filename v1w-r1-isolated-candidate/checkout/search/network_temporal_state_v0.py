from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from dataclasses import dataclass
from itertools import (
    combinations,
    product,
)

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.network import (
    CoreNetwork,
    NetworkEdge,
    NetworkEvent,
    NetworkNode,
    run_core_network,
)
from spk_core.runtime import (
    run_core_batch,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


EDGE_SLOTS = (
    ("a", "b"),
    ("a", "c"),
    ("b", "c"),
)


DELAY_CHOICES = (
    None,
    1,
    2,
)


NODE_TYPE_CHOICES = (
    "R",
    "D",
)


INPUT_ALPHABET = (
    0,
    1,
)


BRIDGE_MAX_HORIZON = 6


MAX_REACHABLE_STATES = 100_000


def relay_program() -> CoreProgram:
    return CoreProgram(
        (
            CoreAcc(1, 0),
            CoreCmp(1),
            CoreEmit(7),
            CoreReset(0),
        )
    )


def decay_program() -> CoreProgram:
    """
    Temporal memory probe.

    One isolated event leaves raw=16.

    A later event distinguishes elapsed time:

        delta=1:
            (16 >> 1) + 16 = 24 -> emit

        delta=2:
            (16 >> 2) + 16 = 20 -> emit

        delta=3:
            (16 >> 3) + 16 = 18 -> no emit
    """

    return CoreProgram(
        (
            ShiftDecay(1),
            CoreAcc(16, 0),
            CoreCmp(19),
            CoreEmit(7),
            CoreReset(0),
        )
    )


PROGRAMS = {
    "R": relay_program(),
    "D": decay_program(),
}


def age_cap_for_node(
    node: NetworkNode,
) -> int:
    """
    Exact conservative age saturation bound for the current unsigned
    fixed-width Core semantics.

    If the smallest positive shift rate is k, then once:

        k * delta >= state_bits

    every positive ShiftDecay maps every representable raw value to 0.

    Beyond that delta, increasing elapsed time cannot alter the result
    of any positive shift.
    """

    positive_rates = [
        instruction.bits_per_tick
        for instruction
        in node.program.instructions
        if (
            isinstance(
                instruction,
                ShiftDecay,
            )
            and instruction.bits_per_tick > 0
        )
    ]

    if not positive_rates:
        return 0

    minimum_rate = min(
        positive_rates
    )

    return (
        node.config.state_bits
        + minimum_rate
        - 1
    ) // minimum_rate


def make_nodes(
    b_type: str,
    c_type: str,
):
    return (
        NetworkNode(
            "a",
            CONFIG,
            PROGRAMS["R"],
        ),
        NetworkNode(
            "b",
            CONFIG,
            PROGRAMS[b_type],
        ),
        NetworkNode(
            "c",
            CONFIG,
            PROGRAMS[c_type],
        ),
    )


def make_network(
    delays,
    b_type: str,
    c_type: str,
):
    edges = []

    for (
        source,
        target,
    ), delay in zip(
        EDGE_SLOTS,
        delays,
    ):
        if delay is None:
            continue

        edges.append(
            NetworkEdge(
                source=source,
                source_channel=7,
                target=target,
                target_channel=0,
                delay=delay,
            )
        )

    return CoreNetwork(
        nodes=make_nodes(
            b_type,
            c_type,
        ),
        edges=tuple(edges),
    )


def topology_name(
    delays,
    b_type: str,
    c_type: str,
):
    parts = []

    for (
        source,
        target,
    ), delay in zip(
        EDGE_SLOTS,
        delays,
    ):
        parts.append(
            f"{source}{target}="
            + (
                "-"
                if delay is None
                else str(delay)
            )
        )

    return (
        f"b={b_type} "
        f"c={c_type} "
        + " ".join(parts)
    )


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
            result.append(
                (
                    topology_name(
                        delays,
                        b_type,
                        c_type,
                    ),
                    make_network(
                        delays,
                        b_type,
                        c_type,
                    ),
                )
            )

    return tuple(result)


@dataclass(
    frozen=True,
    slots=True,
)
class TemporalState:
    #
    # Persistent Core raw values.
    #
    raws: tuple[
        tuple[str, int],
        ...
    ]

    #
    # Relative elapsed time since the last batch processed by each
    # node, saturated at that node's exact age cap.
    #
    ages: tuple[
        tuple[str, int],
        ...
    ]

    #
    # Events already in flight.
    #
    # offset is relative to the current logical tick.
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
    state: TemporalState

    #
    # Terminal output emitted during this logical tick.
    #
    output: tuple[
        tuple[str, int, int],
        ...
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class StateWitness:
    word: tuple[int, ...]

    left_output: tuple[
        tuple[str, int, int],
        ...
    ]

    right_output: tuple[
        tuple[str, int, int],
        ...
    ]

    explored_pairs: int


def normalize_map(
    values,
):
    return tuple(
        sorted(
            values.items()
        )
    )


def normalize_pending(
    counter,
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
            in counter.items()
            if multiplicity
        )
    )


class TemporalMachine:
    def __init__(
        self,
        network: CoreNetwork,
    ):
        self.network = network

        self.nodes = {
            node.name: node
            for node in network.nodes
        }

        self.age_caps = {
            node.name: (
                age_cap_for_node(
                    node
                )
            )
            for node in network.nodes
        }

        outgoing = defaultdict(
            list
        )

        for edge in network.edges:
            outgoing[
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
            in outgoing.items()
        }

        self.initial = TemporalState(
            raws=normalize_map(
                {
                    node.name: (
                        node.initial_raw
                    )
                    for node
                    in network.nodes
                }
            ),
            ages=normalize_map(
                {
                    node.name: 0
                    for node
                    in network.nodes
                }
            ),
            pending=(),
        )

        self._step_cache = {}

    def step(
        self,
        state: TemporalState,
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

        if input_symbol not in INPUT_ALPHABET:
            raise ValueError(
                f"invalid input symbol: "
                f"{input_symbol}"
            )

        raws = dict(
            state.raws
        )

        ages = dict(
            state.ages
        )

        old_pending = Counter()

        for (
            offset,
            node,
            channel,
            multiplicity,
        ) in state.pending:
            old_pending[
                (
                    offset,
                    node,
                    channel,
                )
            ] += multiplicity

        due = Counter()
        next_pending = Counter()

        #
        # Advance routed events by one logical tick.
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
        # External input enters a:0 at the current tick.
        #
        if input_symbol:
            due[
                (
                    "a",
                    0,
                )
            ] += 1

        node_channels = defaultdict(
            list
        )

        for (
            node_name,
            channel,
        ), multiplicity in due.items():
            node_channels[
                node_name
            ].extend(
                [channel]
                * multiplicity
            )

        terminal = Counter()

        next_ages = {}

        #
        # delay >= 1 guarantees that emissions generated in this loop
        # cannot affect another node during the same logical tick.
        #
        for node_name in sorted(
            self.nodes
        ):
            node = self.nodes[
                node_name
            ]

            channels = node_channels.get(
                node_name
            )

            cap = self.age_caps[
                node_name
            ]

            current_age = ages[
                node_name
            ]

            if not channels:
                if cap == 0:
                    next_ages[
                        node_name
                    ] = 0
                else:
                    next_ages[
                        node_name
                    ] = min(
                        current_age + 1,
                        cap,
                    )

                continue

            #
            # Only delta matters to Core. Using timestamp=current_age
            # and previous_timestamp=0 gives exactly that delta.
            #
            result = run_core_batch(
                node.config,
                node.program,
                timestamp=current_age,
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

            #
            # State returned by step() represents the beginning of the
            # NEXT logical tick. One tick will then have elapsed since
            # the batch just processed.
            #
            if cap == 0:
                next_ages[
                    node_name
                ] = 0
            else:
                next_ages[
                    node_name
                ] = 1

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
                    next_pending[
                        (
                            edge.delay - 1,
                            edge.target,
                            edge.target_channel,
                        )
                    ] += 1

        next_state = TemporalState(
            raws=normalize_map(
                raws
            ),
            ages=normalize_map(
                next_ages
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

            for symbol in INPUT_ALPHABET:
                target = self.step(
                    state,
                    symbol,
                ).state

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


def words_up_to(
    maximum: int,
):
    yield ()

    for length in range(
        1,
        maximum + 1,
    ):
        yield from product(
            INPUT_ALPHABET,
            repeat=length,
        )


def external_events(
    word,
):
    return tuple(
        NetworkEvent(
            timestamp=timestamp,
            node="a",
            channel=0,
        )
        for timestamp, symbol
        in enumerate(word)
        if symbol
    )


def runtime_trace(
    network,
    word,
):
    result = run_core_network(
        network,
        external_events(
            word
        ),
    )

    return tuple(
        (
            event.timestamp,
            event.node,
            event.channel,
        )
        for event
        in result.terminal_outputs
    )


def machine_trace(
    machine: TemporalMachine,
    word,
):
    state = machine.initial

    output = []

    timestamp = 0

    def record(
        step_output,
        current_timestamp,
    ):
        for (
            node,
            channel,
            multiplicity,
        ) in step_output:
            output.extend(
                (
                    current_timestamp,
                    node,
                    channel,
                )
                for _ in range(
                    multiplicity
                )
            )

    for symbol in word:
        step = machine.step(
            state,
            symbol,
        )

        record(
            step.output,
            timestamp,
        )

        state = step.state
        timestamp += 1

    #
    # Flush already-scheduled network events.
    #
    while state.pending:
        step = machine.step(
            state,
            0,
        )

        record(
            step.output,
            timestamp,
        )

        state = step.state
        timestamp += 1

    return tuple(
        sorted(
            output
        )
    )


def bridge_check(
    networks,
):
    words = tuple(
        words_up_to(
            BRIDGE_MAX_HORIZON
        )
    )

    checks = 0

    for label, network in networks:
        machine = TemporalMachine(
            network
        )

        for word in words:
            expected = runtime_trace(
                network,
                word,
            )

            actual = machine_trace(
                machine,
                word,
            )

            checks += 1

            if expected != actual:
                return (
                    checks,
                    (
                        label,
                        word,
                        expected,
                        actual,
                    ),
                )

    return (
        checks,
        None,
    )


def decay_saturation_audit():
    """
    Independently verify the selected D node's age saturation.

    For every 8-bit raw value and input multiplicity 1 or 2, compare
    delta=8 with all larger tested deltas.

    Since ShiftDecay(1) at delta>=8 annihilates every 8-bit raw value,
    these executions should be identical.
    """

    program = decay_program()

    checks = 0

    for raw in range(
        CONFIG.max_raw + 1
    ):
        for multiplicity in (
            1,
            2,
        ):
            channels = (
                (0,)
                * multiplicity
            )

            reference = run_core_batch(
                CONFIG,
                program,
                timestamp=8,
                channels=channels,
                initial_raw=raw,
                previous_timestamp=0,
            )

            reference_obs = (
                tuple(
                    channel
                    for _, channel
                    in reference.output.as_pairs()
                ),
                reference.final_raw,
                reference.final_guard,
            )

            for delta in range(
                9,
                17,
            ):
                candidate = run_core_batch(
                    CONFIG,
                    program,
                    timestamp=delta,
                    channels=channels,
                    initial_raw=raw,
                    previous_timestamp=0,
                )

                candidate_obs = (
                    tuple(
                        channel
                        for _, channel
                        in candidate.output.as_pairs()
                    ),
                    candidate.final_raw,
                    candidate.final_guard,
                )

                checks += 1

                if (
                    candidate_obs
                    != reference_obs
                ):
                    return (
                        checks,
                        (
                            raw,
                            multiplicity,
                            delta,
                            reference_obs,
                            candidate_obs,
                        ),
                    )

    return (
        checks,
        None,
    )


def distinguish_states(
    machine: TemporalMachine,
    left: TemporalState,
    right: TemporalState,
):
    initial_pair = (
        left,
        right,
    )

    words = {
        initial_pair: ()
    }

    queue = deque(
        (
            initial_pair,
        )
    )

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

        for symbol in INPUT_ALPHABET:
            left_step = machine.step(
                left_state,
                symbol,
            )

            right_step = machine.step(
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
                return StateWitness(
                    word=witness,
                    left_output=(
                        left_step.output
                    ),
                    right_output=(
                        right_step.output
                    ),
                    explored_pairs=explored,
                )

            pair = (
                left_step.state,
                right_step.state,
            )

            if pair in words:
                continue

            words[
                pair
            ] = witness

            queue.append(
                pair
            )

    return None


def age_blind_key(
    state: TemporalState,
):
    return (
        state.raws,
        state.pending,
    )


def find_age_witness(
    networks,
):
    candidate_groups = 0
    state_pairs_checked = 0

    for label, network in networks:
        machine = TemporalMachine(
            network
        )

        groups = defaultdict(
            list
        )

        for state in (
            machine.reachable_states()
        ):
            groups[
                age_blind_key(
                    state
                )
            ].append(
                state
            )

        for states in groups.values():
            if len(states) < 2:
                continue

            distinct_ages = {
                state.ages
                for state in states
            }

            if len(distinct_ages) < 2:
                continue

            candidate_groups += 1

            for left, right in combinations(
                states,
                2,
            ):
                if (
                    left.ages
                    == right.ages
                ):
                    continue

                state_pairs_checked += 1

                witness = distinguish_states(
                    machine,
                    left,
                    right,
                )

                if witness is None:
                    continue

                return {
                    "label": label,
                    "left": left,
                    "right": right,
                    "witness": witness,
                    "candidate_groups": (
                        candidate_groups
                    ),
                    "state_pairs_checked": (
                        state_pairs_checked
                    ),
                }

    return {
        "label": None,
        "candidate_groups": (
            candidate_groups
        ),
        "state_pairs_checked": (
            state_pairs_checked
        ),
    }


def main() -> None:
    print(
        "SPK NETWORK TEMPORAL STATE v0"
    )

    print(
        "node types: R,D"
    )

    print(
        "D = "
        "SHIFT1;ACC16(0);CMP19;"
        "EMIT7;RESET0"
    )

    print(
        "edge slots: a->b, a->c, b->c"
    )

    print(
        "edge delays: absent,1,2"
    )

    print(
        "external alphabet: {0,1}"
    )

    networks = enumerate_networks()

    print(
        f"typed networks: "
        f"{len(networks)}"
    )

    example = make_nodes(
        "D",
        "D",
    )

    print()
    print(
        "age saturation caps:"
    )

    for node in example:
        print(
            f"    {node.name}: "
            f"{age_cap_for_node(node)}"
        )

    #
    # --------------------------------------------------------------
    # Local saturation check
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "TEMPORAL SATURATION AUDIT"
    )
    print(
        "=" * 88
    )

    (
        saturation_checks,
        saturation_failure,
    ) = decay_saturation_audit()

    print(
        f"comparisons: "
        f"{saturation_checks}"
    )

    if saturation_failure is not None:
        print(
            f"failure: "
            f"{saturation_failure}"
        )

        raise SystemExit(1)

    print(
        "mismatches: 0"
    )

    #
    # --------------------------------------------------------------
    # Independent bridge
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "RELATIVE-AGE / RUNTIME BRIDGE"
    )
    print(
        "=" * 88
    )

    (
        bridge_checks,
        bridge_failure,
    ) = bridge_check(
        networks
    )

    print(
        f"maximum horizon: "
        f"{BRIDGE_MAX_HORIZON}"
    )

    print(
        f"runtime comparisons: "
        f"{bridge_checks}"
    )

    if bridge_failure is not None:
        (
            label,
            word,
            expected,
            actual,
        ) = bridge_failure

        print()
        print(
            "BRIDGE FAILURE"
        )

        print(
            f"network: {label}"
        )

        print(
            f"word: {word}"
        )

        print(
            f"runtime: {expected}"
        )

        print(
            f"relative-age machine: "
            f"{actual}"
        )

        raise SystemExit(1)

    print(
        "runtime mismatches: 0"
    )

    #
    # --------------------------------------------------------------
    # Reachable state census
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "TEMPORAL REACHABLE STATE CENSUS"
    )
    print(
        "=" * 88
    )

    counts = []

    temporal_networks = 0

    for _, network in networks:
        machine = TemporalMachine(
            network
        )

        states = (
            machine.reachable_states()
        )

        counts.append(
            len(states)
        )

        if any(
            cap > 0
            for cap
            in machine.age_caps.values()
        ):
            temporal_networks += 1

    print(
        f"networks containing D: "
        f"{temporal_networks}"
    )

    print(
        f"minimum reachable states: "
        f"{min(counts)}"
    )

    print(
        f"maximum reachable states: "
        f"{max(counts)}"
    )

    print(
        f"total reachable states: "
        f"{sum(counts)}"
    )

    distribution = Counter(
        counts
    )

    print()
    print(
        "state-count distribution:"
    )

    for count in sorted(
        distribution
    ):
        print(
            f"    {count:5d}: "
            f"{distribution[count]} networks"
        )

    #
    # --------------------------------------------------------------
    # Does age contain semantic information?
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "AGE NECESSITY SEARCH"
    )
    print(
        "=" * 88
    )

    result = find_age_witness(
        networks
    )

    if result[
        "label"
    ] is None:
        print(
            "No semantic age witness found."
        )

        print(
            f"age-collision groups checked: "
            f"{result['candidate_groups']}"
        )

        print(
            f"state pairs checked: "
            f"{result['state_pairs_checked']}"
        )

        raise SystemExit(2)

    witness = result[
        "witness"
    ]

    left = result[
        "left"
    ]

    right = result[
        "right"
    ]

    print(
        "AGE IS SEMANTICALLY OBSERVABLE"
    )

    print()
    print(
        "network:"
    )

    print(
        f"    {result['label']}"
    )

    print()
    print(
        "same raw + pending projection:"
    )

    print(
        f"    raws="
        f"{left.raws}"
    )

    print(
        f"    pending="
        f"{left.pending}"
    )

    print()
    print(
        "different relative ages:"
    )

    print(
        f"    L="
        f"{left.ages}"
    )

    print(
        f"    R="
        f"{right.ages}"
    )

    print()
    print(
        "shortest distinguishing "
        "future word:"
    )

    print(
        "    "
        + "".join(
            map(
                str,
                witness.word,
            )
        )
    )

    print(
        f"L output at distinction: "
        f"{witness.left_output}"
    )

    print(
        f"R output at distinction: "
        f"{witness.right_output}"
    )

    print(
        f"product-state pairs explored: "
        f"{witness.explored_pairs}"
    )

    print(
        f"age-collision groups examined: "
        f"{result['candidate_groups']}"
    )

    print(
        f"state pairs examined: "
        f"{result['state_pairs_checked']}"
    )

    #
    # --------------------------------------------------------------
    # Checkpoint
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
        "absolute timestamp required: NO"
    )

    print(
        "bounded relative age sufficient "
        "for tested runtime bridge: YES"
    )

    print(
        "relative age semantically "
        "observable: YES"
    )

    print(
        "TEMPORAL STATE v0 "
        "FINITE CHECKPOINT: PASS"
    )

    print()
    print(
        "No universal temporal-state "
        "completeness claim."
    )


if __name__ == "__main__":
    main()
