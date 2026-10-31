"""BV v1v: read-only, source-pinned native observation API surface audit.

Inspection cannot establish absence of a callback in all possible integrations;
more importantly, a callback signature alone proves no authenticated receiver
receipt or independent absence coverage. No production source is modified.
"""
from __future__ import annotations
import ast
from collections import Counter
from hashlib import sha256
from pathlib import Path

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.incremental_shadow_channel_v1u import SCHEMA as U_SCHEMA, STATUS as U_STATUS

SCHEMA='spk-bv-frozen-runtime-observation-surface-audit/v1v'
STATUS='SOURCE_PINNED_READONLY_API_SURFACE_NO_VERIFIED_LIVE_RECEIVER_CHANNEL'
SCHED='spk_backvalidation_v0/live_dual_scheduler_v0e.py'
PRODUCER='search/spk_bv_v0e_live_evidence.py'
TEST='tests/test_spk_bv_live_dual_scheduler_v0e.py'
ARCH='spk_architecture_v1/pe_execution_v1b.py'
PINS=(PRODUCER,SCHED,TEST)
EVENT_HINTS=('callback','on_event','on_emit','on_emission','listener','observer','sink','hook','subscribe','on_batch')
REQUIRED_BOUNDARY=(
 'source-owned-event-observation-during-native-execution',
 'receiver-accessible-independent-control-delivery',
 'predecision-expectation-and-receipt',
 'independent-clock-and-coverage-with-failure-awareness',
 'native-authenticated-source-identity-and-episode',
 'no-interference-with-frozen-forward-and-BV-scheduling',
 'recipient-local-declared-value-criterion',
 'decision-to-event-causal-provenance',
)
CLAIMS_EXCLUDED=(
 'static-AST-signature-audit-does-not-prove-absence-of-all-possible-hooks',
 'potential-callback-name-is-not-an-executed-event-stream',
 'one-shot-scheduler-return-is-not-live-receiver-delivery',
 'producer-source-SHA256-is-integrity-not-messaging-authentication',
 'native-posthoc-traces-are-not-independent-absence-certificates',
 'no-shadow-lab-mailbox-promotion-to-native-B',
 'no-native-scored-judgment-update-credit-or-learning',
 'no-core-network-compiler-architecture-modification',
)


def _hex64(x):
    return type(x) is str and len(x)==64 and all(c in '0123456789abcdef' for c in x)


def validate_predecessor(u:dict, raw:bytes):
    require(type(u) is dict and type(raw) is bytes and canon(u)==raw,
            'v1u predecessor is not canonical')
    required={
      'schema':U_SCHEMA,'status':U_STATUS,
      'source_kind':'ATTESTED_NATIVE_V1T_PLUS_RESEARCH_OWNED_INCREMENTAL_CLOCK',
      'inherited_native_v1t_recomputation_verified_in_this_run':True,
      'new_native_scheduler_runs_in_this_module':0,
      'lab_incremental_session_count':58,
      'native_scheduler_callback_connected':False,
      'native_receiver_received_live_control_packets':0,
      'native_authenticated_source_evidence':0,
      'native_independent_absence_certificates':0,
      'native_scored_receiver_judgments':0,
      'native_operator_updates':0,
      'native_learning_proven':False,
      'lab_tick_is_simulated_not_native':True,
      'lab_ingress_is_simulated_from_posthoc_count':True,
      'lab_control_loss_fails_closed':True,
      'lab_queue_overflow_fails_closed':True,
      'producer_posthoc_counts_withheld_from_receiver':True,
      'no_cross_world_event_pairing':True,
    }
    require(all(type(u.get(k)) is type(v) and u.get(k)==v for k,v in required.items()),
            'native-vs-shadow trust boundary changed')
    frozen=u.get('frozen_native_sources')
    require(type(frozen) is dict and set(frozen)=={
        'frozen_producer_sha256','frozen_a1_compute_source_sha256',
        'compute_function_ast_sha256','compute_function_name',
        'compute_function_positional_args'}, 'frozen inventory missing fields')
    pins=frozen['frozen_producer_sha256']
    require(type(pins) is dict and set(pins)==set(PINS) and
            all(_hex64(h) for h in pins.values()) and
            _hex64(frozen['frozen_a1_compute_source_sha256']) and
            _hex64(frozen['compute_function_ast_sha256']) and
            frozen['compute_function_name']=='_compute_local' and
            frozen['compute_function_positional_args']==['node','state','timestamp','channels'],
            'invalid frozen producer or compute function inventory')
    for k in ('reference_v1t_sha256','reference_v1m_sha256','reference_v1s_sha256',
              'native_fixture_sha256'):
        require(_hex64(u.get(k)),'malformed predecessor digest '+k)
    rows=u.get('lab_incremental_sessions')
    require(type(rows) is list and len(rows)==58,'incomplete native-seeded shadow lab')
    keys=[]
    for row in rows:
        require(type(row) is dict and row.get('arm') in ('original','variant') and
                row.get('mode') in ('on','off') and type(row.get('plan')) is str and
                row.get('lab_tick_not_native',True) is True and
                row.get('lab_clock_not_native') is True and
                row.get('seed_origin')=='POSTHOC_V1T_PRODUCER_COUNTS_ONLY' and
                row.get('native_stream_messages_delivered')==0 and
                type(row.get('receiver_view')) is dict and
                row['receiver_view'].get('native_receiver') is False and
                row['receiver_view'].get('native_authority') is False and
                row['receiver_view'].get('native_absence_certificate') is False and
                row['receiver_view'].get('operator_update_committed') is False and
                row['receiver_view'].get('receiver_scored_judgment') is False and
                row['receiver_view'].get('sender_decision_causal_role_known') is False and
                row['receiver_view'].get('receiver_ingress_count')==(2 if row['arm']=='original' else 0) and
                row.get('experimenter_source_counts_not_in_B_view')=={
                   'sender':2 if row['arm']=='original' else 0,
                   'ingress':2 if row['arm']=='original' else 0},
                'v1u shadow session promoted or mutated')
        keys.append((row['arm'],row['mode'],row['plan']))
    require(len(set(keys))==58 and
            Counter((a,m) for a,m,p in keys)=={('original','off'):15,
                ('original','on'):15,('variant','off'):14,('variant','on'):14},
            'v1u sessions not a complete set')
    return pins,frozen


def _function(tree:ast.Module,name:str):
    found=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==name]
    require(len(found)==1,'missing or duplicate frozen function '+name)
    return found[0]


def _signature(node:ast.FunctionDef|ast.AsyncFunctionDef):
    a=node.args
    positions=[x.arg for x in a.posonlyargs+a.args]
    kw=[x.arg for x in a.kwonlyargs]
    require(len(set(positions+kw))==len(positions+kw),'duplicate function argument')
    return {
      'name':node.name,
      'positional':positions,
      'keyword_only':kw,
      'has_varargs':a.vararg is not None,
      'has_kwargs':a.kwarg is not None,
      'possible_callback_name_hints':[n for n in positions+kw if any(
             n==hint or n.startswith(hint+'_') for hint in EVENT_HINTS)],
      'generator_body_has_yield':any(isinstance(x,(ast.Yield,ast.YieldFrom))
          for x in ast.walk(node) if not isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))),
      'has_return_statement':any(isinstance(x,ast.Return) for x in ast.walk(node)),
      'async_function':isinstance(node,ast.AsyncFunctionDef),
    }


def audit_surface(u:dict, raw:bytes, blobs:dict[str,bytes]|None=None):
    pins,frozen=validate_predecessor(u,raw)
    verified=blobs is not None
    surfaces=None
    if verified:
        require(type(blobs) is dict and set(blobs)==set(PINS)|{ARCH},
                'complete pinned source inventory required')
        trees={}
        for rel,source in blobs.items():
            require(type(source) is bytes and 0<len(source)<=600_000,
                    'missing, oversized or malformed frozen source')
            expected=pins[rel] if rel in pins else frozen['frozen_a1_compute_source_sha256']
            require(sha256(source).hexdigest()==expected,
                    'frozen source sha256 drift: '+rel)
            trees[rel]=ast.parse(source,filename=rel)
        sched_fn=_function(trees[SCHED],'execute_live_v0e')
        fixture_fn=_function(trees[PRODUCER],'fixture')
        compute_fn=_function(trees[ARCH],'_compute_local')
        _function(trees[ARCH],'_admit')
        plan=[x for x in trees[SCHED].body if isinstance(x,ast.ClassDef)
              and x.name=='LiveBVPlanV0e']
        require(len(plan)==1,'native plan type missing or ambiguous')
        digest=sha256(ast.dump(compute_fn,include_attributes=False).encode('utf8')).hexdigest()
        require(digest==frozen['compute_function_ast_sha256'] and
                [x.arg for x in compute_fn.args.args]==frozen['compute_function_positional_args'],
                'frozen compute AST identity mismatch')
        surfaces={
           'scheduler_entrypoint':_signature(sched_fn),
           'fixture_entrypoint':_signature(fixture_fn),
           'neuron_compute_entrypoint':_signature(compute_fn),
           'plan_class_found':True,
           'producer_files_sha256':{rel:sha256(blobs[rel]).hexdigest()
               for rel in sorted(blobs)},
           'observation_class':'SOURCE_SIGNATURE_HINTS_ONLY_NOT_EXECUTION_PROOF',
        }
    return {
      'schema':SCHEMA,'status':STATUS,
      'source_kind':('NATIVE_FROZEN_SOURCE_SHA256_AST_READONLY_AUDIT' if verified
                     else 'PREDECESSOR_BOUND_OFFLINE_CONTRACT_ONLY'),
      'reference_v1u_sha256':sha256(raw).hexdigest(),
      'reference_v1t_sha256':u['reference_v1t_sha256'],
      'frozen_native_sources':frozen,
      'frozen_source_bytes_rechecked_in_this_run':verified,
      'actual_native_API_surface':surfaces,
      'inherited_native_v1u_recomputation_verified_in_this_run':False,
      'public_live_event_hook_semantics_verified':False,
      'native_per_event_callback_invoked':False,
      'native_source_to_B_control_delivery_verified':False,
      'native_independent_absence_certificate_verified':False,
      'native_clock_or_coverage_certified':False,
      'no_new_scheduler_executions_in_v1v':True,
      'native_scored_receiver_judgments':0,
      'native_operator_updates':0,'native_learning_proven':False,
      'integration_requirements_not_yet_satisfied':list(REQUIRED_BOUNDARY),
      'claims_excluded':list(CLAIMS_EXCLUDED),
    }


def read_pinned_sources(root:Path, u:dict):
    """Read at known relative paths; reject symlinks, TOCTOU drift, and drifts."""
    root=root.resolve(strict=True)
    pins,frozen=validate_predecessor(u,canon(u))
    out={}
    for rel in (*PINS,ARCH):
        p=root/rel
        require(not p.is_symlink() and p.is_file() and p.resolve(strict=True)==p and
                p.stat().st_size<=600_000,
                'unsafe or missing frozen source '+rel)
        b=p.read_bytes()
        expected=pins[rel] if rel in pins else frozen['frozen_a1_compute_source_sha256']
        require(sha256(b).hexdigest()==expected,'frozen source SHA256 mismatch '+rel)
        out[rel]=b
    return out
