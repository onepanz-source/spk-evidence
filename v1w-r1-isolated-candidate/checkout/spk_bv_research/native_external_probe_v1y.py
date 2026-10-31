"""BV v1y: bounded, EXTERNAL sys.settrace probe of frozen Python scheduler.

No scheduler modification, interception of Python line/call/return events only.
Observing the scheduler's source location DOES NOT attest a semantic spike event.
Never a sender-owned callback, a separate B channel or an absence certificate.
"""
from __future__ import annotations
import sys
from hashlib import sha256
from pathlib import Path
from spk_bv_research.off_on_v0t import require, snapshot
from spk_bv_research.native_capture_v0k import canonical_fixture, _json_bytes
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.reference_observation_port_v1x import (
    SCHEMA as X_SCHEMA, STATUS as X_STATUS, PORT as X_PORT, CASES as X_CASES,
    NATIVE_LIMITS as X_LIMITS, check_predecessor as check_w,
)
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS

SCHEMA='spk-bv-frozen-native-external-python-trace-parity/v1y'
STATUS='NATIVE_TRACE_SCOPE_PARITY_NO_PRODUCER_OWNED_EVENT_CHANNEL'
LIMIT=16384
EXPECTED={'original':{'off':(2,2),'on':(2,2)},'variant':{'off':(0,0),'on':(0,0)}}
NATIVE_ZERO={
 'native_producer_owned_observer_callback_calls':0,
 'native_receiver_B_control_messages':0,
 'native_authenticated_producer_evidence':0,
 'native_independent_absence_certificates':0,
 'native_scored_receiver_judgments':0,
 'native_operator_updates':0,
 'native_learning_proven':False,
 'native_communication_authentication_verified':False,
 'native_observer_ON_source_owned_mode_executed':False,
 'native_value_criterion_identified':False,
}
EXCLUSIONS=[
 'python-interpreter-trace-events-are-not-semantic-spike-events',
 'external-sys-settrace-is-not-producer-owned-callback-or-independent-witness',
 'external-probe-can-slow-or-perturb-timing-no-general-realtime-noninterference',
 'equal-return-bytes-on-bounded-fixture-not-universal-noninterference-proof',
 'no-native-recipient-control-message-or-independent-absence-certificate',
 'source-lines-matched-by-Python-runtime-are-not-proof-of-delivery',
 'no-operator-commit-rollback-value-criterion-causal-credit-or-learning',
 'no-modification-or-promotion-of-frozen-contracts',
]


def check_x(x, raw):
    require(type(x) is dict and type(raw) is bytes and canon(x)==raw,'noncanonical v1x')
    required={'schema':X_SCHEMA,'status':X_STATUS,
        'source_kind':'FROZEN_NATIVE_REPEATED_BASELINE_PLUS_SEPARATE_REFERENCE_PORT',
        'inherited_native_v1w_recomputation_verified_in_this_run':True,
        'native_results_repeated_without_observer':True,
        'native_baseline_equal_bytes_not_observer_on_off_proof':True,
        'native_scheduler_executions_in_this_module':8,
        'native_source_readonly_bytes_rechecked_in_this_run':True,
        'reference_lab_session_count':4*len(X_CASES),
        'reference_port_version':X_PORT,
        'reference_port_executed_during_reference_runtime':True,
        'reference_port_is_native_scheduled_event_tap':False,
        'source_files_modified':False,
    }
    require(all(type(x.get(k)) is type(v) and x[k]==v for k,v in required.items()),
            'v1x trust status/chain mismatch')
    require(all(type(x.get(k)) is type(v) and x[k]==v for k,v in X_LIMITS.items()),
            'v1x native authority was promoted')
    require(x.get('native_proof_obligations_unmet')==[
        {'id':k,'verified':False} for k,_ in PORT_OBLIGATIONS],
        'v1x proof obligation drift')
    require(type(x.get('reference_v1w_sha256')) is str and len(x['reference_v1w_sha256'])==64,
            'v1w SHA missing')
    matrix=x.get('native_run_reference_matrix')
    require(type(matrix) is dict and set(matrix)==set(EXPECTED),'v1x matrix missing arms')
    for arm in EXPECTED:
        require(type(matrix[arm]) is dict and set(matrix[arm])==set(EXPECTED[arm]),
                'v1x matrix missing modes')
        for mode,(s,i) in EXPECTED[arm].items():
            item=matrix[arm][mode]
            require(type(item) is dict and set(item)=={'sender','ingress','repeatability_identical','result_sha256'} and
                    type(item['sender']) is int and item['sender']==s and
                    type(item['ingress']) is int and item['ingress']==i and
                    item['repeatability_identical'] is True and
                    type(item['result_sha256']) is str and len(item['result_sha256'])==64 and
                    all(c in '0123456789abcdef' for c in item['result_sha256']),
                    'v1x native matrix tampered')
    sessions=x.get('reference_lab_sessions')
    require(type(sessions) is list and len(sessions)==64,'v1x laboratory truncated')
    seen=set()
    for case in sessions:
        require(type(case) is dict and case.get('arm') in EXPECTED and
                case.get('mode') in ('off','on') and case.get('plan') in X_CASES and
                case.get('native_scheduler_callback_calls')==0 and
                case.get('source_owned_during_reference_execution') is True and
                case.get('reference_noninterference_equal_bytes') is True and
                case.get('receiver_view',{}).get('native_authority') is False and
                case.get('receiver_view',{}).get('receiver_scored_judgment') is False and
                case.get('receiver_view',{}).get('native_absence_certificate') is False and
                case.get('receiver_view',{}).get('operator_update_committed') is False,
                'v1x session authority/shape mismatch')
        key=(case['arm'],case['mode'],case['plan'])
        require(key not in seen,'duplicate v1x lab session')
        seen.add(key)
    return True


class ScopedPythonProbe:
    """Trace only one exact function code object; no globals or locals are retained.

    Fails closed if another sys.settrace hook is installed, or if event count
    exceeds the quota. The trace is restored on all exceptional exits.
    """
    def __init__(self, target, line_candidates=(), max_events=LIMIT):
        require(callable(target) and hasattr(target,'__code__'),'invalid probe target')
        require(type(max_events) is int and 1<=max_events<=LIMIT,'invalid bounded trace quota')
        require(type(line_candidates) in (tuple,list) and all(type(v) is int and v>0 for v in line_candidates),
                'invalid candidate source lines')
        self.code=target.__code__
        self.candidates=frozenset(line_candidates)
        self.limit=max_events
        self.events=0
        self.calls=0
        self.returns=0
        self.lines=0
        self.candidate_hits={str(n):0 for n in sorted(self.candidates)}
        self.overflow=False
        self.trace_error=False
        self.restored=False
        self._old=None
    def _local(self, frame,event,arg):
        try:
            if event not in ('line','return','exception'):return self._local
            self.events+=1
            if self.events>self.limit:
                self.overflow=True
                return None
            if event=='line':
                self.lines+=1
                key=str(frame.f_lineno)
                if key in self.candidate_hits:self.candidate_hits[key]+=1
            if event=='return':self.returns+=1
        except Exception:
            self.trace_error=True
        return self._local
    def _global(self, frame,event,arg):
        if event=='call' and frame.f_code is self.code:
            try:
                self.calls+=1
                self.events+=1
                if self.events>self.limit:
                    self.overflow=True
                    return None
            except Exception:self.trace_error=True
            return self._local
        return None
    def __enter__(self):
        require(sys.gettrace() is None,'existing Python trace hook refused')
        self._old=sys.gettrace()
        sys.settrace(self._global)
        return self
    def __exit__(self,*args):
        sys.settrace(self._old)
        self.restored=sys.gettrace() is self._old
        return False
    def summary(self):
        require(self.restored,'trace hook failed to restore')
        return {'python_target_call_events':self.calls,'python_return_events':self.returns,
                'python_line_events':self.lines,'trace_events_seen':self.events,
                'candidate_line_hits':self.candidate_hits,
                'trace_overflow':self.overflow,'trace_error':self.trace_error,
                'trace_restored':self.restored,
                'scope':'PYTHON_INTERPRETER_FUNCTION_CODE_OBJECT_ONLY',
                'semantic_spike_events_attested':0,'native_B_packets_delivered':0}


def observed_pair(native_run, args, target, candidate_lines=(), cap=LIMIT):
    """One no-probe run vs one externally traced run; compare full result bytes."""
    require(callable(native_run) and callable(target),'invalid native executor')
    # The pinned v1p/v1x native SHA is snapshot(result), NOT SHA256 of the
    # pretty-printed v1r research report JSON.  Compare exactly the lossless,
    # type-tagged native snapshot BYTES before and while tracing.
    before=_json_bytes(canonical_fixture(native_run(*args)))
    with ScopedPythonProbe(target,candidate_lines,cap) as p:
        after=_json_bytes(canonical_fixture(native_run(*args)))
    trace=p.summary()
    require(trace['python_target_call_events']==1 and trace['python_return_events']==1 and
            trace['python_line_events']>0 and not trace['trace_overflow'] and
            not trace['trace_error'], 'missing/incomplete Python trace of native function')
    require(before==after,'native result changed with external Python probe')
    return {'no_probe_result_sha256':sha256(before).hexdigest(),
            'probe_result_sha256':sha256(after).hexdigest(),
            'native_return_bytes_equal':True,'trace':trace}


def analyze(x,raw,*,native_pairs=None,source_rechecked=False):
    check_x(x,raw)
    require(type(source_rechecked) is bool,'invalid source pin flag')
    require(native_pairs is None or (type(native_pairs) is dict and set(native_pairs)==set(EXPECTED) and
            all(type(native_pairs[a]) is dict and set(native_pairs[a])==set(EXPECTED[a]) for a in EXPECTED)),
            'incomplete observed-native pairs')
    if native_pairs is not None:
        require(source_rechecked,'native pairs without source custody')
        for arm in EXPECTED:
            for mode in EXPECTED[arm]:
                r=native_pairs[arm][mode]
                require(type(r) is dict and set(r)=={'no_probe_result_sha256','probe_result_sha256','native_return_bytes_equal','trace'} and
                        r['native_return_bytes_equal'] is True and
                        r['no_probe_result_sha256']==r['probe_result_sha256']==x['native_run_reference_matrix'][arm][mode]['result_sha256'] and
                        type(r['trace']) is dict and r['trace'].get('python_target_call_events')==1 and
                        r['trace'].get('python_return_events')==1 and
                        type(r['trace'].get('python_line_events')) is int and r['trace']['python_line_events']>0 and
                        r['trace'].get('trace_overflow') is False and
                        r['trace'].get('trace_error') is False and
                        r['trace'].get('trace_restored') is True and
                        r['trace'].get('semantic_spike_events_attested')==0 and
                        r['trace'].get('native_B_packets_delivered')==0,
                        'invalid native OFF/ON trace equality')
    return {
        'schema':SCHEMA,'status':STATUS,'source_kind':'FROZEN_NATIVE_EXECUTION_EXTERNAL_PYTHON_PROBE' if native_pairs is not None else 'V1X_BOUND_TRACE_PROBE_CONTRACT_ONLY',
        'reference_v1x_sha256':sha256(raw).hexdigest(),'reference_v1w_sha256':x['reference_v1w_sha256'],
        'inherited_native_v1x_recomputation_verified_in_this_run':False,
        'source_pins_rechecked_in_this_run':source_rechecked,
        'native_probe_parity_matrix':native_pairs,
        'native_scheduler_executions_without_trace_in_this_module':4 if native_pairs is not None else 0,
        'native_scheduler_executions_with_trace_in_this_module':4 if native_pairs is not None else 0,
        'interpreter_tracing_observed_scheduler_during_native_execution':native_pairs is not None,
        'source_owned_native_semantic_events_attested':0,
        'native_source_callback_invoked':False,
        'runtime_listener_interface_installed':False,
        'probe_has_independent_clock_or_coverage':False,
        'source_files_modified':False,
        'native_proof_obligations_unmet':[{'id':k,'verified':False} for k,_ in PORT_OBLIGATIONS],
        **NATIVE_ZERO,'claims_excluded':EXCLUSIONS,
    }
