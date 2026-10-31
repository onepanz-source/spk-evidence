"""T9MNO: context-aware admission experiment on unchanged reference V1 engine."""
from __future__ import annotations
import tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import MultiTickEngine,ensure,digest
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from .stale_evidence_v1 import HistoricalEvidence, attestable_stale

def run_strategy(strategy,*,reopen_each_wave=False, record_evidence=True,learn=True):
    ensure(strategy in ('serial','batch3','context_affinity'),'UNSUPPORTED_ADMISSION_POLICY')
    ordered=list(enumerate(tasks()))
    with tempfile.TemporaryDirectory(prefix='spk-t9-frontier-') as tmp:
        e=MultiTickEngine(Path(tmp)/'scheduler.sqlite',learn=learn,max_inflight=3)
        ledger=HistoricalEvidence(Path(tmp)/'historical.sqlite')
        remaining=ordered[:]; assigned={};wave_sizes=[];step_count=0
        while remaining:
            selected=[];seen=set()
            for original,(cue,goal) in remaining:
                if len(selected)>=3 or (strategy=='serial' and selected):break
                if strategy=='context_affinity' and cue in seen:continue
                selected.append((original,cue,goal));seen.add(cue)
            ensure(selected and len(selected)<=3,'ADMISSION_DEADLOCK')
            for original,cue,goal in selected:
                assigned[original]=e.submit(cue,goal)
            if reopen_each_wave:e.reopen()
            steps=e.run();step_count+=len(steps)
            wave_sizes.append(len(selected))
            if reopen_each_wave:e.reopen()
            remaining=[x for x in remaining if x[0] not in assigned]
        audit=e.audit()
        historic=attestable_stale(e)
        if record_evidence:
            for row in historic:ledger.append(row)
        ledger_result=ledger.audit()
        ensure(ledger_result['P_grants']==0 and
               (ledger_result['historical_records']==audit['stale_vetoes'] if record_evidence else
                ledger_result['historical_records']==0),'HISTORICAL_CREDIT_BOUNDARY')
        result_rows=[e.result(assigned[i]) for i in range(len(ordered))]
        successes=sum(x['outcome']=='IMPROVED' for x in result_rows)
        ensure(all(x['cue']==ordered[i][1][0] and x['goal']==ordered[i][1][1]
                   for i,x in enumerate(result_rows)),'TASK_ORDER_DRIFT')
        if reopen_each_wave:ledger.reopen();ensure(ledger.audit()==ledger_result,'HISTORICAL_REOPEN_DRIFT')
        result={'strategy':strategy,'max_inflight_admitted':max(wave_sizes),'capacity_limit':3,
            'episodes':len(result_rows),'waves':len(wave_sizes),'dispatcher_slots':step_count,
            'successes':successes,'P_grants':audit['reference_v1_tick_grants'],
            'P_writes':audit['P_writes'],'stale_vetoes':audit['stale_vetoes'],
            'historical_evidence':ledger_result,'rows_digest':digest(result_rows),'core_rows_digest':digest([{k:r[k] for k in ('id','cue','goal','choice','version','outcome','grant')} for r in result_rows]),
            'wave_sizes_digest':digest(wave_sizes),'reopen_each_wave':reopen_each_wave,
            'native_SPK_P_grants':0,'native_learning':False}
        ledger.close();e.close()
        return result
