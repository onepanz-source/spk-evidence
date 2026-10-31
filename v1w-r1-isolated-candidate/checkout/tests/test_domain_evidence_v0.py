from __future__ import annotations

import pytest

from spk.event import SpikeTrain

from spk_core.domain import (
    ExecutionCase,
    FiniteDomainPremiseEvidence,
    FiniteExecutionDomain,
    verify_finite_domain_premise,
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


def test_evidence_cannot_be_constructed_directly():
    with pytest.raises(
        TypeError,
        match="cannot be constructed directly",
    ):
        FiniteDomainPremiseEvidence()


def test_source_defined_evidence_is_issued():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    target = CoreProgram(())

    d = domain(
        ExecutionCase(
            train=train(
                (0, 0),
            ),
            initial_raw=254,
        ),
    )

    evidence = verify_finite_domain_premise(
        "D-ACC-03",
        source,
        target,
        d,
    )

    assert evidence.rule_id == "D-ACC-03"
    assert evidence.premise is (
        DomainPremiseKind.SOURCE_DEFINED
    )
    assert evidence.source == source
    assert evidence.target == target
    assert evidence.domain == d


def test_source_defined_evidence_is_refused():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    target = CoreProgram(())

    d = domain(
        ExecutionCase(
            train=train(
                (0, 0),
            ),
            initial_raw=255,
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not satisfy source_defined",
    ):
        verify_finite_domain_premise(
            "D-ACC-03",
            source,
            target,
            d,
        )


def test_target_defined_evidence_uses_registry_premise():
    source = CoreProgram(())

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

    evidence = verify_finite_domain_premise(
        "D-TIME-05",
        source,
        target,
        d,
    )

    assert evidence.premise is (
        DomainPremiseKind.TARGET_DEFINED
    )


def test_both_defined_evidence_rejects_reverse_overflow():
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

    with pytest.raises(
        ValueError,
        match="does not satisfy both_defined",
    ):
        verify_finite_domain_premise(
            "D-RESET-01",
            source,
            target,
            d,
        )


def test_abstract_bound_cannot_receive_runtime_evidence():
    program = CoreProgram(())

    d = domain(
        ExecutionCase(
            train=train(),
        ),
    )

    with pytest.raises(
        ValueError,
        match="ABSTRACT_BOUND",
    ):
        verify_finite_domain_premise(
            "D-TIME-01",
            program,
            program,
            d,
        )


def test_runtime_rule_id_is_not_domain_evidence():
    program = CoreProgram(())

    d = domain(
        ExecutionCase(
            train=train(),
        ),
    )

    with pytest.raises(
        ValueError,
        match="unknown DOMAIN rule id",
    ):
        verify_finite_domain_premise(
            "L-ACC-01",
            program,
            program,
            d,
        )


def test_unknown_rule_id_is_refused():
    program = CoreProgram(())

    d = domain(
        ExecutionCase(
            train=train(),
        ),
    )

    with pytest.raises(
        ValueError,
        match="unknown DOMAIN rule id",
    ):
        verify_finite_domain_premise(
            "D-NOT-A-RULE",
            program,
            program,
            d,
        )
