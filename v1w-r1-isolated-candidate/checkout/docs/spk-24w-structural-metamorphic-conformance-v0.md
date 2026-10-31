# SPK 24w: Cross-Layer Structural Metamorphic Conformance v0

**Status: INTEGRATION PASS (2026-10-16, bounded isomorphism domain).**

Baseline: accepted checkpoint `4e6d5f8` (24u) and its accepted descendants
24v. Installation expects an accepted 24v commit. All frozen modules
(`spk_core`, `spk_network`, `spk_compiler`, `spk_architecture`, `spk_simulator`)
and all prior 24m–24v adapters are unchanged.

## 1. What is being tested

Earlier end-to-end gates use a fixed three-node corpus and prove exact results.
They do not prove that changing semantically irrelevant *representations*
leaves the result unchanged throughout the compiled pipeline. A hidden reliance
on literal neuron identifiers, source tuple ordering, or graph wire ordering
could survive an otherwise green fixed-corpus gate.

24w uses the original 216-case 24o corpus, pinned by SHA-256
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.
For every case, three independent **invertible** transformations are defined:

| Variant | Structural transformation |
| --- | --- |
| `cycle_and_reverse` | A→B→C→A and reverse node, edge and ingress order |
| `swap_ac` | Exchange A/C identifiers, preserve ordering |
| `reverse_order` | Keep identifiers, reverse node, edge and ingress order |

All edge delays, channel identifiers, instruction sequences, initial states,
state widths, parallel wire multiplicity and ingress event multiplicity remain
unchanged. The variants deliberately contain no node deletion or edge rewrite.
The primitive transformations import NO frozen SPK runtime modules.

## 2. Independent oracle obligation

For each of the **648 transformed programs**, execute the 24n independent
interpreter and normalize the resulting emission, terminal, state, batch and
route projections back to the original neuron identifiers. Require **full
projection equality** with the original untransformed source. Identical
counts alone are insufficient.

This independent calculation establishes a metamorphic *expectation*. It does
NOT certify the frozen Compiler or Network. Only the authoritative gate does.

## 3. Compiled integrated obligation

For each transformed source, require all of the following:

1. Frozen Network IR admission and round-trip;
2. Frozen Compiler admission using 24u's explicit three-PE resource profile;
3. Versioned compilation manifest round-trip and pinned SHA-256;
4. Actual execution through the existing 24t diagnostic reference host,
   including passive observer ON/OFF and independent-result checks;
5. `CLOSED`, `EXACT_PASS`, no selected/eligible failure reason;
6. Inverse-rename the **actual host receipt's complete result** and compare it
   with the **original** primitive source interpretation.

All 216 source cases and all three variants are mandatory. A compile rejection,
Network schema rejection, observer mismatch, changed state or changed route
multiplicity fails the gate with the relevant case identifier. There is no
silent reduction of the accepted corpus and no bypass of the Compiler.

### Evidence

The report records 648 source/variant rows, all manifest digests and normalized
full-result digests. Canonical strict JSON is re-executed in a separate process;
re-sealing a forged row cannot pass verification. SHA-256 is a consistency
mechanism, NOT cryptographic authentication or a signature.

## 4. Acceptance boundary

The experiment is **bounded to three named neurons, 8-bit Core state,
positive-delay DAGs, the six fixed Core instruction profiles and six ingress
patterns**. It does not establish arbitrary-graph isomorphism (including
cycles), PE remapping invariance under resource contention, distributed
scheduling invariance, observer callback sandboxing, durable execution,
learning, or universal program equivalence.

Renaming the program does not necessarily preserve the literal *serialized
manifest hash*, which is not asserted. It must preserve the computational
projection after reversing the identifier mapping.

## 5. Gate

1. Pure 648-case metamorphic oracle proof and plan identity.
2. Real frozen Compiler→manifest→24t host, all transformed cases.
3. Independent-process canonical evidence and full replay.
4. Existing 24u/24v cross-layer and failure regression.
5. Full repository regression.
6. Frozen module/staging/whitespace protection.

The gate does not create commits or tags. No stage is accepted based on mocked
runtime wiring; real `fwork` frozen modules are authoritative.

## 6. Engineering roadmap before certification

S1=100%, S2=100%, S3=90%, S4=85%, S5=90%; equally weighted total 93%,
following accepted 24v. These are engineering estimates, not proof fractions.
A 24w PASS will justify reassessing S3 and S5, but no promotion is automatic.

## 7. Certified fwork gate - 2026-10-16

Baseline: 67a80e2.

- Independent metamorphic plan tests: 15 PASS.
- Frozen Compiler/host metamorphic tests: 10 PASS.
- Original source programs: 216.
- Compiled structural transformations: 648.
- Prior 24u/24v regression: 37 PASS.
- Full repository regression: 2977 PASS.
- Cross-process evidence replay: PASS.
- Frozen boundary and hygiene: PASS.

Plan SHA256:
91dda6289f29b38a12a7672c36169003c3eddc27ff3d4b8abfd923d9f0565d0f

Evidence SHA256:
1e620306cad44da0f3b1d289a68fab751dc759e1ae243c97ff352354f2ca9e98

Acceptance covers declared finite graph isomorphisms only.
It does not prove cyclic graph equivalence, PE contention
invariance, arbitrary observer isolation or general liveness.

Engineering roadmap:
S1=100%, S2=100%, S3=90%, S4=85%, S5=95%.
Total=94%, equally weighted; previous 93%, delta +1 pp.
