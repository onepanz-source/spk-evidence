"""Additive PE-scope research emitter, not a cryptographic/native C authority.

This module is invoked synchronously at the PE compute point of a COPIED
scheduler. A Python host can replace it or construct its descriptor at will.
Frozen spk_architecture_v1/pe_execution_v1b.py remains unchanged.
"""
from dataclasses import dataclass
from spk_architecture_v1.pe_execution_v1b import _compute_local


class PEIssuerRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PEEmission:
    C_emission_id: str
    C_source: str
    tick: int
    source_channel: int
    sign: int
    causal_parents: tuple[str, ...]
    compute_batch: int

    def to_packet(self):
        """Serialize same schema as T5ABC; no promotion/attestation field."""
        return {'C_emission_id': self.C_emission_id, 'C_source': self.C_source,
                'tick': self.tick, 'source_channel': self.source_channel,
                'sign': self.sign, 'causal_parents': list(self.causal_parents),
                'compute_batch': self.compute_batch}


def compute_and_issue(node, state, timestamp, channels, parents, compute_batch):
    """Produce PE result and any PE-scope descriptor as one research call.

    No extra compute call, no post-hoc source report, no external sensor truth.
    C=Python research node identity, not trusted silicon or isolated runtime.
    """
    if type(timestamp) is not int or timestamp < 0 or type(compute_batch) is not int or compute_batch < 1:
        raise PEIssuerRejected('invalid PE issuance clock/batch')
    if type(parents) is not tuple or any(type(x) is not str or not x for x in parents) or tuple(sorted(set(parents))) != parents:
        raise PEIssuerRejected('invalid PE causal parents')
    raw, guard, outputs = _compute_local(node, state, timestamp, channels)
    if getattr(node, 'node_id', None) != 'C':
        return raw, guard, outputs, None
    c_channels = [ch for ch in outputs if ch in (11, 12)]
    if len(c_channels) > 1:
        raise PEIssuerRejected('ambiguous PE C sign')
    if not c_channels:
        return raw, guard, outputs, None
    if 30 not in outputs:
        raise PEIssuerRejected('PE C sign without terminal 30')
    channel = c_channels[0]
    return raw, guard, outputs, PEEmission(
        C_emission_id=f'C-batch-{compute_batch}-tick-{timestamp}',
        C_source='C', tick=timestamp, source_channel=channel,
        sign=1 if channel == 11 else -1,
        causal_parents=parents, compute_batch=compute_batch)
