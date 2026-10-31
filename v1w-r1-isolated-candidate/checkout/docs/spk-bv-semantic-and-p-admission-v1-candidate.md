# SPK BV Semantic Payload and P Admission v1 CANDIDATE

**Research design only, as of T8ABC/DEF/GHI. Not a runtime release, not native SPK learning.**

## Baseline and compatibility

- The frozen `execute_live_v0e` (SHA-256 `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`) transports only **structural** A→B→C BV assessments.
- The original PE (`8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c`) generates semantic channel 21/22 as a **separate A PE emission** in T7 experiments.
- Current T7 host adapter joins that emission with structural ancestry and updates a **host-managed SQLite policy**, not SPK P memory.
- V1 must have a NEW schema/version and new admission code. V0e is immutable; no in-place reinterpretation of V0e packets or new field smuggled into V0e payloads.

## T8ABC proposed v1 semantic BV message

- Include authenticated (in a future implementation) `issuer=A`, `destination=C`, full `A→B→C` custody, `epoch/decision_id`, `context_id`, `policy_version`, chosen C action, positive/negative verdict, raw A emission reference, source trace identifier, and a C-visible, single-use delivery ID.
- The model-only candidate here contains each of these as **host-visible data**. Digests bind internally consistent fields, **not** origin authenticity. Native BV-v0e messages do not carry it.
- Production semantics must specify whether A observes and judges an actual consequence of C or merely a correlative change; absent a causal model, label it observational feedback. No source quality disguised as semantic weight.

## T8DEF proposed P write authorization

- A candidate write must be issued by **C** for P-domain state owned by C in `execute` mode. Bind PE mapping, decision identity, observed outcome, expected policy version, update bounds, and replay protection.
- P mutation requires a distinct Memory Contract authorization and an atomic versioned commit **inside** the native runtime, not just a valid semantic packet.
- This research code always returns `DENIED_NO_NATIVE_MEMORY_CONTRACT_GRANT`. It can independently update the T7 SQLite research policy to exercise the future interface; native writes remain zero.

## T8GHI runtime integration and acceptance roadmap

1. Define new v1 event/feedback schema and compatibility adapter; reject native-v0e packets erroneously claiming v1 semantics.
2. Implement per-PE C authority plus native P admission and atomic commit, with replay/stale checks, without altering historical v0e output.
3. Establish a producer trust model: **host trusted** for simulator-only claims, or attested producer/receiver for adversarial-host claims. Pure-Python checksums are never attestation.
4. Run matched control and adaptive epochs, faults, stale/conflict/recovery, and causal tests with measurements from the simulated network; demonstrate on previously unseen contexts and without host-rewritten outcomes before claiming general learning.
5. Use the native BV semantic verdict itself, not an A-emission sidecar, and show C's subsequent computation reads the **native** P state. Only then consider semantic BV credit and learning promotion.

The included gate is a **compatibility experiment** using real frozen v0e and research-only candidate interfaces. It does *not* implement items 2–5 and must never report native BV learning.
