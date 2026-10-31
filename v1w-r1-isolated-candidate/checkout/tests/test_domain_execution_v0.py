from __future__ import annotations

import pytest

from spk.event import SpikeTrain

from spk_core.domain import (
    ExecutionCase,
    FiniteExecutionDomain,
    definedness_pairs,
    finite_domain_satisfies,
)
from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreProgram,
    CoreReset,
)
from spk_core.rules import DomainPremiseKind


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


def train(*pairs):
    return SpikeTrain.from_pairs(
        pairs
    )


def domain(
    *cases: ExecutionCase,
):
    return FiniteExecutionDomain(
        config=CONFIG,
        cases=cases,
    )


def test_finite_domain_rejects_empty_case_set():
    with pytest.raises(
        ValueError,
        match="at least one case",
    ):
        FiniteExecutionDomain(
            config=CONFIG,
            cases=(),
        )


def test_finite_domain_rejects_invalid_initial_raw():
    with pytest.raises(
        ValueError,
        match="outside",
    ):
        domain(
            ExecutionCase(
                train=train(),
                initial_raw=256,
            ),
        )


def test_source_defined_premise():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    target = CoreProgram(
        ()
    )

    d = domain(
        ExecutionCase(
            train=train(
                (0, 0),
            ),
            initial_raw=254,
        ),
    )

    assert finite_domain_satisfies(
        DomainPremiseKind.SOURCE_DEFINED,
        source,
        target,
        d,
    )


def test_source_defined_can_fail():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    target = CoreProgram(
        ()
    )

    d = domain(
        ExecutionCase(
            train=train(
                (0, 0),
            ),
            initial_raw=255,
        ),
    )

    assert not finite_domain_satisfies(
        DomainPremiseKind.SOURCE_DEFINED,
        source,
        target,
        d,
    )


def test_target_defined_premise():
    source = CoreProgram(
        ()
    )

    target = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    d = domain(
        ExecutionCase(
            train=train(
                (0, 0),
            ),
            initial_raw=254,
        ),
    )

    assert finite_domain_satisfies(
        DomainPremiseKind.TARGET_DEFINED,
        source,
        target,
        d,
    )


def test_both_defined_distinguishes_reverse_overflow():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=255,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    target = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    d = domain(
        ExecutionCase(
            train=train(
                (0, 0),
            ),
            initial_raw=1,
        ),
    )

    pairs = definedness_pairs(
        source,
        target,
        d,
    )

    assert len(pairs) == 1
    assert not pairs[0].source_defined
    assert pairs[0].target_defined

    assert not finite_domain_satisfies(
        DomainPremiseKind.BOTH_DEFINED,
        source,
        target,
        d,
    )


def test_abstract_bound_cannot_be_faked_by_runtime_cases():
    source = CoreProgram(())
    target = CoreProgram(())

    d = domain(
        ExecutionCase(
            train=train(),
        ),
    )

    with pytest.raises(
        ValueError,
        match="internally derived",
    ):
        finite_domain_satisfies(
            DomainPremiseKind.ABSTRACT_BOUND,
            source,
            target,
            d,
        )
