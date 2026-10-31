from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from spk_core.rules import (
    RULE_SPECS,
    RuleLayer,
    RuleValidity,
)


class PremiseKind(str, Enum):
    #
    # Proven local premise:
    #
    #     Def(source) => Def(target)
    #
    SOURCE_DEFINED = (
        "source_defined"
    )

    #
    # Candidate theorem:
    #
    #     Def(source) => Def(target)
    #
    # Therefore the declared successful-source domain may be enough.
    # This is NOT considered proven merely by appearing here.
    #
    SOURCE_DEFINED_CANDIDATE = (
        "source_defined_candidate"
    )

    #
    # Proven local premise:
    #
    #     Def(target) => Def(source)
    #
    TARGET_DEFINED = (
        "target_defined"
    )

    #
    # Finite census contains source-defined / target-overflow
    # witnesses.  Therefore source-definedness alone is known to be
    # insufficient.
    #
    TARGET_DEFINED_REQUIRED = (
        "target_defined_required"
    )

    #
    # Applicability is justified by abstract reachable-state facts,
    # rather than by a generic overflow-domain premise.
    #
    BOTH_DEFINED = (
        "both_defined"
    )

    ABSTRACT_BOUND = (
        "abstract_bound"
    )


class PremiseStatus(str, Enum):
    CANDIDATE = "candidate"
    NECESSARY = "necessary"
    PROVED_LOCAL = "proved_local"
    IMPLEMENTED_MATCHER = "implemented_matcher"


@dataclass(
    frozen=True,
    slots=True,
)
class DomainPremise:
    rule_id: str
    helper: str
    layer: RuleLayer
    kind: PremiseKind
    status: PremiseStatus
    obligation: str


PREMISES = (
    DomainPremise(
        rule_id="D-TIME-05",
        helper="_remove_pre_acc_shift_under_cmp1_reset0",
        layer=RuleLayer.CORE,
        kind=PremiseKind.TARGET_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(target) implies Def(source); "
            "shift-removal dominance proof plus independent finite regression"
        ),
    ),
    DomainPremise(
        rule_id="D-RESET-01",
        helper="_remove_shadowed_resets",
        layer=RuleLayer.CORE,
        kind=PremiseKind.BOTH_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(source) and Def(target) imply observational equivalence; "
            "DO and OD witnesses exclude either unilateral premise"
        ),
    ),
    DomainPremise(
        rule_id="D-ACC-03",
        helper="_cap_saturated_acc_before_guarded_reset",
        layer=RuleLayer.CORE,
        kind=PremiseKind.SOURCE_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(source) implies Def(target); "
            "local monotonicity proof plus independent finite regression"
        ),
    ),
    DomainPremise(
        rule_id="D-ZERO-01",
        helper="_strip_state_before_lsb_annihilator",
        layer=RuleLayer.CORE,
        kind=PremiseKind.SOURCE_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(source) implies Def(target); "
            "local annihilator proof plus independent finite regression"
        ),
    ),
    DomainPremise(
        rule_id="D-COUNT-01",
        helper="_normalize_shared_count_pre_shift_acc",
        layer=RuleLayer.SEMANTIC,
        kind=PremiseKind.SOURCE_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(source) implies Def(target); "
            "shared-count monotonicity proof plus independent finite regression"
        ),
    ),
    DomainPremise(
        rule_id="D-ACC-01",
        helper="_normalize_positive_acc_before_cmp1_zero_reset",
        layer=RuleLayer.SEMANTIC,
        kind=PremiseKind.SOURCE_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(source) implies Def(target); "
            "local monotonicity proof plus independent finite regression"
        ),
    ),
    DomainPremise(
        rule_id="D-ZERO-02",
        helper="_remove_dead_state_before_zero_barrier",
        layer=RuleLayer.SEMANTIC,
        kind=PremiseKind.SOURCE_DEFINED,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "Def(source) implies Def(target); "
            "zero-barrier/dead-guard proof plus independent finite regression"
        ),
    ),
    DomainPremise(
        rule_id="D-TIME-01",
        helper="_normalize_temporal_shift_width",
        layer=RuleLayer.SEMANTIC,
        kind=PremiseKind.ABSTRACT_BOUND,
        status=PremiseStatus.PROVED_LOCAL,
        obligation=(
            "abstract transfer and join conservatively contain all "
            "defined concrete reachable states; upper<=1 therefore "
            "soundly implies concrete raw in {0,1}"
        ),
    ),
)


def main() -> None:
    domain_specs = tuple(
        spec
        for spec in RULE_SPECS
        if spec.validity is RuleValidity.DOMAIN
    )

    registry_by_helper = {
        spec.helper: spec
        for spec in domain_specs
    }

    premise_by_helper = {
        premise.helper: premise
        for premise in PREMISES
    }

    if len(premise_by_helper) != len(PREMISES):
        raise AssertionError(
            "duplicate helper in DOMAIN premise ledger"
        )

    registry_helpers = set(
        registry_by_helper
    )
    premise_helpers = set(
        premise_by_helper
    )

    missing = (
        registry_helpers
        - premise_helpers
    )

    stale = (
        premise_helpers
        - registry_helpers
    )

    if missing:
        raise AssertionError(
            "DOMAIN helpers missing premise classification: "
            + ", ".join(
                sorted(missing)
            )
        )

    if stale:
        raise AssertionError(
            "premise ledger contains non-DOMAIN helpers: "
            + ", ".join(
                sorted(stale)
            )
        )

    for helper, premise in premise_by_helper.items():
        spec = registry_by_helper[
            helper
        ]

        if spec.rule_ids != (
            premise.rule_id,
        ):
            raise AssertionError(
                f"{helper}: Rule ID mismatch: "
                f"registry={spec.rule_ids} "
                f"premise={premise.rule_id}"
            )

        if spec.layer is not premise.layer:
            raise AssertionError(
                f"{helper}: layer mismatch: "
                f"registry={spec.layer} "
                f"premise={premise.layer}"
            )

    print(
        "SPK CORE DOMAIN PREMISE LEDGER v0"
    )
    print()

    print(
        f"DOMAIN rules: {len(domain_specs)}"
    )

    print()

    for premise in PREMISES:
        print(
            f"{premise.rule_id:<11} "
            f"{premise.layer.value:<8} "
            f"{premise.kind.value:<27} "
            f"{premise.status.value:<20} "
            f"{premise.helper}"
        )

        print(
            " " * 13
            + premise.obligation
        )

    counts = {
        kind: sum(
            premise.kind is kind
            for premise in PREMISES
        )
        for kind in PremiseKind
    }

    print()
    print(
        "premise classes:"
    )

    for kind, count in counts.items():
        print(
            f"  {kind.value}: {count}"
        )

    if sum(
        counts.values()
    ) != len(domain_specs):
        raise AssertionError(
            "DOMAIN premise partition failure"
        )

    print()
    print(
        "DOMAIN PREMISE LEDGER CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
