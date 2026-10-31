# SPK/* — BV v0x: limite di osservabilità del valore informativo

## 1. Portata

v0x consolida le 15 celle × 3 bracci di **v0w** e separa tre affermazioni logicamente differenti:

1. Il feedback consuma risorse astratte del modello v0e e può introdurre attesa nello scheduler.
2. Gli esiti `forward` osservati nei 15 confronti coincidono come multinsiemi di output e stati finali, anche dove differiscono i tick.
3. **Il valore informativo del feedback non è identificabile nel modello v0e**: il payload non trasporta un giudizio valutabile rispetto a un obiettivo esterno; v0e non usa un giudizio per cambiare operatore, programma o aggiornamento dello stato neuronale.

Il punto 3 è un limite del *dispositivo sperimentale* v0e, non una dimostrazione che il feedback sia inutile per il neurone SPK.

## 2. Evidenza v0w

- 5 profili: `baseline`, `coincident`, `second_plus_1`, `second_plus_3`, `repeated_episode`.
- 3 configurazioni per profilo: `(fabric,inflight) = (1,4),(2,1),(2,4)`.
- 3 bracci: `OFF`, `ON forward-first`, `ON feedback-first`.
- 15 celle, 45 esecuzioni per processo; il report v0w certifica l'identità dei riferimenti v0v/v0u/v0t/v0o e l'invarianza dei dati d'ingresso *entro la cella*.
- Su report native 13 fornito il 18/10/2026: 15/15 celle con esiti forward conservati; 15/15 con ritardo forward nullo in `ON forward-first` rispetto a OFF; 6/15 con ritardo in `ON feedback-first`; 9/15 senza tale ritardo. Non si tratta di 15 prove statisticamente indipendenti.
- La somma di grant astratti incrementali nei 15 confronti ON vs OFF è 66, ma le tre configurazioni per carico sono rilanci della **stessa** fixture. Non usare 66 come stima di costo di un workload continuo o come misurazione hardware.

I contatori di contesa (`fabric_link`, `directional_link`, `inflight`) contano tentativi secondo il codice v0e. Non sono una misura fisica e non costituiscono da soli un bilancio causale di ogni tick.

## 3. Contratto minimo ancora assente

Per distinguere una **ricezione di feedback** da un **giudizio utilizzabile** servono almeno quattro oggetti separati:

`Judgment`: criterio di valutazione predefinito; valore/segno del giudizio; evidenza verificabile; autore/receiver; tick di disponibilità; regole di deduplicazione per la stessa origine causale. Un semplice `assessment_id` con `evidence_ids` non porta un valore valutativo.

`Decision`: neurone; stato pre-decisione; insieme degli operatori ammissibili; operatore selezionato; tick della decisione; identificatore della decisione e del contesto cui il giudizio si riferisce.

`Update`: test esplicito di causalità e finestra di eleggibilità; delta proposto alla *strategia di scelta*; bound di variazione; committibilità/reversibilità; eventuale no-op. L'aggiornamento non può usare feedback dal futuro.

`Evaluation`: obiettivo esterno dichiarato **prima** dell'esperimento, una sequenza futura holdout, braccio senza update, costo complessivo del feedback e del calcolo, attribuzione causale del contributo, e controllo contro l'aumento ingiustificato della complessità computazionale.

Proposta teorica, **non implementata**:

\[
  d_t = F_{\theta_t}(s_t, x_t), \qquad
  \theta_{t+1} = U(\theta_t, J_{\leq t}, E_t)
\]

Qui `F` è una semantica di calcolo SPK da definire rigorosamente, `J` è la parte valutativa del feedback, `E_t` è una prova locale di eleggibilità, e `U` è un ipotetico operatore di aggiornamento. Nessuna di queste equazioni autorizza una promozione nel Core/Network/Compiler/Architecture congelati.

**Domanda sperimentale successiva**: una politica neuronale adattiva, entro un budget identico, migliora un obiettivo predefinito su stimoli *successivi* rispetto al controfattuale `noop`, al netto dei costi e con giudizi la cui origine è verificata? Finché non esiste questo obiettivo, non si parla di apprendimento efficace.

## 4. Comandi

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v0x_Value_Observability_Boundary.tar.gz
bash search/spk_bv_v0x_research_gate.sh
python -m search.spk_bv_v0x_value_boundary \
  --v0w-13 /tmp/spk-bv-v0w-native-13.json \
  --v0w-811 /tmp/spk-bv-v0w-native-811.json \
  --recompute-native \
  --out /tmp/spk-bv-v0x-native-verified.json
bash search/spk_bv_credit_v0a_full_regression.sh
```

La CLI consente di omettere `--v0w-811` quando il secondo report non è disponibile, e riporta esplicitamente `cross_process_payload_equality_verified=false`. Il controllo `--recompute-native` ricalcola le 45 esecuzioni native con il codice sorgente di fwork **senza modificarlo**; il report non viene dichiarato ricomputato senza quella verifica. Il valore dei pin SHA di v0e viene controllato prima e dopo.

L'output e le eventuali fixture non sono mai scritti dentro la directory Git e non vengono sovrascritti. In assenza dell'archivio v0w e delle sue dipendenze, il comando rifiuta l'esecuzione.

## 5. Esclusioni

Nessuna prova di learning, qualità del giudizio, equivalenza di workload dinamici fra celle, scalabilità N-node, hardware o equivalenza allo stress sintetico v0h da 528 pacchetti. Architecture v1 e le altre versioni congelate restano inalterate.
