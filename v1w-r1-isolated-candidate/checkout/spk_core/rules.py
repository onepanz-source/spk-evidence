from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from functools import wraps


class RuleValidity(str, Enum):
    RUNTIME = "runtime"
    DOMAIN = "domain"


class RuleLayer(str, Enum):
    CORE = "core"
    SEMANTIC = "semantic"


class DomainPremiseKind(str, Enum):
    SOURCE_DEFINED = "source_defined"
    TARGET_DEFINED = "target_defined"
    BOTH_DEFINED = "both_defined"
    ABSTRACT_BOUND = "abstract_bound"


@dataclass(
    frozen=True,
    slots=True,
)
class RuleSpec:
    rule_ids: tuple[str, ...]
    helper: str
    validity: RuleValidity
    layer: RuleLayer
    domain_premise: DomainPremiseKind | None = None

    def __post_init__(self):
        if (
            self.validity is RuleValidity.RUNTIME
            and self.domain_premise is not None
        ):
            raise ValueError(
                "RUNTIME rule must not declare "
                "a DOMAIN premise"
            )

        if (
            self.validity is RuleValidity.DOMAIN
            and self.domain_premise is None
        ):
            raise ValueError(
                "DOMAIN rule must declare "
                "a DOMAIN premise"
            )


RULE_SPECS: tuple[RuleSpec, ...] = (
    #
    # Core runtime rules.
    #
    RuleSpec(
        ("L-ACC-01",),
        "_remove_zero_acc",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-ACC-02", "L-ACC-03"),
        "_normalize_acc_runs",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-CMP-01",),
        "_remove_redundant_repeated_compares",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-CMP-02", "L-GUARD-03"),
        "_normalize_false_compare_after_reset",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-EMIT-01",),
        "_move_emit_left",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-EMIT-02",),
        "_sort_emit_runs",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-GUARD-01",),
        "_remove_dead_compares",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-GUARD-02",),
        "_remove_false_guard_prefix",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-RESET-01",),
        "_collapse_adjacent_resets",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-TIME-01",),
        "_commute_zero_reset_across_shift",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-TIME-02",),
        "_remove_shift_between_cmp1_and_reset0",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-TIME-03",),
        "_remove_shift_when_state_known_zero",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-TIME-05",),
        "_sink_known_false_compare_across_shift",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("L-TIME-06",),
        "_normalize_shift_decay_runs",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),

    #
    # Core domain-conditioned rules.
    #
    RuleSpec(
        ("L-ACC-04",),
        "_pull_saturated_acc_across_compare",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("D-ACC-03",),
        "_cap_saturated_acc_before_guarded_reset",
        RuleValidity.DOMAIN,
        RuleLayer.CORE,
        DomainPremiseKind.SOURCE_DEFINED,
    ),
    RuleSpec(
        ("D-RESET-01",),
        "_remove_shadowed_resets",
        RuleValidity.DOMAIN,
        RuleLayer.CORE,
        DomainPremiseKind.BOTH_DEFINED,
    ),
    RuleSpec(
        ("L-TIME-07",),
        "_cap_shift_before_zero_reset_from_compare_bound",
        RuleValidity.RUNTIME,
        RuleLayer.CORE,
    ),
    RuleSpec(
        ("D-TIME-05",),
        "_remove_pre_acc_shift_under_cmp1_reset0",
        RuleValidity.DOMAIN,
        RuleLayer.CORE,
        DomainPremiseKind.TARGET_DEFINED,
    ),
    RuleSpec(
        ("D-ZERO-01",),
        "_strip_state_before_lsb_annihilator",
        RuleValidity.DOMAIN,
        RuleLayer.CORE,
        DomainPremiseKind.SOURCE_DEFINED,
    ),

    #
    # Semantic runtime rules.
    #
    RuleSpec(
        ("L-COUNT-01",),
        "_normalize_shared_count_cmp1_acc_commute",
        RuleValidity.RUNTIME,
        RuleLayer.SEMANTIC,
    ),
    RuleSpec(
        ("L-CTRL-01",),
        "_normalize_cmp_emit_runs",
        RuleValidity.RUNTIME,
        RuleLayer.SEMANTIC,
    ),
    RuleSpec(
        ("L-CTRL-02",),
        "_normalize_emit_reset_partition",
        RuleValidity.RUNTIME,
        RuleLayer.SEMANTIC,
    ),

    #
    # Semantic domain-conditioned rules.
    #
    RuleSpec(
        ("D-ACC-01",),
        "_normalize_positive_acc_before_cmp1_zero_reset",
        RuleValidity.DOMAIN,
        RuleLayer.SEMANTIC,
        DomainPremiseKind.SOURCE_DEFINED,
    ),
    RuleSpec(
        ("D-COUNT-01",),
        "_normalize_shared_count_pre_shift_acc",
        RuleValidity.DOMAIN,
        RuleLayer.SEMANTIC,
        DomainPremiseKind.SOURCE_DEFINED,
    ),
    RuleSpec(
        ("D-TIME-01",),
        "_normalize_temporal_shift_width",
        RuleValidity.DOMAIN,
        RuleLayer.SEMANTIC,
        DomainPremiseKind.ABSTRACT_BOUND,
    ),
    RuleSpec(
        ("L-TIME-08",),
        "_normalize_temporal_cmp2_barrier",
        RuleValidity.RUNTIME,
        RuleLayer.SEMANTIC,
    ),
    RuleSpec(
        ("L-TIME-09",),
        "_normalize_temporal_guarded_reset_commute",
        RuleValidity.RUNTIME,
        RuleLayer.SEMANTIC,
    ),
    RuleSpec(
        ("D-ZERO-02",),
        "_remove_dead_state_before_zero_barrier",
        RuleValidity.DOMAIN,
        RuleLayer.SEMANTIC,
        DomainPremiseKind.SOURCE_DEFINED,
    ),
)


def rule_specs(
    *,
    validity: RuleValidity | None = None,
    layer: RuleLayer | None = None,
) -> tuple[RuleSpec, ...]:
    return tuple(
        spec
        for spec in RULE_SPECS
        if (
            validity is None
            or spec.validity is validity
        )
        and (
            layer is None
            or spec.layer is layer
        )
    )


def helper_names(
    *,
    validity: RuleValidity | None = None,
    layer: RuleLayer | None = None,
) -> tuple[str, ...]:
    return tuple(
        spec.helper
        for spec in rule_specs(
            validity=validity,
            layer=layer,
        )
    )


def rule_ids() -> tuple[str, ...]:
    return tuple(
        rule_id
        for spec in RULE_SPECS
        for rule_id in spec.rule_ids
    )


class CanonicalizationProfile(str, Enum):
    FULL = "full"
    RUNTIME = "runtime"


_ACTIVE_PROFILE: ContextVar[CanonicalizationProfile] = ContextVar(
    "spk_core_canonicalization_profile",
    default=CanonicalizationProfile.FULL,
)



#
# DOMAIN rules are fail-closed.
#
# FULL selects the complete rule vocabulary, but DOMAIN rewrites still
# require explicit activation.  This temporary capability is used only
# by proof/search harnesses and historical DOMAIN tests while executable
# Gamma_r predicates are being implemented.
#
_DOMAIN_RULES_ENABLED: ContextVar[bool] = ContextVar(
    "spk_core_domain_rules_enabled",
    default=False,
)


#
# Verified DOMAIN authorization is deliberately private to the package.
#
# Public callers must obtain it through a concrete verifier such as
# FiniteExecutionDomain.  unchecked_domain_rules() remains the explicit
# proof/search bypass.
#
_ACTIVE_DOMAIN_AUTHORIZER: ContextVar[object | None] = ContextVar(
    "spk_core_domain_authorizer",
    default=None,
)


@contextmanager
def _verified_domain_authorizer(
    authorizer,
):
    if not callable(authorizer):
        raise TypeError(
            "DOMAIN authorizer must be callable"
        )

    token = _ACTIVE_DOMAIN_AUTHORIZER.set(
        authorizer
    )

    try:
        yield
    finally:
        _ACTIVE_DOMAIN_AUTHORIZER.reset(
            token
        )


def _domain_spec_for_helper(
    helper: str,
) -> RuleSpec:
    matches = tuple(
        spec
        for spec in RULE_SPECS
        if (
            spec.validity is RuleValidity.DOMAIN
            and spec.helper == helper
        )
    )

    if len(matches) != 1:
        raise AssertionError(
            f"expected one DOMAIN RuleSpec "
            f"for helper {helper!r}, "
            f"found {len(matches)}"
        )

    return matches[0]


@contextmanager
def canonicalization_profile(
    profile: CanonicalizationProfile,
):
    token = _ACTIVE_PROFILE.set(profile)

    try:
        yield
    finally:
        _ACTIVE_PROFILE.reset(token)


@contextmanager
def unchecked_domain_rules():
    """
    Explicit temporary opt-in for DOMAIN rewrites.

    This is not evidence that any Gamma_r premise holds.

    Intended only for proof/search harnesses and migration of
    historical DOMAIN-specific tests.
    """

    token = _DOMAIN_RULES_ENABLED.set(
        True
    )

    try:
        yield
    finally:
        _DOMAIN_RULES_ENABLED.reset(
            token
        )


def _domain_rules_enabled() -> bool:
    return (
        _ACTIVE_PROFILE.get()
        is CanonicalizationProfile.FULL
        and _DOMAIN_RULES_ENABLED.get()
    )


def domain_rule(function):
    """
    DOMAIN rewrite over an instruction sequence.

    Default behavior is fail-closed.

    A candidate may execute only under either:

        - unchecked_domain_rules(), for proof/search harnesses; or
        - a verified package authorizer.

    Current DOMAIN instruction helpers may optionally receive CoreConfig
    as their first extra argument.
    """

    spec = _domain_spec_for_helper(
        function.__name__
    )

    @wraps(function)
    def wrapped(
        instructions,
        *args,
        **kwargs,
    ):
        if (
            _ACTIVE_PROFILE.get()
            is not CanonicalizationProfile.FULL
        ):
            return instructions

        if _DOMAIN_RULES_ENABLED.get():
            return function(
                instructions,
                *args,
                **kwargs,
            )

        authorizer = (
            _ACTIVE_DOMAIN_AUTHORIZER.get()
        )

        if authorizer is None:
            return instructions

        candidate = function(
            instructions,
            *args,
            **kwargs,
        )

        if candidate == instructions:
            return instructions

        from .isa import CoreProgram

        source_program = CoreProgram(
            tuple(instructions)
        )

        target_program = CoreProgram(
            tuple(candidate)
        )

        config = kwargs.get(
            "config"
        )

        if (
            config is None
            and args
        ):
            config = args[0]

        if authorizer(
            spec,
            source_program,
            target_program,
            config,
        ):
            return candidate

        return instructions

    return wrapped


def domain_program_rule(function):
    """
    DOMAIN rewrite over CoreProgram.

    Candidate execution is separated from candidate authorization.
    """

    spec = _domain_spec_for_helper(
        function.__name__
    )

    @wraps(function)
    def wrapped(
        program,
        *args,
        **kwargs,
    ):
        if (
            _ACTIVE_PROFILE.get()
            is not CanonicalizationProfile.FULL
        ):
            return program

        if _DOMAIN_RULES_ENABLED.get():
            return function(
                program,
                *args,
                **kwargs,
            )

        authorizer = (
            _ACTIVE_DOMAIN_AUTHORIZER.get()
        )

        if authorizer is None:
            return program

        candidate = function(
            program,
            *args,
            **kwargs,
        )

        if candidate == program:
            return program

        if authorizer(
            spec,
            program,
            candidate,
            None,
        ):
            return candidate

        return program

    return wrapped


def domain_config_program_rule(function):
    """
    DOMAIN rewrite with signature helper(config, program).

    The concrete config is part of authorization because config-sensitive
    matcher facts must use the same semantics as the evidence scope.
    """

    spec = _domain_spec_for_helper(
        function.__name__
    )

    @wraps(function)
    def wrapped(
        config,
        program,
        *args,
        **kwargs,
    ):
        if (
            _ACTIVE_PROFILE.get()
            is not CanonicalizationProfile.FULL
        ):
            return program

        if _DOMAIN_RULES_ENABLED.get():
            return function(
                config,
                program,
                *args,
                **kwargs,
            )

        authorizer = (
            _ACTIVE_DOMAIN_AUTHORIZER.get()
        )

        if authorizer is None:
            return program

        candidate = function(
            config,
            program,
            *args,
            **kwargs,
        )

        if candidate == program:
            return program

        if authorizer(
            spec,
            program,
            candidate,
            config,
        ):
            return candidate

        return program

    return wrapped
