# SPK Back Validation v1s: isolated receiver-visible separate channel

## Scope

Only research files are added. This is an isolated, finite, in-process **toy transport** of information from distinct logical actors to the local receiver B, anchored to the native **source-bound** v1r report. It does not edit frozen Core v0, Network v0, Architecture v1, Compiler v0, or live scheduler v0e.

This is a constructive counterexample to any inference from a missing ingress event alone. It is *not* a native receiver-attested event, cryptographic authentication, independent timing certificate, meaningful utility judgment, causal attribution, adaptation, or learning.

## Explicit actors and boundaries

1. B owns only its own `ingress` count and a local mailbox. It cannot read the v1q/v1r factorial matrix.
2. A dedicated **logical** channel issues immutable packets for expectation, sender port, sender coverage, receiver coverage, and decision disclosure. Roles `planner`, `sender_tap`, `receiver_tap`, and `sender_decision` have distinct process-local identity seals.
3. Each packet carries receiver B, source A, the physical direct edge `A:7 → B:0`, an episode, a single expected-event identifier, creation time, delivery time, kind and typed data.
4. B verifies scope, local per-kind replay prevention, arrival before its verdict, expected content and role seal. A Python object-identity seal is **not** authentication outside this process. It is a laboratory assumption that MUST NOT be serialized as a trusted native message.
5. Expected-event receipt must precede decision; sender/receiver tap and interval-coverage information are accepted only after the episode. A source-independent interval certificate would require actual native implementations not provided here.
6. **Decision visibility does not prove causal responsibility**, and there is no value criterion or scored judgment in this module.

## Closed-world outcomes

- Receiver-local positive ingress: observation without external causal authentication; if it contradicts a received sender-port count, fail closed as inconsistent.
- No received predecision expectation: cannot judge missing event.
- Missing sender-port disclosure: unknown, never silence.
- Missing one coverage witness: unknown, never silence.
- Both logical coverage messages, sender-port zero: lab sender-port silence.
- Both logical coverage messages, sender-port positive, B ingress zero: lab possible transport gap.
- A received decision record: declared action visibility only, not effect, value, or utility.

Adversarial tests require fail-closed rejection for duplicates, forged seal, wrong receiver C, mismatched episode/event/port, wrong issuer, late/stale receipt, malformed content, and untrusted JSON. Empty channel outputs for two different possible worlds are observationally indistinguishable to B.

## Native provenance and execution

The pure analyzer validates the supplied canonical v1r document but never sets native replay success. Only `search.spk_bv_v1s_receiver_disclosure_channel` recursively invokes the full v1r CLI, requires a **byte-identical** regenerated v1r report, checks inputs unchanged, and then sets `inherited_native_v1r_recomputation_verified_in_this_run=true`. This certifies the inherited v1q/v1r source chain, **not** the shadow channel.

Required inputs: `--v1r`, `--v1q`, `--v1p`, `--v1o`, `--v1n`, `--v1m`, `--v1l`, `--v1k`, `--v1j`, `--v1i`, `--v1h`, `--v1g1`, `--v1f`, `--v1e`, `--v1d`, `--v1c`, `--v1b1`, `--v1a`, `--v0w`, `--out`. Run `bash search/spk_bv_v1s_research_gate.sh` before invoking the CLI on fwork.

**Frozen release promotion and native channel integration are expressly prohibited by this increment.** A genuine future contract must replace the laboratory seals with provenance-bearing native producer receipts, independent observation/coverage certificates and receiver-visible delivery acknowledgements, without giving B privileged simulator logs. Only then might a receiver-native declared objective and causally-bound evaluation be introduced.
