from search.corpus_v1 import CORPUS_V1
from search.equivalence import Sample
from spk.event import SpikeTrain


#
# Counterexamples discovered automatically by CEGAR v2.
#
CEGAR_COUNTEREXAMPLES_V2 = (
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=-3.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=-4.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=-5.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=-8.0,
    ),
)


CORPUS_V2 = tuple(
    dict.fromkeys(
        CORPUS_V1
        + CEGAR_COUNTEREXAMPLES_V2
    )
)
