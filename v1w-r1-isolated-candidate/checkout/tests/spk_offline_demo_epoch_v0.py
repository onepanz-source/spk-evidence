"""LOCAL DEMO ONLY: build a finite SPK sealed epoch from existing test fixtures.

NOT a production provider. Uses test fixture topology and a deliberately quiet
Core C program. The shared epoch starts with NO P/S or BATCH_CONSUME receipts.
No source authentication, global authority or deployment safety is claimed.
"""
from dataclasses import replace
from unittest.mock import patch

from spk_core.isa import CoreCmp, CoreProgram
from tests import test_owned_root_batch_consumption_v0 as root_fixtures


def make_epoch():
    original = root_fixtures.scenario

    def quiet_scenario():
        arch, network, placement, image, prepared, registry = original()
        nodes = tuple(
            replace(node, program=CoreProgram(tuple(
                replace(op, threshold_raw=100) if isinstance(op, CoreCmp) else op
                for op in node.program.instructions
            ))) if node.node_id == 'C' else node
            for node in network.nodes
        )
        network = replace(network, nodes=nodes)
        registry = replace(registry, allocation_ledger=replace(
            registry.allocation_ledger, network=network))
        return arch, network, placement, image, prepared, registry

    with patch.object(root_fixtures, 'scenario', quiet_scenario):
        return root_fixtures.seeded(confirmed=())
