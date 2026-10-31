# SPK V5 · T10JKL/MNO/PQR: bounded reference P-resource admission

**Status:** research-v1; no change to frozen Algebra, Core, Network, PE, Architecture or BV-v0e.

## JKL: typed reference P resource manifest

A single host-owned SQLite `reference_p_resource` contains `owner=C`, `domain=P`, `pe_id=PE-C-RESEARCH`, `mode=execute|verify`, global/per-context grant ceilings, and a revision number. This is a resource *model*, not SPK's original Memory Contract or physical memory accounting. The exact originating provider from T10ABC remains independently enforced, and no native grant is constructed.

## MNO: resource admission at the C semantic receipt tick

An additional `BEFORE UPDATE ON p` trigger examines the actually inserted, consumed `p_grant` **inside the same transaction** as the original P-version CAS. Both global and per-cue ceilings apply. An exhausted quota or `verify` mode causes an SQLite transaction rollback: no partial `p_grant`, policy change, event consumption or ledger entry. The pending semantic receipt remains queued and can be retried after explicit, version-checked reference resource reconfiguration. The existing T10 callback and store guard remain installed; the new class recognizes exactly one additional named trigger.

Profile reconfiguration itself performs an administrative reference-only CAS, rejects stale revisions, refuses to shrink below existing usage, and refuses a downgrade while a tick event is outstanding. A privileged host can still bypass this design by rewriting SQLite or source: no independent authority is claimed.

## PQR: verified boundaries and fail-closed native seam

The real native Memory Contract provider is **not present in this checkout**. `native_authorize` from the prior T9 port still raises `NativeUnavailable`, and this milestone explicitly expects a denial. There are zero SPK native grants, P writes or semantic BV credits. PE `_compute_local` is original; feedback goals and PE programs remain host-authored. No new physical clock or multi-PE occupancy is claimed. This checkpoint does not implement native S/E/O resource accounting; it only exercises a strict C/P reference quota.

The cumulative gate verifies the unchanged original PE/BV hashes, original source pins, all cumulative research manifests, the authentic BV-v0e preflight, all inherited regression suites, two independent byte-identical reports, and zero native promotion. Its final evidence is published only after all checks succeed. A native SPK integration must be developed later against an actual importable, versioned Memory Contract API and native lifecycle, not a guessed interface or shim.
