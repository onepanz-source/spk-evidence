from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from spk.event import SpikeTrain

from .isa import (
    CoreConfig,
    CoreProgram,
)
from .rules import (
    DomainPremiseKind,
    RuleSpec,
    RuleValidity,
    _verified_domain_authorizer,
    rule_specs,
)
from .runtime import run_core_program


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionCase:
    """
    One concrete Core execution environment.

    The program is deliberately not part of the case because DOMAIN
    rewrites compare a source program with a candidate target over the
    same execution environment.
    """

    train: SpikeTrain
    initial_raw: int = 0


@dataclass(
    frozen=True,
    slots=True,
)
class FiniteExecutionDomain:
    """
    Explicit finite set of executions under one CoreConfig.

    This is intentionally finite and executable.  It does not pretend
    to represent a symbolic or universal execution domain.
    """

    config: CoreConfig
    cases: tuple[ExecutionCase, ...]

    def __post_init__(self):
        if not self.cases:
            raise ValueError(
                "finite execution domain "
                "must contain at least one case"
            )

        for case in self.cases:
            if not (
                0
                <= case.initial_raw
                <= self.config.max_raw
            ):
                raise ValueError(
                    "execution case initial_raw "
                    f"{case.initial_raw} outside "
                    f"[0,{self.config.max_raw}]"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class DefinednessPair:
    source_defined: bool
    target_defined: bool


def _is_defined(
    config: CoreConfig,
    program: CoreProgram,
    case: ExecutionCase,
) -> bool:
    """
    Definedness means successful Core execution.

    OverflowError is semantic undefinedness for the current Core model.
    Other exceptions are programming/domain errors and must propagate.
    """

    try:
        run_core_program(
            config,
            program,
            case.train,
            initial_raw=case.initial_raw,
        )
    except OverflowError:
        return False

    return True


def definedness_pairs(
    source: CoreProgram,
    target: CoreProgram,
    domain: FiniteExecutionDomain,
) -> tuple[DefinednessPair, ...]:
    return tuple(
        DefinednessPair(
            source_defined=_is_defined(
                domain.config,
                source,
                case,
            ),
            target_defined=_is_defined(
                domain.config,
                target,
                case,
            ),
        )
        for case in domain.cases
    )


def finite_domain_satisfies(
    premise: DomainPremiseKind,
    source: CoreProgram,
    target: CoreProgram,
    domain: FiniteExecutionDomain,
) -> bool:
    """
    Check an externally observable definedness premise over an explicit
    finite execution domain.

    ABSTRACT_BOUND is intentionally excluded: that premise is established
    internally from abstract interpretation, not by enumerating runtime
    executions.
    """

    if premise is DomainPremiseKind.ABSTRACT_BOUND:
        raise ValueError(
            "ABSTRACT_BOUND is internally derived "
            "and cannot be certified by a finite "
            "execution domain"
        )

    pairs = definedness_pairs(
        source,
        target,
        domain,
    )

    if premise is DomainPremiseKind.SOURCE_DEFINED:
        return all(
            pair.source_defined
            for pair in pairs
        )

    if premise is DomainPremiseKind.TARGET_DEFINED:
        return all(
            pair.target_defined
            for pair in pairs
        )

    if premise is DomainPremiseKind.BOTH_DEFINED:
        return all(
            pair.source_defined
            and pair.target_defined
            for pair in pairs
        )

    raise AssertionError(
        f"unknown DOMAIN premise: {premise!r}"
    )


class DomainPremiseUnsatisfied(
    ValueError
):
    """
    Requested finite DOMAIN premise is false on at least one case.
    """

    pass


@dataclass(
    frozen=True,
    slots=True,
    init=False,
)
class FiniteDomainPremiseEvidence:
    """
    Verified evidence that the DOMAIN premise required by one RuleSpec
    holds for one concrete (source, target, finite-domain) tuple.

    This object does NOT prove that target was produced from source by
    the named rewrite helper.  That relation must be established by the
    rewrite enforcement layer itself.
    """

    rule_id: str
    helper: str
    premise: DomainPremiseKind
    source: CoreProgram
    target: CoreProgram
    domain: FiniteExecutionDomain

    def __init__(self, *args, **kwargs):
        raise TypeError(
            "FiniteDomainPremiseEvidence cannot be "
            "constructed directly; use "
            "verify_finite_domain_premise()"
        )

    @classmethod
    def _issue(
        cls,
        *,
        spec: RuleSpec,
        rule_id: str,
        source: CoreProgram,
        target: CoreProgram,
        domain: FiniteExecutionDomain,
    ):
        premise = spec.domain_premise

        if premise is None:
            raise AssertionError(
                "DOMAIN RuleSpec has no premise"
            )

        instance = object.__new__(cls)

        object.__setattr__(
            instance,
            "rule_id",
            rule_id,
        )
        object.__setattr__(
            instance,
            "helper",
            spec.helper,
        )
        object.__setattr__(
            instance,
            "premise",
            premise,
        )
        object.__setattr__(
            instance,
            "source",
            source,
        )
        object.__setattr__(
            instance,
            "target",
            target,
        )
        object.__setattr__(
            instance,
            "domain",
            domain,
        )

        return instance


def _domain_rule_spec(
    rule_id: str,
) -> RuleSpec:
    matches = tuple(
        spec
        for spec in rule_specs(
            validity=RuleValidity.DOMAIN,
        )
        if rule_id in spec.rule_ids
    )

    if not matches:
        raise ValueError(
            f"unknown DOMAIN rule id: "
            f"{rule_id!r}"
        )

    if len(matches) != 1:
        raise AssertionError(
            f"ambiguous DOMAIN rule id: "
            f"{rule_id!r}"
        )

    return matches[0]


def verify_finite_domain_premise(
    rule_id: str,
    source: CoreProgram,
    target: CoreProgram,
    domain: FiniteExecutionDomain,
) -> FiniteDomainPremiseEvidence:
    """
    Verify the premise required by a DOMAIN rule over one explicit
    finite execution domain.

    This certifies Gamma_r only.  It does not certify that `target` is
    the output of the named rewrite helper.

    That second fact will be guaranteed later by the enforcement layer,
    which computes the candidate target itself before requesting
    premise evidence.
    """

    spec = _domain_rule_spec(
        rule_id
    )

    premise = spec.domain_premise

    if premise is None:
        raise AssertionError(
            f"{rule_id}: DOMAIN rule has no premise"
        )

    if premise is DomainPremiseKind.ABSTRACT_BOUND:
        raise ValueError(
            f"{rule_id}: ABSTRACT_BOUND is "
            "internally derived and cannot be "
            "certified by finite runtime evidence"
        )

    if not finite_domain_satisfies(
        premise,
        source,
        target,
        domain,
    ):
        raise DomainPremiseUnsatisfied(
            f"{rule_id}: finite execution domain "
            f"does not satisfy "
            f"{premise.value}"
        )

    return FiniteDomainPremiseEvidence._issue(
        spec=spec,
        rule_id=rule_id,
        source=source,
        target=target,
        domain=domain,
    )


@contextmanager
def verified_finite_domain_rules(
    domain: FiniteExecutionDomain,
):
    """
    Enable DOMAIN rewrites only when their current concrete candidate is
    justified over this finite execution domain.

    Definedness premises are rechecked for every source/candidate pair.

    ABSTRACT_BOUND remains matcher-local: the authorizer only confirms
    that a verified DOMAIN context exists and that any config used by
    the matcher matches this execution domain.
    """

    def authorize(
        spec: RuleSpec,
        source: CoreProgram,
        target: CoreProgram,
        config,
    ) -> bool:
        if (
            config is not None
            and config != domain.config
        ):
            return False

        premise = spec.domain_premise

        if premise is None:
            raise AssertionError(
                "DOMAIN RuleSpec has no premise"
            )

        if (
            premise
            is DomainPremiseKind.ABSTRACT_BOUND
        ):
            return True

        if len(spec.rule_ids) != 1:
            raise AssertionError(
                "finite DOMAIN authorization "
                "requires one rule id per DOMAIN helper"
            )

        try:
            verify_finite_domain_premise(
                spec.rule_ids[0],
                source,
                target,
                domain,
            )
        except DomainPremiseUnsatisfied:
            return False

        return True

    with _verified_domain_authorizer(
        authorize
    ):
        yield
