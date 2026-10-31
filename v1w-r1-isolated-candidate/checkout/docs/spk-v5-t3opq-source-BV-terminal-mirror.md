# SPK V5-T3o/p/q | C-authored terminal mirror / frozen BV-v0e custody

**Research-only; no frozen SPK module is modified.** This milestone packages T3o
(source BV bridge), T3p (fail-closed admission) and T3q (longitudinal adversarial
replay) as ONE installable, verifiable unit.

## Source design

T3h previously routed the C `11` / `12` verdict through B to A via normal
A1b spike edges, but BV-v0e's assessor supports **one terminal channel only**;
routed C emissions are NOT terminal. The previous C closure (`channel 9`, tick
15) was terminal but had no input occurrence ancestry, so no native BV grant.
This limitation was reproduced directly against unmodified BV-v0e.

T3o creates a **separate experiment CaseV0**: C mirrors computed +1/-1 into
unrouted terminal channels 30/31, and emits its closure at tick 14, when
A's decision marker is causally received. C's original routed 11/12 channels
remain. Source-native `execute_live_v0e()` is run twice on the identical
CaseV0, terminal_channel=30 and 31, respectively. One pass discovers the
emitted sign with a source-ancestried C terminal assessment, two charged
feedback grants, and an observed C->B->A lineage. The other pass has no
corresponding terminal and must mint no assessment or grant.

**Crucial boundary:** these two independent runs are an auditor-controlled
multiplex of the original frozen BV source implementation, **NOT** a single
native BV scheduler with dynamic signed semantic credit. There is no
cryptographic authentication of C or its CO2 sensor. Host currently binarizes
CO2; the additional mirror/tick alignment are modifications to a *research
program*, not to frozen A1b/BV source. BV source feedback packets do not
natively carry the task sign. The host separately matches the source-grant
chain to the C/A1b sign. Host inter-episode delay and the source BV tick are
DIFFERENT clocks; no direct equivalence is asserted.

T3p uses the preexisting T3i `OnlinePolicy` without modifying it. A new
`SourceGatedPolicy` only accepts T3i settlements whose original T3h C->A
semantic credit, independently replayed two-pass BV-v0e lineage, source
resource ledger and immutably committed arm/episode agree. Missing C sensor,
missing decision marker, broken material forward signal, missing semantic
return, forged receipts, replay and expired credits do not update the
registry. **Intentional silence is NOT failed forward transport.** If A did
not need to emit a spike, absence of that edge is not a loss.

The Python wrapper is a test harness with public attributes and replayable
SHA chains; it is **not** a privilege boundary against a malicious operator
controlling the Python process. No claim of authentication, native learning,
independent validation or task-goal correctness is permitted. See T3l/m/n for
the already demonstrated non-identifiability of global goals from local C
reward alone.

## Gate / installation

Untar the add-only milestone at the same workspace root as T3l/m/n:

```sh
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T3opq_Milestone_20261021.tar.gz
bash search/spk_v5_t3opq_source_bridge_gate.sh /tmp/spk-v5-t3opq-source-bv-credit.json
```

The gate verifies inherited source SHA pins, local pins, **60 new** tests,
**407 inherited** T3a–T3lmn and frozen A1b/BV tests, then compares a create-only
engineered reference report byte-exact. If the report already exists, choose
another fresh path; the runner deliberately never overwrites results.

## Next native-blocking engineering requirements

1. One BV source scheduler run that can assess **two terminal sign channels**
   without a privileged observer choosing the assessor's channel.
2. Real actor custody binding C source identity and C sensor origin to signed
   trace-derived credit authorization; local SHA pins are insufficient.
3. Actor-mediated program updates that cannot be bypassed by host Python.
4. Independent, prospective goal semantics. The result of T3l/m/n remains a
   live scientific limitation even if transport is eventually authenticated.
