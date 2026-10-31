"""Deterministic synthetic BV v0i stress witness; not a BV v0h trace."""

from .evidence_cost_v0i import Reception

def fixture():
    for i in range(33):
        for path in range(16):
            yield Reception(
                transmission_id=f"tx-{i:03d}-{path:03d}", epoch=1,
                observed_tick=10 + (path % 2), batch_tick=10,
                origin=f"n{33 + (i % 31):02d}", batch_id=f"batch-{i // 3}",
                receiver=f"n{i:02d}", context_id=f"ctx-{i % 3}",
                evidence_code="symbolic-observation",
                link_id=f"link-{path % 4}", path_id=f"path-{path}",
                transport_units=1,
            )

