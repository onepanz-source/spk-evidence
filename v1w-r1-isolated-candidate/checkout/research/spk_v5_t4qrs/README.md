# SPK V5 T4QRS | Experimental process-separated receiver port

Research only. Additive files; no changes to frozen Core / Network / Compiler /
Architecture v1, BV-v0e runtime or historical milestones.

## Objective

T4Q: In a distinct Python producer process call the **actual frozen BV-v0e
scheduler once per case**, all 180 original T4NOP cases, compare each source
SHA-256 against the pinned T4NOP report. Extract signed C-channel observations
from *returned producer data*, not from a separate A1b run. Admit only the 24
prior research-guard cases with a coherent positive/negative C→B→A trace.

T4R: The producer creates 24 independent 256-bit random one-time preimages,
SHA-256 commitments binding the full typed packet, and a host-commissioned
commitment list. A distinct Python relay process forwards the opaque packets
without authority to change their committed meaning.

T4S: A distinct Python A-receiver process checks trusted (host-commissioned)
commitments and independently checks source SHA, sign, time order, channels,
route, case eligibility and anti-replay. It writes its own research ledger and
runs 13 adversarial negatives. Two independent end-to-end runs must produce
byte-identical normalized reports while their random commitments differ.

## Critical, non-promotable boundary

The C producer in this milestone is a **Python adapter reading C's events from
the BV scheduler's returned object**, not code executed with native ownership
inside the neuron C. The host commissions the commitment list and can replace
it. SHA-256 precommit detects mutation/replay under the assumed enrollment
boundary; it is *not* a signed native-C certificate or a trusted external sensor.
The separate Python A process is *not* SPK neuronal memory or a native BV credit
transaction. Every report states `C_neuron_origin_authenticated=false`,
`BV_native_receiver_semantic_receipt=false`, `native_learning_proven=false`,
`promotion_allowed=false`.

No external Python dependencies. Relies on Python >=3.10. Enrolled secrets only
exist in temporary files created under restrictive umask and destroyed on exit.
The output report stores hashes and case metadata, no one-time preimages.

## Run from existing repo

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4QRS_Process_Receiver_Port_Milestone_20261022.tar.gz
mkdir -p ~/workspace/spk-evidence
bash search/spk_v5_t4qrs_process_receiver_port_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t4qrs-process-receiver-port.json
```

**Expected:** 180 original BV source invocations in each run; 24 research A
process commits per run; 13 adversarial rejections; two normalized byte-equal
reports; zero native C-authentication, semantic BV receipt or learning.

The pinned report is included in the milestone and SHA-verified to avoid `/tmp`
dependencies. Source pins additionally cover 12 historical research/frozen paths.
