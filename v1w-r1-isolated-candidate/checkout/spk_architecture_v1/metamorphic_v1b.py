"""A5b: deterministic architecture-preserving transformations.

Physical PE names are opaque labels. A simultaneous, order-preserving
alpha-renaming of PE identities must not change causal computation or ledger
contents modulo those identities. Admission and ownership are still checked
by A1b at execution. This module performs no neuron execution itself.
"""
from __future__ import annotations
from dataclasses import replace
from spk_architecture_v1.pe_fabric_v1a import FabricV1a
from spk_architecture_v1.temporal_service_v1b import CausalServicePlanV1b
from spk_architecture_v1.causal_memory_v1c import CausalMemoryPlanV1c


class MetamorphicDeniedV1b(ValueError):
    pass


def alpha_rename_v1b(args):
    """Change every owned PE ID and per-PE quota consistently, preserving order."""
    if not isinstance(args, tuple) or len(args) != 6:
        raise MetamorphicDeniedV1b('expected six execution arguments')
    case, fabric, transport, pe, memory, link = args
    if not isinstance(fabric, FabricV1a) or not isinstance(pe, CausalServicePlanV1b) or not isinstance(memory, CausalMemoryPlanV1c):
        raise MetamorphicDeniedV1b('invalid source fabric or capacity plan')
    if len(fabric.pe_ids) != len(set(fabric.pe_ids)) or not fabric.pe_ids:
        raise MetamorphicDeniedV1b('duplicate or empty physical PE IDs')
    names = {pid: f'Q{i}' for i, pid in enumerate(fabric.pe_ids)}
    if set(names) & set(names.values()):
        raise MetamorphicDeniedV1b('renamed and original PE names overlap')
    if set(dict(pe.pe_slots)) != set(names) or set(dict(memory.pe_slots)) != set(names):
        raise MetamorphicDeniedV1b('inconsistent PE quota population')
    renamed = replace(fabric,
        pe_ids=tuple(names[x] for x in fabric.pe_ids),
        placement=tuple(replace(row, pe_id=names[row.pe_id]) for row in fabric.placement),
        static_routes=tuple(replace(row, source_pe=names[row.source_pe],
                                    target_pe=names[row.target_pe]) for row in fabric.static_routes))
    p = replace(pe, pe_slots=tuple((names[x], amount) for x, amount in pe.pe_slots))
    m = replace(memory, pe_slots=tuple((names[x], amount) for x, amount in memory.pe_slots))
    return (case, renamed, transport, p, m, link), names


def normalize_pe_names_v1b(value, old_to_new):
    """Recursively project PE IDs back in a complete output, including map keys."""
    if type(old_to_new) is not dict or len(set(old_to_new.values())) != len(old_to_new):
        raise MetamorphicDeniedV1b('ambiguous reverse mapping')
    reverse = {new: old for old, new in old_to_new.items()}
    def recurse(obj):
        if isinstance(obj, dict):
            return {reverse.get(k, k): recurse(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [recurse(x) for x in obj]
        if isinstance(obj, str):
            return reverse.get(obj, obj)
        return obj
    return recurse(value)
