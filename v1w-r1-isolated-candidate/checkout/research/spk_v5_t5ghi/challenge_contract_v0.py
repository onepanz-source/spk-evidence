"""Pure SPK T5GHI research challenge digest shared by C-side and A-side.

A shared Python hash is NOT a trust anchor or an unforgeable signature.
"""
from hashlib import sha256
import json

class PEIssuerRejected(ValueError):pass

def challenge_digest(challenge, packet):
    """Research freshness binding, NOT an unforgeable C signature.

    The challenge is disclosed to the host to drive PE computation. A host
    can calculate the exact digest without executing the neuron.
    """
    if type(challenge) is not dict or set(challenge)!={'case_index','nonce'}:
        raise PEIssuerRejected('receiver challenge invalid shape')
    index=challenge['case_index'];nonce=challenge['nonce']
    if type(index) is not int or index<0 or type(nonce) is not str or len(nonce)!=64 or any(c not in '0123456789abcdef' for c in nonce):
        raise PEIssuerRejected('receiver challenge invalid value')
    required=('C_emission_id','C_source','tick','source_channel','sign','causal_parents','compute_batch')
    if type(packet) is not dict or not all(x in packet for x in required):
        raise PEIssuerRejected('receiver challenge missing issuer fields')
    payload={k:packet[k] for k in required}
    payload.update({'domain':'spk-t5ghi-receiver-challenge/research-v0', 'case_index':index, 'nonce':nonce})
    return sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


