from __future__ import annotations

from collections import Counter

import pytest

from spk_core.rules import (
    DomainPremiseKind,
    RuleLayer,
    RuleSpec,
    RuleValidity,
    rule_specs,
)


EXPECTED_DOMAIN_PREMISES = {
    "D-ACC-03": DomainPremiseKind.SOURCE_DEFINED,
    "D-RESET-01": DomainPremiseKind.BOTH_DEFINED,
    "D-TIME-05": DomainPremiseKind.TARGET_DEFINED,
    "D-ZERO-01": DomainPremiseKind.SOURCE_DEFINED,
    "D-ACC-01": DomainPremiseKind.SOURCE_DEFINED,
    "D-COUNT-01": DomainPremiseKind.SOURCE_DEFINED,
    "D-TIME-01": DomainPremiseKind.ABSTRACT_BOUND,
    "D-ZERO-02": DomainPremiseKind.SOURCE_DEFINED,
}


def test_runtime_rules_have_no_domain_premise():
    runtime = rule_specs(
        validity=RuleValidity.RUNTIME,
    )

    assert runtime

    assert all(
        spec.domain_premise is None
        for spec in runtime
    )


def test_domain_rules_have_exact_premise_registry():
    domain = rule_specs(
        validity=RuleValidity.DOMAIN,
    )

    actual = {}

    for spec in domain:
        assert spec.domain_premise is not None

        for rule_id in spec.rule_ids:
            actual[rule_id] = (
                spec.domain_premise
            )

    assert actual == EXPECTED_DOMAIN_PREMISES


def test_domain_premise_distribution():
    domain = rule_specs(
        validity=RuleValidity.DOMAIN,
    )

    counts = Counter(
        spec.domain_premise
        for spec in domain
    )

    assert counts == {
        DomainPremiseKind.SOURCE_DEFINED: 5,
        DomainPremiseKind.TARGET_DEFINED: 1,
        DomainPremiseKind.BOTH_DEFINED: 1,
        DomainPremiseKind.ABSTRACT_BOUND: 1,
    }


def test_runtime_rule_rejects_domain_premise():
    with pytest.raises(
        ValueError,
        match="RUNTIME rule must not declare",
    ):
        RuleSpec(
            rule_ids=("L-TEST-01",),
            helper="_test",
            validity=RuleValidity.RUNTIME,
            layer=RuleLayer.CORE,
            domain_premise=(
                DomainPremiseKind.SOURCE_DEFINED
            ),
        )


def test_domain_rule_requires_domain_premise():
    with pytest.raises(
        ValueError,
        match="DOMAIN rule must declare",
    ):
        RuleSpec(
            rule_ids=("D-TEST-01",),
            helper="_test",
            validity=RuleValidity.DOMAIN,
            layer=RuleLayer.CORE,
        )
