# SPK BV v1k | Receiver-local witness authority boundary

**Status:** research-only, no native absence witness, no receiver judgment, no learning.

## Evidence anchor

v1j's native source-bound A→B→C network has two original A→B occurrences,
two original B→C occurrences, and zero variant forward occurrences, native
assessments, or reverse feedback. Its native sender does not expose a locally
accessible receiver witness of **why** the variant stream is silent. The v1k
CLI independently reruns the entire v1j chain before producing the report.

## Protocol design, NOT source attestation

An *independent observation channel* would have to communicate a pre-decision
expectation to B, including a specific event/decision identity, a deadline,
and a receiver acknowledgement. An independent observer must provide a
source-authenticated and *complete* monitor interval including negative
evidence, not merely a post-hoc dictionary or hash of expected data.

The nominal `shadow_protocol` is a logical example with strictly validated
fields: sender A, direct receiver B, channels 7→0, pre-decision commitment and
acknowledgement, future deadline, coverage interval, uniquely declared
expected event identities and corresponding observed event IDs,
monitor identity, and declared criterion ID. It is **never elevated** beyond
`SHADOW_DECLARATION_ONLY`. Even a complete declaration of missingness is
reported as `DECLARED_EXPECTATION_MISSED_NO_NATIVE_CAUSAL_AUTHORITY`.

The obligation is recursive: if A can suppress its spike and also choose not
to publish a commitment, a receiver cannot learn about the missing expectation
from its event-only channel. A future source of commitments must have its own
independently attestable coverage, rather than secretly relying on the same
spike being monitored.

C is A's *causal descendant* but not A's direct recipient. It cannot directly
certify an A→C missing event from a fabricated route. Any C-side judgment
requires its own B→C expectation and a cross-hop causal binding; it must not
be counted as an independent causal vote about A merely because C is another
physical neuron.

## Shadow classifications

- Declared event IDs present: `DECLARED_EVENTS_SEEN_WITHOUT_NATIVE_AUTHORITY`.
- Deadline in future: `DECLARED_EXPECTATION_PENDING`.
- Time coverage not complete: `DECLARED_COVERAGE_GAP`.
- Declared interval complete, expected event not declared seen:
  `DECLARED_EXPECTATION_MISSED_NO_NATIVE_CAUSAL_AUTHORITY`.

All four are *hypothetical* and not projected onto the native v1h variant.
Hash values identify document bytes only. They are not signatures, external
truth, unbiased counterfactuals, or endorsements from the recipient.

## Installation / usage

From fwork's `~/workspace/spk-backvalidation-v0`, extract the v1k package and
run `bash search/spk_bv_v1k_research_gate.sh`. The executable
`python -m search.spk_bv_v1k_witness_authority` takes `--v1j`, `--v1i`,
`--v1h`, `--v1g1`, `--v1f`, `--v1e`, `--v1d`, `--v1c`, `--v1b1`, `--v1a`,
`--v0w`, and a fresh `--out`. Optional `--demo-shadow` produces four
hypothetical scenarios; `--shadow-protocol PATH` evaluates a user-provided
list of explicit declarations without allowing source authority promotion.

Do not modify frozen Architecture v1, Core, Network, Compiler or the v0e native
scheduler. Next: implement a research-only independent monitor of *one hop*
with trusted producer custody and complete-interval attestation, then test
noncircular scheduling and causal association before any scoring or update.
