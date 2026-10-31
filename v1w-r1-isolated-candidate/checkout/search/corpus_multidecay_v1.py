from __future__ import annotations

import math

from search.corpus_decay_v1 import CORPUS_DECAY_V1
from search.equivalence import Sample
from spk.event import SpikeTrain


MULTIDECAY_COUNTEREXAMPLES_V1 = (
    #
    # delta = 0: DECAY is the identity.
    #
    Sample(
        SpikeTrain.from_pairs(
            [(0, 1)]
        ),
        initial_x=1.0,
    ),

    Sample(
        SpikeTrain.from_pairs(
            [(0, 1)]
        ),
        initial_x=2.0,
    ),

    #
    # delta = 0 with channel 0, so ACC participates.
    #
    Sample(
        SpikeTrain.from_pairs(
            [(0, 0)]
        ),
        initial_x=2.0,
    ),

    #
    # Critical threshold preimage:
    #
    #     2 * exp(2) * exp(-2) = 2
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 1)]
        ),
        initial_x=2.0 * math.exp(2.0),
    ),
)


CORPUS_MULTIDECAY_V1 = tuple(
    dict.fromkeys(
        CORPUS_DECAY_V1
        + MULTIDECAY_COUNTEREXAMPLES_V1
    )
)
