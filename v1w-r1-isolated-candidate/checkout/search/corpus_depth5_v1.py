from __future__ import annotations

import math

from search.corpus_multidecay_v1 import (
    CORPUS_MULTIDECAY_V1,
)
from search.equivalence import Sample
from spk.event import SpikeTrain


DEPTH5_COUNTEREXAMPLES_V1 = (
    Sample(
        SpikeTrain.from_pairs([(0, 0)]),
        initial_x=-6.0,
    ),
    Sample(
        SpikeTrain.from_pairs([(0, 0)]),
        initial_x=-7.0,
    ),

    Sample(
        SpikeTrain.from_pairs([(1, 1)]),
        initial_x=math.exp(3.0) * 1.001,
    ),
    Sample(
        SpikeTrain.from_pairs([(1, 1)]),
        initial_x=2.0 * math.exp(3.0) * 1.001,
    ),
    Sample(
        SpikeTrain.from_pairs([(1, 1)]),
        initial_x=2.0 * math.exp(2.5) * 1.001,
    ),

    Sample(
        SpikeTrain.from_pairs([(0, 0)]),
        initial_x=-4.0,
    ),
    Sample(
        SpikeTrain.from_pairs([(0, 0)]),
        initial_x=-5.0,
    ),

    Sample(
        SpikeTrain.from_pairs(
            [
                (0, 0),
                (0, 0),
            ]
        ),
        initial_x=-4.0,
    ),

    Sample(
        SpikeTrain.from_pairs([(0, 0)]),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [
                (0, 0),
                (0, 0),
            ]
        ),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs([(0, 0)]),
        initial_x=1.0,
    ),
)


CORPUS_DEPTH5_V1 = tuple(
    dict.fromkeys(
        CORPUS_MULTIDECAY_V1
        + DEPTH5_COUNTEREXAMPLES_V1
    )
)
