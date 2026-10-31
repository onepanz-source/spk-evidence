# SPK/* BV v1w: Versioned Additive Observation Seam Feasibility Contract

**Classification:** Research-only, additive, read-only; NOT an installed event callback,
not an independently authenticated absence certificate, and not a native receiver channel.

## Attested starting point

The user's native v1v attestation reports `execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv)`
with neither callback-like formals, generator yield, nor async declaration.
`_compute_local(node,state,timestamp,channels)` and `fixture(program,ticks,**kwargs)`
likewise report no callback formal. The v1v AST source audit and SHA-256 custody
confirm exactly that *surface*, not the nonexistence of any possible integration.
No callback execution, native message to B, or runtime-native coverage was attested.

## Experiment v1w

1. Verify the exact canonical v1v native report, source SHA-256 identities,
   API-signature inventory, eight unmet requirements and all native authority barriers.
2. Audit four pinned frozen files *in place, read only*, and reject symlinks,
   source drift, missing bytes, AST drift and signature drift.
3. Collect **bounded AST call-name candidates** in `execute_live_v0e`, `fixture`,
   and `_compute_local`, grouped as emission, routing, ingress, feedback and batch.
   These lexical candidate sites are **neither proven data-flow paths nor hooks**;
   a zero candidate count also does not prove their absence.
4. Propose `spk-bv-observation-port/v1-proposal` as an explicitly NEW,
   versioned, SOURCE-OWNED interface requiring its own design review and
   conformance gate before it may be adopted. NO original file is modified.
5. Maintain ten **unmet** acceptance obligations: authenticated source identity;
   online happens-before; genuine receiver delivery; producer trust anchor;
   predecision expectation; independent coverage/clock; bounded fault-aware
   backpressure; read-only noninterference with unchanged native forward/BV
   results; local value criterion; actual decision-to-event causal binding.
6. Replay v1v including its inherited native chain, require the generated
   v1v JSON to equal the uploaded bytes *exactly*, then reread native sources
   and predecessors before writing the result with `open('xb')`.

### Evidence hierarchy

- **Native**: frozen source identity and syntactic AST candidate sites, if the
  full fwork audit succeeds and the v1v predecessor is reproduced byte-identically.
- **Proposed**: new event API, packet schema, trust/coverage/time semantics.
- **NOT OBSERVED**: in-execution source hooks, delivery to native B, native
  independent coverage, scored receiver judgments, causal credit, operator
  commits and learning. Post-return traces must not be misclassified as online.

The static AST inventory intentionally exposes only categorical counts and a
small bounded list of file/function/line/callee hints, never private stack frames
or simulator side-data to B.

### Installation (incremental only)

```sh
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1w_Additive_Observation_Seam_Feasibility.tar.gz
bash search/spk_bv_v1w_research_gate.sh
```

The full CLI accepts `--v1v <reference>` and all the same predecessor
arguments as v1v (`--v1u ... --v0w`), plus `--out`. Source-bound mode requires
fwork's frozen files. For *design-only*, `--contract-only --v1v ... --out ...`
produces a report with both native source and inherited recomputation flags
**false**, even if the v1v input itself attests earlier native source checks.

### Next scientific step

A future v1x can implement a **new, explicitly versioned research-side event
source**, prove callback invocation and source ownership through an independent
runtime conformance harness, and compare baseline vs observed forward/BV traces
for noninterference. Such tests must keep research events and actual B-receipts
separately auditable. Until then the production scheduler remains frozen and
**no online BV promotion is justified**.
