# SPK Back Validation v4ae–v4ag — two-view task adjudication and disagreement escrow

**RESEARCH ONLY. No program adoption, no native learning, no change to frozen
Architecture v1 or the native v0e executor.**

## Research question

When two reviewers of the same candidate disagree, can the system withhold
adoption? Yes, within the bounded simulator experiment. But two reviewers
*agreeing* still do **not** prove that their task labels correspond to reality.

This milestone explicitly separates three phenomena:

1. **Execution facts:** an original SHA-pinned native execution, plus
   counterfactual candidate/previous program probes.
2. **Observed agreement:** endpoint-event and emission-event projections of
   each probe both report the same terminal C/channel-7 behavior.
3. **Semantic judgment:** a *previously declared synthetic task*, not a
   real external truth source, assigns costs to those observations.

The two code paths use different projections (`forward.terminal` versus
`forward.emissions` filtered to C/channel 7). They are **correlated evidence
from the same native run**, not physically, institutionally or epistemically
independent measurements. The two review MACs are distinct public **test-only**
HMAC-SHA256 keys with canonical domain-separated signed payloads. They prove
mechanism behavior, not reviewer identity. Replay history remains transient.

## Indistinguishable observation, opposite task conclusions

For the injected shadow degradation A `CMP=0` and candidate `CMP=1`, the
bounded two-input probe yields the same observed counts to both reviewers:

| Case | Channel 0 | Channel 1 | Task loss under declared labels (0→1, 1→0) | Task loss under opposite labels (0→0, 1→1) |
| --- | ---: | ---: | ---: | ---: |
| Shadow base, `CMP=0` | 1 | 1 | 4 | 4 |
| Candidate, `CMP=1` | 1 | 0 | 0 | 9 |

The **identical native observations** produce a judgment of improvement
under one declared task and regression under its opposite. No amount of
agreement between these two extractors can determine which task was truly
intended. The pinned v4y–v4aa canary only detects deviations from the prior
declaration; it cannot validate that declaration against the world.

## Source-bound test matrix

- 18 exact original SHA-verified native v0e reexecutions (3 schedules × 2 modes
  × 3 fabric capacities).
- 72 further native counterfactual probes (base/candidate × channel 0/1).
- 15 variants for each original source = 270 adjudication cases.
- 18 two-view consistent research-only witnesses; 18 explicit disagreements
  and 18 abstentions quarantined; 18 both-signed poisoned task labels vetoed.
- Additional negative cases: incomplete view, unanimous false judgment,
  shared evidence origin, nonce reuse, wrong lineage/scope, altered review,
  tampered projection, causally premature review, replay and shared test keys.
- Audit regenerates each scenario from signed source and actual native replay,
  and rejects modified report decisions. CLI is create-only, rejects source
  SHA drift, symlinked signed inputs and in-repository outputs.

## Boundaries and next gate

1. No genuinely independent source of task truth, no offline holdout with
   independently verified labels, and no protection against colluding
   reviewers with access to the same synthetic ground-truth declaration.
2. Public embedded HMAC fixture keys are not a secure identity system. Replay
   defense is in-memory only; no restart/crash-safe review record exists.
3. Adjudication is purely a research gate: **even a consistent verdict does
   not authorize adopting or changing a program**. No physical energy model,
   generalized objective, mesh topology or source-dependent weights.

The next substantive step would be an independently provisioned evidence
source, plus durable tamper-evident replay/escrow custody. Until then, the
research evidence supports only *internal consistency and fail-closed
disagreement*, not autonomous learning correctness.
