from search.equivalence import Sample
from spk.event import SpikeTrain


TRAINS = (
    SpikeTrain.from_pairs([]),

    SpikeTrain.from_pairs(
        [(1, 0)]
    ),

    SpikeTrain.from_pairs(
        [(1, 1)]
    ),

    SpikeTrain.from_pairs(
        [
            (1, 0),
            (1, 0),
        ]
    ),

    SpikeTrain.from_pairs(
        [
            (1, 0),
            (1, 1),
        ]
    ),

    SpikeTrain.from_pairs(
        [
            (1, 0),
            (2, 0),
        ]
    ),

    SpikeTrain.from_pairs(
        [
            (1, 0),
            (3, 0),
            (8, 0),
        ]
    ),

    SpikeTrain.from_pairs(
        [
            (1, 1),
            (3, 1),
            (8, 1),
        ]
    ),
)


INITIAL_STATES = (
    -2.0,
    -1.5,
    -1.0,
    -0.5,
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
)


CORPUS_V1 = tuple(
    Sample(
        train=train,
        initial_x=initial_x,
    )
    for train in TRAINS
    for initial_x in INITIAL_STATES
)
