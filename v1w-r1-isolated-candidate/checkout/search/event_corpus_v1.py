from __future__ import annotations

from spk.event import SpikeTrain


EVENT_CORPUS_V1 = (
    #
    # Separating basis.
    #
    {
        "A": SpikeTrain.from_pairs(
            [(0, 0)]
        ),
        "B": SpikeTrain.from_pairs(
            [(0, 1)]
        ),
        "C": SpikeTrain.from_pairs(
            [(0, 2)]
        ),
    },

    #
    # Distinct initial timestamps.
    #
    {
        "A": SpikeTrain.from_pairs(
            [(0, 0)]
        ),
        "B": SpikeTrain.from_pairs(
            [(2, 1)]
        ),
        "C": SpikeTrain.from_pairs(
            [(4, 2)]
        ),
    },

    #
    # Complete collision.
    #
    {
        "A": SpikeTrain.from_pairs(
            [(0, 0)]
        ),
        "B": SpikeTrain.from_pairs(
            [(0, 0)]
        ),
        "C": SpikeTrain.from_pairs(
            [(0, 0)]
        ),
    },

    #
    # Multiplicity.
    #
    {
        "A": SpikeTrain.from_pairs(
            [
                (0, 0),
                (0, 0),
            ]
        ),
        "B": SpikeTrain.from_pairs(
            [
                (1, 0),
                (1, 0),
                (1, 0),
            ]
        ),
        "C": SpikeTrain.from_pairs(
            [(2, 1)]
        ),
    },

    #
    # Empty variable A.
    #
    {
        "A": SpikeTrain(),
        "B": SpikeTrain.from_pairs(
            [(0, 1)]
        ),
        "C": SpikeTrain.from_pairs(
            [(0, 2)]
        ),
    },

    #
    # Empty variable B.
    #
    {
        "A": SpikeTrain.from_pairs(
            [(0, 0)]
        ),
        "B": SpikeTrain(),
        "C": SpikeTrain.from_pairs(
            [(0, 2)]
        ),
    },

    #
    # Multi-event trains.
    #
    {
        "A": SpikeTrain.from_pairs(
            [
                (0, 0),
                (2, 0),
            ]
        ),
        "B": SpikeTrain.from_pairs(
            [
                (1, 1),
                (3, 1),
            ]
        ),
        "C": SpikeTrain.from_pairs(
            [
                (0, 2),
                (3, 2),
            ]
        ),
    },
)
