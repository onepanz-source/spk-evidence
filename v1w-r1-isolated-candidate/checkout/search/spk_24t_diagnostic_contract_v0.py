"""SPK 24t: pure, bounded diagnostic equivalence contract.

Separate *eligible violations* from an implementation's selected diagnostic.
No import of frozen Core, Compiler, Network or application-host modules.
"""
from __future__ import annotations

from dataclasses import dataclass

from search.spk_24n_independent_oracle_v0 import execute_v0, OracleLimitV0

REASONS = ('max_batches', 'max_events')
BASELINE_BATCHES = 128
BASELINE_EVENTS = 4096


@dataclass(frozen=True)
class DiagnosticProofV0:
    status: str
    eligible: tuple[str, ...]
    independent_choice: str | None
    prior_batches: int
    prior_events: int
    pending_events: int


def classify_v0(case, *, max_batches, max_events):
    """Find first failing logical batch via a complete independent trace.

    Bounded admission requires independent completion with fixed upper limits.
    This is a reference-only, finite semantic domain, not a general runtime
    deadlock or termination oracle. The first failing batch is independently
    derived and must match the 24n failure/success status under caller limits.
    """
    if (type(max_batches) is not int or max_batches < 1 or
            type(max_events) is not int or max_events < 1):
        raise ValueError('budgets must be positive integers')
    # Reject nonterminating/unbounded or out-of-domain source programs. Never
    # reinterpret an oracle overflow, recursion limit or other error as CLOSED.
    full = execute_v0(case, max_batches=BASELINE_BATCHES,
                      max_events=BASELINE_EVENTS)
    prior_events = 0
    for b, batch in enumerate(full['observations']['batches']):
        n = len(batch['channels'])
        if n < 1:
            raise AssertionError('invalid empty logical batch')
        eligible = tuple(name for name, bad in (
            ('max_batches', b >= max_batches),
            ('max_events', prior_events + n > max_events),
        ) if bad)
        if eligible:
            try:
                execute_v0(case, max_batches=max_batches,
                           max_events=max_events)
            except OracleLimitV0 as exc:
                choice = str(exc)
            else:
                raise AssertionError('independent bounded classification inconsistent')
            if choice not in eligible:
                raise AssertionError('independent reason outside eligible set')
            return DiagnosticProofV0('LIMIT_REACHED', eligible, choice,
                                     b, prior_events, n)
        prior_events += n
    try:
        actual = execute_v0(case, max_batches=max_batches, max_events=max_events)
    except OracleLimitV0 as exc:
        raise AssertionError('independent full/single-budget inconsistency') from exc
    if (actual['processed_events'] != prior_events or
            actual['processed_batches'] != len(full['observations']['batches'])):
        raise AssertionError('independent full projection inconsistency')
    return DiagnosticProofV0('CLOSED', (), None, len(full['observations']['batches']),
                             prior_events, 0)


def adjudicate_v0(proof, *, observed_status, observed_reason):
    """Enforce only the first-failing-batch eligible-condition set.

    Singleton failures require exact cause; ties permit either actual cause.
    An observer is checked separately against the unobserved frozen execution.
    """
    if type(proof) is not DiagnosticProofV0:
        raise TypeError('DiagnosticProofV0 required')
    if observed_status != proof.status:
        raise AssertionError('frozen and independent execution status mismatch')
    if proof.status == 'CLOSED':
        if observed_reason is not None:
            raise AssertionError('successful execution supplied a failure reason')
        return 'EXACT_PASS'
    if proof.status != 'LIMIT_REACHED' or observed_reason not in REASONS:
        raise AssertionError('unsupported status or failure reason')
    if observed_reason not in proof.eligible:
        raise AssertionError('reason not eligible at independently proven boundary')
    if len(proof.eligible) == 1 and observed_reason != proof.independent_choice:
        raise AssertionError('unambiguous independent reason mismatch')
    return 'AMBIGUOUS_TIE_PASS' if len(proof.eligible) == 2 else 'EXACT_PASS'
