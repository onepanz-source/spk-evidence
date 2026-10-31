from __future__ import annotations

from dataclasses import dataclass

from spk.event import SpikeTrain
from spk.program import Program
from spk.runtime import ExecutionContext
from spk.state import State


@dataclass(frozen=True, slots=True)
class RunResult:
    """
    Immutable result of executing one Program over one SpikeTrain.

    output:
        Canonical output spike train.

    final_state:
        Snapshot of the final persistent state and transient guard.
    """

    output: SpikeTrain
    final_state: tuple[float, bool]


def run_program(
    program: Program,
    train: SpikeTrain,
    *,
    initial_x: float = 0.0,
) -> RunResult:
    """
    Execute an SPK/v0 Program over a complete SpikeTrain.

    Execution rules:

    - input events are processed in timestamp batches;
    - persistent state survives between batches;
    - guard is reset before every batch;
    - first delta is measured from t=0;
    - subsequent deltas are measured from the previous input batch;
    - emitted events are collected into one canonical output SpikeTrain.
    """

    if not isinstance(program, Program):
        raise TypeError(
            "run_program requires a Program"
        )

    if not isinstance(train, SpikeTrain):
        raise TypeError(
            "run_program requires a SpikeTrain"
        )

    state = State(x=initial_x)

    output_events = []

    previous_timestamp = 0

    for batch in train.batches():
        state.begin_batch()

        delta_ticks = (
            batch.timestamp
            - previous_timestamp
        )

        context = ExecutionContext(
            timestamp=batch.timestamp,
            delta_ticks=delta_ticks,
            batch=batch,
            state=state,
            output_events=output_events,
        )

        program(context)

        previous_timestamp = batch.timestamp

    return RunResult(
        output=SpikeTrain(
            tuple(output_events)
        ),
        final_state=state.snapshot(),
    )
