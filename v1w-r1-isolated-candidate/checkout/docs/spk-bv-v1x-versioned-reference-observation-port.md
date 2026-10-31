# SPK/* Back Validation v1x: Versioned reference observation port and frozen baseline

Research-only additive increment. **No changes to** Core v0, Network v0,
Compiler v0, Architecture v1, the frozen live scheduler v0e, or its event
semantics. This is not a release or architecture promotion.

## Why

The source-pinned v1w native audit shows `execute_live_v0e(case, fabric, tplan,
pplan, mplan, lplan, bv)` with no exposed callback parameters. Its call-name
candidates are neither demonstrated hooks nor proof that other hooks cannot
exist. v1x must not pass a callback through this frozen signature, replace the
runtime dynamically, or assert streaming based on post-return traces.

## The two deliberately separated experiments

### 1. Research-owned reference execution

`spk-bv-observation-port/reference-v1x` is installed **only** on an isolated
reference executor implemented by this increment. The executor issues
`expectation`, `decision`, individual `sender_emission` events, a final
`sender_count`, and reference `sender_coverage` / `receiver_coverage` records.
The synchronous listener is called *before the research reference function
returns*. Its own logical ticks are not SPK scheduler timestamps; expectation
and coverage are controlled laboratory assumptions, not authenticated native
claims.

A separate bounded reference mailbox for a simulated B sees only specifically
*delivered* records, not the experimenter's source counts. Python object
identity is used only as a local **laboratory** capability; it provides
neither cryptographic identity nor an independently trusted source. Invalid
packets, replay, wrong episode, wrong receiver, old/order-invalid tickets,
loss, overflow, and observer exceptions cannot alter the **byte-identical
reference forward result**. Overflow and losses fail closed: no lack of
control traffic becomes a verdict on A's silence.

Input counts for the laboratory are **seeded only after a native scheduler
call returns**, or in an offline audit from established bounded historical
counts. The simulated events are therefore NOT original online native events.
Every report distinguishes `reference_port_executed_during_reference_runtime`
from `reference_port_is_native_scheduled_event_tap` (always `false`).

### 2. Source-pinned frozen native no-observer repeatability

On fwork only, and **after** v1w is reconstructed byte-identically, the CLI:

1. Verifies pinned native source files and runs the inherited replay chain.
2. Recreates the original A→B→C fixture and the existing pre-episode A
   `CMP(1)→CMP(2)` intervention via the research fixture-copy utility.
3. Executes original/variant × BV OFF/ON, each **twice**, with the unmodified
   native `execute_live_v0e`, and **without any observer**.
4. Verifies full native result byte-repeatability, fixture invariance, exact
   source SHA and exact equality of each native audit summary to v1p.
5. Seeds the *separate* research reference executor from those post-return
   native source/ingress counts; emits the v1x report only if all checks pass.

Thus the native run count in v1x is eight, but **all eight are no-observer
runs**. This measures ordinary deterministic reproducibility and custody,
NOT the mandatory native observer-enabled versus observer-disabled
noninterference property. That requirement remains **unmet**.

## Strictly excluded scientific claims

- No native source-event callback, streaming feed, native receiver B mailbox,
  or authenticated source data.
- No native independent absence/clock/coverage certificate or causal
  attribution of a sender decision.
- No native value criterion, endogenous scored judgment, operator commit,
  rollback, backpropagation of newly scored credit, or learning.
- No cross-world event ID pairing, frozen runtime mutation, or new
  algebraic rewrite certification.

The 10 native acceptance obligations inherited from v1w remain explicitly
`verified: false`. Demonstrating reference-level noninterference does not
promote the corresponding native obligation.

## Usage

```sh
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1x_Versioned_Reference_Observer_Port.tar.gz
bash search/spk_bv_v1x_research_gate.sh
```

Native source-bound mode: `python -m search.spk_bv_v1x_reference_observation_port`
with `--v1w /tmp/spk-bv-v1w-observation-seam.json`, all inherited
`--v1v ... --v0w` report flags, and an unused `--out` file path outside the
checkout. Missing ancestors, symlinks, report aliases, existing output files,
noncanonical v1w, source drift or byte-mismatched v1w replay reject without
writing an attested report.

Design-only mode (portable, **no native recomputation**):

```sh
python -m search.spk_bv_v1x_reference_observation_port \
  --v1w /tmp/spk-bv-v1w-observation-seam.json \
  --reference-only \
  --out /tmp/spk-bv-v1x-reference-only.json
```

The design-only JSON can illustrate all 64 laboratory scenarios, but keeps
native execution count and all native proof flags at zero/false. The native
command requires the frozen fwork checkout and cannot be attested in the
standalone research bundle.

## Next gate

To close native read-only noninterference, a **new, explicitly versioned**
source-owned native observer interface must be implemented in a separately
versioned experimental runtime, followed by original-vs-observed comparison
with authoritative native source emission before return, actual control
receipts and fault-aware interval coverage. This must NOT be grafted onto the
frozen v0e scheduler without a new freeze/release gate. Only then can the
remaining BV receiver authority, local criterion, causal binding and eventual
learning be investigated.
