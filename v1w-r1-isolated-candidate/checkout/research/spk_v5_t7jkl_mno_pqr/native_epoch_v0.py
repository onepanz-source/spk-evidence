"""Execute genuinely frozen BV-v0e, returning raw source for shadow binding.

All case construction and resource admission follows T7. The source is
host-readable and host-forgeable. This adapter is not a native learning hook.
"""
from __future__ import annotations
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import case_for,verify_source

def execute_raw(choice,goal,*,drop_forward=False):
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    case=case_for(choice,goal,drop_forward=drop_forward)
    fabric=plan_v1a(case,'spread')
    source=execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,
                           max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='A',terminal_channel=7,max_ticks=256))
    verified=verify_source(source,choice,goal,drop_forward=drop_forward)
    return source,verified
