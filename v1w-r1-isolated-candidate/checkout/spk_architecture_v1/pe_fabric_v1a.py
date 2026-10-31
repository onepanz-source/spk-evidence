"""SPK Architecture v1 / A1a: hardware-neutral, static PE ownership projection.

No scheduler, runtime, inter-PE transport, arbitration or latency is implemented.
This module never imports frozen Core, Compiler or Network modules.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter

SCHEMA = 'spk-architecture-pe-placement/v1a'
SCHEMES = ('single', 'split', 'spread')


@dataclass(frozen=True)
class PlacementV1a:
    node_id: str
    pe_id: str


@dataclass(frozen=True)
class StaticRouteV1a:
    source_node: str
    source_channel: int
    target_node: str
    target_channel: int
    delay_ticks: int
    source_pe: str
    target_pe: str

    @property
    def cross_pe(self):
        return self.source_pe != self.target_pe


@dataclass(frozen=True)
class FabricV1a:
    scheme: str
    pe_ids: tuple[str, ...]
    placement: tuple[PlacementV1a, ...]
    static_routes: tuple[StaticRouteV1a, ...]

    def owner(self, node_id: str) -> str:
        for p in self.placement:
            if p.node_id == node_id:
                return p.pe_id
        raise ValueError('unplaced neuron: ' + str(node_id))

    def profile(self) -> dict:
        usage = Counter(p.pe_id for p in self.placement)
        return {'schema': SCHEMA, 'scheme': self.scheme,
                'node_count': len(self.placement), 'pe_count': len(self.pe_ids),
                'nodes_per_pe': {pe: usage[pe] for pe in self.pe_ids},
                'node_owners': [[p.node_id, p.pe_id] for p in self.placement],
                'static_edge_count': len(self.static_routes),
                'cross_pe_edges': sum(route.cross_pe for route in self.static_routes),
                'local_edges': sum(not route.cross_pe for route in self.static_routes)}


def plan_v1a(case, scheme: str) -> FabricV1a:
    """Validate total unique placement and preserve every *edge occurrence*."""
    if scheme not in SCHEMES:
        raise ValueError('unsupported A1 placement scheme')
    nodes = tuple(n.node_id for n in case.nodes)
    if len(nodes) != 3 or set(nodes) != {'A', 'B', 'C'}:
        raise ValueError('A1a corpus scope: exactly A, B, C')
    count = {'single': 1, 'split': 2, 'spread': 3}[scheme]
    pes = tuple(f'PE{i}' for i in range(count))
    target = {'single': (0, 0, 0), 'split': (0, 1, 1),
              'spread': (0, 1, 2)}[scheme]
    mapping = dict(zip(('A', 'B', 'C'), (pes[i] for i in target)))
    owners = tuple(PlacementV1a(nid, mapping[nid]) for nid in sorted(nodes))
    routes = []
    for edge in case.edges:
        if edge.source_node not in mapping or edge.target_node not in mapping:
            raise ValueError('dangling edge')
        if type(edge.delay_ticks) is not int or edge.delay_ticks <= 0:
            raise ValueError('nonpositive edge delay')
        routes.append(StaticRouteV1a(
            edge.source_node, edge.source_channel, edge.target_node,
            edge.target_channel, edge.delay_ticks,
            mapping[edge.source_node], mapping[edge.target_node]))
    return FabricV1a(scheme, pes, owners, tuple(routes))


def classify_routes_v1a(fabric: FabricV1a, observed_routes) -> dict:
    """Add PE locality to event occurrences without changing their semantics.

    The observer supplies logical route occurrences; this function is a pure
    classification, NOT the inter-PE transport implementation. Parallel routes
    remain separate occurrences even when they have identical descriptors.
    """
    known = {(r.source_node, r.source_channel, r.target_node,
              r.target_channel, r.delay_ticks) for r in fabric.static_routes}
    local = remote = 0
    routed = []
    required = {'emission_timestamp', 'source_node', 'source_channel',
                'delivery_timestamp', 'target_node', 'target_channel', 'delay_ticks'}
    for route in observed_routes:
        if type(route) is not dict or set(route) != required:
            raise ValueError('invalid logical route occurrence')
        k = (route['source_node'], route['source_channel'],
             route['target_node'], route['target_channel'], route['delay_ticks'])
        if k not in known:
            raise ValueError('route has no admitted static edge')
        if (type(route['emission_timestamp']) is not int or
                type(route['delivery_timestamp']) is not int or
                route['delivery_timestamp'] != (route['emission_timestamp'] +
                                                route['delay_ticks'])):
            raise ValueError('route changed logical event timing')
        src = fabric.owner(route['source_node'])
        dest = fabric.owner(route['target_node'])
        if src == dest:
            local += 1
        else:
            remote += 1
        routed.append({'logical': dict(route), 'source_pe': src,
                       'target_pe': dest, 'cross_pe': src != dest})
    return {'routes': routed, 'occurrences': len(routed),
            'local_occurrences': local, 'cross_pe_occurrences': remote}
