# SPK V5 T4WXY · Experimental C-context execution port

**Research-only, nonfrozen, synthetic reference runtime.** This follows the
successful T4TUV adversarial demonstration that a host can reproduce an
apparently authentic A-ledger without running the frozen BV scheduler.

- **T4W:** Pin T4TUV and prior source identities; create 24 **synthetic input**
  cases selected by historic research-eligible indices. In a new Python
  experimental C *execution context*, compute a sign from input integers and
  create a semantic event within the same `C_compute_and_emit` call.
- **T4X:** Send events through independent Python `C`, `B`, `A` OS processes;
  B preserves bytes, and A owns a ledger. Reject sign/route/parent/challenge
  substitutions, malformed payloads and replay. 24 research admissions.
- **T4Y:** **Demonstrate that the host can still forge** a convincing C packet
  using its enrollment key. This is an intentional negative result. A MAC
  and challenge are *not* proof of the identity of SPK neuron C.

This reference port does **not** invoke original BV-v0e, does not compute using
frozen SPK neuron C, and does not use independent sensor/goal evidence. It
specifies a candidate semantic transaction shape, not a native integration.
The host provisions the symmetric key to both C and A; the host can forge a
valid packet. No promotion to native BV or learning is allowed.

The next genuine integration requires introducing `C_emission_id`,
`semantic_sign`, `causal_parent_id`, `source_identity`, and verifier-controlled
origin into a **nonfrozen experimental execution-owned scheduler fork**, with
A verifying issuer authority **from runtime custody**, not an enrollment key
controlled by the host. This milestone intentionally does not patch the frozen
BV-v0e scheduler or try to fake this missing authority.

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4WXY_C_Context_Reference_Port_Milestone_20261022.tar.gz
bash search/spk_v5_t4wxy_c_context_reference_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t4wxy-c-context-reference.json
```
