from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from dataclasses import dataclass

from spk_core.isa import ShiftDecay
from spk_core.runtime import run_core_batch

from search.network_temporal_state_v0 import (
    INPUT_ALPHABET,
    TemporalMachine,
    TemporalState,
    enumerate_networks,
)

from search.network_temporal_minimize_v0 import (
    canonical_minimized_machine,
)


MAX_REACHABLE_STATES = 100_000


@dataclass(
    frozen=True,
    slots=True,
)
class EffectiveState:
    #
    # State already decayed to the current logical tick.
    #
    raws: tuple[
        tuple[str, int],
        ...
    ]

    #
    # Events already in flight.
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
    state: EffectiveState

    output: tuple[
        tuple[str, int, int],
        ...
    ]


def normalize_map(values):
    return tuple(
        sorted(
            values.items()
        )
    )


def normalize_pending(counter):
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


def node_shift_rate(node) -> int:
    """
    Effective-state v0 supports the current R/D fragment:

    - no ShiftDecay; or
    - exactly one ShiftDecay as first instruction.
    """

    shifts = [
        (
            index,
            instruction,
        )
        for index, instruction
        in enumerate(
            node.program.instructions
        )
        if isinstance(
            instruction,
            ShiftDecay,
        )
    ]

    if not shifts:
        return 0

    if len(shifts) != 1:
        raise ValueError(
            "effective-state v0 requires "
            "at most one ShiftDecay"
        )

    index, instruction = shifts[0]

    if index != 0:
        raise ValueError(
            "effective-state v0 requires "
            "ShiftDecay to be the first instruction"
        )

    return instruction.bits_per_tick


class EffectiveMachine:
    """
    Eager-decay representation.

    Instead of storing:

        raw + elapsed age

    store the raw value already decayed to the current logical tick.

    Time still affects the machine, but no explicit age variable is
    retained.
    """

    def __init__(
        self,
        network,
    ):
        self.network = network

        self.nodes = {
            node.name: node
            for node in network.nodes
        }

        self.shift_rates = {
            node.name: (
                node_shift_rate(
                    node
                )
            )
            for node in network.nodes
        }

        outgoing = defaultdict(list)

        for edge in network.edges:
            outgoing[
                (
                    edge.source,
                    edge.source_channel,
                )
            ].append(edge)

        self.outgoing = {
            key: tuple(value)
            for key, value
            in outgoing.items()
        }

        self.initial = EffectiveState(
            raws=normalize_map(
                {
                    node.name: node.initial_raw
                    for node in network.nodes
                }
            ),
            pending=(),
        )

        self._step_cache = {}

    def step(
        self,
        state: EffectiveState,
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
                f"invalid input symbol: {input_symbol}"
            )

        raws = dict(
            state.raws
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
        # Advance already-routed events.
        #
        for (
            offset,
            node,
            channel,
        ), multiplicity in old_pending.items():
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
        # External source event at the current logical tick.
        #
        if input_symbol:
            due[
                (
                    "a",
                    0,
                )
            ] += 1

        node_channels = defaultdict(list)

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

        next_raws = {}

        for node_name in sorted(
            self.nodes
        ):
            node = self.nodes[
                node_name
            ]

            current_raw = raws[
                node_name
            ]

            channels = node_channels.get(
                node_name
            )

            if channels:
                #
                # current_raw already represents the state at NOW.
                #
                # Therefore ShiftDecay must observe delta=0 during
                # this batch.
                #
                result = run_core_batch(
                    node.config,
                    node.program,
                    timestamp=0,
                    channels=tuple(
                        channels
                    ),
                    initial_raw=current_raw,
                    previous_timestamp=0,
                )

                raw_after = result.final_raw

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

            else:
                raw_after = current_raw

            #
            # Move from NOW to the beginning of the next logical tick.
            #
            shift_rate = self.shift_rates[
                node_name
            ]

            if shift_rate:
                raw_after >>= shift_rate

            next_raws[
                node_name
            ] = raw_after

        next_state = EffectiveState(
            raws=normalize_map(
                next_raws
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

    def reachable_states(self):
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

                seen.add(target)

                if (
                    len(seen)
                    > MAX_REACHABLE_STATES
                ):
                    raise RuntimeError(
                        "reachable-state limit exceeded"
                    )

                queue.append(target)

        return frozenset(seen)


def project_temporal_state(
    temporal_machine: TemporalMachine,
    temporal_state: TemporalState,
) -> EffectiveState:
    """
    Candidate quotient:

        (raw, age, pending)
            ->
        (raw decayed to current time, pending)
    """

    raws = dict(
        temporal_state.raws
    )

    ages = dict(
        temporal_state.ages
    )

    effective = {}

    for node_name, raw in raws.items():
        node = temporal_machine.nodes[
            node_name
        ]

        rate = node_shift_rate(
            node
        )

        age = ages[
            node_name
        ]

        if rate:
            raw >>= (
                rate
                * age
            )

        effective[
            node_name
        ] = raw

    return EffectiveState(
        raws=normalize_map(
            effective
        ),
        pending=temporal_state.pending,
    )


def exact_projection_audit(
    network,
):
    """
    Check the commuting diagram on every reachable temporal state:

             temporal
        S  ------------> S'
        |                 |
        q                 q
        |                 |
        v                 v
        E  ------------> E'
             effective

    Outputs must also agree.
    """

    temporal = TemporalMachine(
        network
    )

    effective = EffectiveMachine(
        network
    )

    temporal_states = (
        temporal.reachable_states()
    )

    effective_states = (
        effective.reachable_states()
    )

    projected_states = {
        project_temporal_state(
            temporal,
            state,
        )
        for state in temporal_states
    }

    state_space_match = (
        projected_states
        == set(
            effective_states
        )
    )

    checks = 0

    for temporal_state in temporal_states:
        effective_state = (
            project_temporal_state(
                temporal,
                temporal_state,
            )
        )

        for symbol in INPUT_ALPHABET:
            temporal_step = temporal.step(
                temporal_state,
                symbol,
            )

            effective_step = effective.step(
                effective_state,
                symbol,
            )

            projected_target = (
                project_temporal_state(
                    temporal,
                    temporal_step.state,
                )
            )

            checks += 1

            if (
                temporal_step.output
                != effective_step.output
                or projected_target
                != effective_step.state
            ):
                return (
                    temporal,
                    effective,
                    checks,
                    state_space_match,
                    (
                        temporal_state,
                        effective_state,
                        symbol,
                        temporal_step,
                        effective_step,
                        projected_target,
                    ),
                )

    return (
        temporal,
        effective,
        checks,
        state_space_match,
        None,
    )


def main() -> None:
    print(
        "SPK NETWORK EFFECTIVE TEMPORAL STATE v0"
    )

    print(
        "candidate state: "
        "(effective_raw, pending)"
    )

    print(
        "candidate quotient: "
        "effective_raw = "
        "raw >> (shift_rate * age)"
    )

    networks = enumerate_networks()

    print(
        f"typed networks: "
        f"{len(networks)}"
    )

    temporal_total = 0
    effective_total = 0
    semantic_total = 0

    transition_checks = 0

    projection_failures = 0
    state_space_failures = 0
    canonical_failures = 0

    reduced_by_projection = 0
    reduced_after_projection = 0

    state_count_pairs = Counter()

    first_failure = None

    for index, (
        label,
        network,
    ) in enumerate(
        networks,
        start=1,
    ):
        (
            temporal,
            effective,
            checks,
            state_space_match,
            failure,
        ) = exact_projection_audit(
            network
        )

        transition_checks += checks

        temporal_count = len(
            temporal.reachable_states()
        )

        effective_count = len(
            effective.reachable_states()
        )

        (
            temporal_canonical,
            temporal_blocks,
            _,
            _,
        ) = canonical_minimized_machine(
            temporal
        )

        (
            effective_canonical,
            effective_blocks,
            _,
            _,
        ) = canonical_minimized_machine(
            effective
        )

        semantic_count = len(
            effective_blocks
        )

        temporal_total += temporal_count
        effective_total += effective_count
        semantic_total += semantic_count

        state_count_pairs[
            (
                temporal_count,
                effective_count,
                semantic_count,
            )
        ] += 1

        if effective_count < temporal_count:
            reduced_by_projection += 1

        if semantic_count < effective_count:
            reduced_after_projection += 1

        if not state_space_match:
            state_space_failures += 1

            if first_failure is None:
                first_failure = (
                    "state-space",
                    label,
                )

        if failure is not None:
            projection_failures += 1

            if first_failure is None:
                first_failure = (
                    "transition",
                    label,
                    failure,
                )

        if (
            temporal_canonical
            != effective_canonical
        ):
            canonical_failures += 1

            if first_failure is None:
                first_failure = (
                    "canonical",
                    label,
                )

        if index % 20 == 0:
            print(
                f"networks={index:3d} "
                f"transition_checks="
                f"{transition_checks:6d} "
                f"projection_failures="
                f"{projection_failures} "
                f"canonical_failures="
                f"{canonical_failures}"
            )

    print()
    print(
        "=" * 88
    )
    print(
        "EXACT TEMPORAL PROJECTION"
    )
    print(
        "=" * 88
    )

    print(
        f"reachable temporal states: "
        f"{temporal_total}"
    )

    print(
        f"reachable effective states: "
        f"{effective_total}"
    )

    print(
        f"states removed by raw/age projection: "
        f"{temporal_total - effective_total}"
    )

    print(
        f"networks reduced by projection: "
        f"{reduced_by_projection}"
    )

    print()

    print(
        f"transition homomorphism checks: "
        f"{transition_checks}"
    )

    print(
        f"transition/output mismatches: "
        f"{projection_failures}"
    )

    print(
        f"projected/reachable "
        f"state-space mismatches: "
        f"{state_space_failures}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "SEMANTIC MINIMIZATION AFTER TIME ABSORPTION"
    )
    print(
        "=" * 88
    )

    print(
        f"effective operational states: "
        f"{effective_total}"
    )

    print(
        f"minimal semantic states: "
        f"{semantic_total}"
    )

    print(
        f"additional states quotiented behaviorally: "
        f"{effective_total - semantic_total}"
    )

    print(
        f"networks further reduced after projection: "
        f"{reduced_after_projection}"
    )

    print()

    print(
        f"canonical temporal/effective mismatches: "
        f"{canonical_failures}"
    )

    print()
    print(
        "temporal -> effective -> semantic "
        "state-count distribution:"
    )

    for (
        temporal_count,
        effective_count,
        semantic_count,
    ), count in sorted(
        state_count_pairs.items()
    ):
        print(
            f"    "
            f"{temporal_count:5d} -> "
            f"{effective_count:5d} -> "
            f"{semantic_count:5d}: "
            f"{count:3d} networks"
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

    if first_failure is not None:
        print(
            f"FIRST FAILURE: "
            f"{first_failure}"
        )

        raise SystemExit(1)

    if semantic_total != 718:
        raise AssertionError(
            "semantic-state total changed"
        )

    print(
        "projection transition mismatches: 0"
    )

    print(
        "projection state-space mismatches: 0"
    )

    print(
        "canonical machine mismatches: 0"
    )

    print(
        f"minimal semantic states: "
        f"{semantic_total}"
    )

    print(
        "EFFECTIVE TEMPORAL STATE CHECKPOINT: PASS"
    )

    print()
    print(
        "Interpretation:"
    )

    print(
        "absolute timestamp is unnecessary"
    )

    print(
        "explicit relative age is unnecessary "
        "in this fragment"
    )

    print(
        "time is absorbed into eager state decay"
    )

    print()
    print(
        "No claim beyond the declared R/D fragment."
    )


if __name__ == "__main__":
    main()
