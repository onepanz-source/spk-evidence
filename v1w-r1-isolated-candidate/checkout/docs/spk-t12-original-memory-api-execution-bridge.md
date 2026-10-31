# SPK V5 T12: macro collegamento eseguibile alle API ORIGINALI di memoria

## Confine di compatibilità

Il riferimento T11 ammette e applica aggiornamenti di `C/P` nel nuovo runtime V1. Il Memory Contract congelato non è stato invocato. T12 esegue per la prima volta un *tentativo verificabile* di ricostruzione dell'ammissione, proiezione e autorizzazione di memoria con le cinque API originali `spk_architecture_v1/memory_*`. Le impronte SHA-256 di queste sorgenti provengono dall'inventario originale T11 eseguito sul checkout completo fwork.

### Macro-workstreams accorpati

1. Origine: codice originale verificato con SHA e AST delle firme, prima dell'import.
2. Preparazione: caso A/B/C ammesso con `case_for`, collocazione `plan_v1a`, servizio originale e piano memoria `uniform_memory_plan_v1a`.
3. Esecuzione: `admit_memory_v1a`, `execute_on_pes_v1b`, `project_execution_memory_v1a`, `authorize_projection_v1b` per quattro combinazioni di scelta/obiettivo. `serve_projection_v1c` viene tentato separatamente e i rifiuti sono registrati.
4. Confine d'autorità: l'eventuale successo delle autorizzazioni originali riguarda **l'accesso computazionale alla memoria**, NON concede modifiche alla politica di apprendimento P.
5. Parità T11: scenari con tre decisioni, affinità per contesto e ripresa dopo interruzione; output 84, 88, 88 su 96 episodi, con otto grant soltanto del nuovo runtime V1.
6. Avversariale: rifiuto di codici falsi con hash diverso, controllo grant obsoleti, quota zero, profilo `verify`, transazioni e riapertura. Nessun componente congelato viene modificato.

Il nuovo gate è **fail closed**: su `fwork` le cinque sorgenti originali devono essere presenti e con hash corretto, e almeno un caso originale deve superare l'ammissione memoria. Se non accade, si arresta con `ORIGINAL_MEMORY_ADMISSION_FAILED_ALL_CASES` e diagnostica. Non produce un report con `PASS` usando stub.

Il report locale su un checkout incompleto può essere prodotto *soltanto* usando il flag `--allow-missing-native` e assume lo stato `LOCAL_PARTIAL_CHECKOUT_NO_ORIGINAL_MEMORY_MODULES`; quel flag NON compare nel gate di rilascio.

## Cosa non prova

- `authorize_projection_v1b` non è un'autorità per l'apprendimento P del neurone. I grant di lettura/scrittura per esecuzione originale sono contati separatamente, e in ogni caso non permettono promozione.
- Non autentica le sorgenti A né i suoi obiettivi. L'host privilegiato resta capace di contraffare/risigillare il riferimento.
- Non trasporta giudizi semantici dentro BV-v0e; non tocca i contratti congelati.
- Gli obiettivi rimangono due contesti sintetici, senza generalizzazione.

## Prossimo criterio di accettazione nativo

Solo dopo aver dimostrato le reali forme degli oggetti `MemoryAdmissionV1a`, `AccessAuthorityV1b`, proiezioni e permessi si potrà definire un contratto di transazione P versionato che trasferisca legittimamente la custodia dell'aggiornamento dalla routine computazionale al memory owner. Non si assume che questo trasferimento sia possibile tramite la API originale senza nuova versione.
