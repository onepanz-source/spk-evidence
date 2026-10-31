SPK V5 T3XYZ - Evidenze originali per recupero offline
======================================================
Questi sono i tre file originali della sessione T3XYZ del 21 ottobre 2026.
Non modifica alcun sorgente del repository. La traccia contiene 64.615
record JSONL, 47.545.722 byte, con copertura Python parziale.

Uso su Fedora:
  cd ~/workspace/spk-backvalidation-v0
  mkdir -p ~/workspace/spk-evidence
  tar -xzf ~/Scaricati/SPK_V5_T3XYZ_Original_Evidence_20261021.tar.gz -C ~/workspace/spk-evidence
  (cd ~/workspace/spk-evidence/spk-v5-t3xyz-20261021 && sha256sum -c SHA256SUMS)
  bash search/spk_v5_t3xyz_trace_recovery_gate.sh \
    /tmp/spk-v5-t3xyz-trace-recovery.json \
    "$HOME/workspace/spk-evidence/spk-v5-t3xyz-20261021/spk-v5-t3xyz-passive-observation"

Non e' un nuovo gate nativo: riprende soltanto la recovery precedente.
