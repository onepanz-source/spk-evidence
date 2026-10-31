# SPK S3.7d/3b2b2k/14 · Owned External Ingress Prefix v0

**Status:** candidate. Requires full fwork regression. No changes to frozen Core v0, Network v0 or Compiler v0.

## Purpose

Prior `Dynamic Batch Closure Obligations v0` accepts `EXTERNAL_INGRESS` event-time frontiers as *claims*, not as evidence. A bounded, finite simulation can establish a narrower fact from the immutable initial input schedule and the actual backpressure boundary ledger: **for a target and logical horizon `t`, every declared external occurrence with `EVENT_TIME <= t` has arrived in EVENT or has been consumed.** This does not require these events to have been consumed, only accounted for. Nor does it establish closure of any *neuronal* emission stream.

An initial `ExternalIngressBindingV0` is a finite, sealed input *contract*. It must be installed at epoch initialization and remain unchanged in the single-owner scheduler; this component does not independently prove the outside world will never supply more inputs. The component cannot be used to close a live, open-ended ingress stream.

## Interface

`seal_finite_external_ingress_v0(architecture, network, binding, *, epoch_id='E0') -> SealedExternalIngressEpochV0` validates the contract: contiguous occurrence indices (including repeated timestamp/channel payloads as distinct indices), all destinations within the frozen network, known PEs, nonnegative event/service times, a complete mapping from each input index to one consume batch release, and release-boundary compatibility. It produces an immutable epoch-scoped seal.

`analyze_owned_external_prefix_v0(architecture, seal, manifest, boundary, *, queries: tuple[ExternalPrefixQueryV0,...]) -> ExternalPrefixAnalysisV0` compares that seal with the current `BackpressureBoundaryStateV0`.

- Revalidates the reservation/storage ledger via `event_reservation_usage_v0`, including finite `EVENT` capacity and routed provenance.
- Rejects any change to the bound input schedule, epoch or profile.
- Rejects an input recorded in EVENT or consumed before its announced `SERVICE_TIME` arrival boundary.
- Rejects any input past due at the observed boundary that was neither admitted nor consumed. The existing Boundary Controller enforces this during actual transitions; this is an independent fail-closed snapshot check.
- For a query `(node, t)`, includes *every* sealed occurrence addressed to `node` with `EVENT_TIME <= t`. A positive `sealed_prefix_accounted` means none of these is missing from `external_resident` or `external_consumed`.
- Uses distinct input indices to preserve multiplicity, even for equal node/time/channel.
- Sorts queries canonically and returns an immutable result.

A later input in logical time does not block an earlier prefix; an unarrived input with earlier logical time blocks regardless of how many service cycles have passed. `EVENT_TIME` and `SERVICE_TIME` never substitute for one another.

## Trust boundary and excluded conclusions

The result is **conditional on the finite sealed input contract and on the authenticity of the controller-owned boundary snapshot**. Dataclasses by themselves do not authenticate an arbitrary caller-supplied snapshot. It provides *external-prefix accounting evidence*, not a general time watermark automatically valid for unknown future inputs. Its sole positive status is `ACCOUNTED_SEALED_PREFIX`.

Even with `sealed_prefix_accounted=True`, both `ExternalPrefixEvidenceV0.supports_consume_admission` and `ExternalPrefixAnalysisV0.supports_consume_admission` remain `False`. This module does not generate `EventTimeClaimV0` as an authoritative certificate, modify buffers, create a `BATCH_CONSUME`, attest Core computation, or certify that neuronal sources have settled their emission histories. An already-arrived external event must still be paired with the actual eventual consuming batch.

The existing `ExternalIngressBindingV0` in replay-derived paths may refer to precomputed `BATCH_CONSUME` identifiers. This module **does not** remove that dependency; replacing it with dynamically owned consuming requests is a separate necessary step.

## Validation and next gate

The new tests cover physical boundary arrivals and consumption, late service availability, two initial occurrences with identical logical time, independent target streams, finite-plan integrity, release-map coverage, due-index omissions, snapshot forgery detection where feasible, determinism and immutability. Local integration: 44 dedicated tests and 821 total tests in the reconstructed bench; this is not the full fwork suite.

**Next:** derive authoritative *source-emission* lower/settled frontiers from committed Core batches, all pending earlier-time inputs and the positive-delay network topology. These must not be accepted merely because no spike is presently visible. Only after both ingress and source evidence are linked by a single owner can batch closure be considered; external-prefix evidence alone cannot authorize consumption.
