from __future__ import annotations

import math

from search.corpus_v2 import CORPUS_V2
from search.equivalence import Sample
from spk.event import SpikeTrain


#
# Counterexamples discovered by temporal CEGAR.
#
# Values are expressed from the critical threshold preimages where
# practical, instead of being left as unexplained decimal constants.
#
DECAY_COUNTEREXAMPLES_V1 = (
    #
    # 2 * exp(1/2) -- one DECAY reaches threshold 2.
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 1)]
        ),
        initial_x=2.0 * math.exp(0.5),
    ),

    #
    # After two DECAY(2) operations:
    #
    #     x -> 2.002
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 1)]
        ),
        initial_x=2.002 * math.exp(1.0),
    ),

    #
    # One DECAY reaches threshold 1.
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 1)]
        ),
        initial_x=math.exp(0.5),
    ),

    #
    # After three DECAY(2) operations:
    #
    #     x -> 2.002
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 1)]
        ),
        initial_x=2.002 * math.exp(1.5),
    ),

    #
    # Same critical state, but channel 0 activates ACC.
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=2.0 * math.exp(0.5),
    ),

    #
    # After three DECAY(2) operations:
    #
    #     x -> 1.001
    #
    Sample(
        SpikeTrain.from_pairs(
            [(1, 1)]
        ),
        initial_x=1.001 * math.exp(1.5),
    ),
)


CORPUS_DECAY_V1 = tuple(
    dict.fromkeys(
        CORPUS_V2
        + DECAY_COUNTEREXAMPLES_V1
    )
)
