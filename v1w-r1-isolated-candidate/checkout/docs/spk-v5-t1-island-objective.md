# SPK/* V5-T1/T2 — Isola logica minima, fattibilità e limite del giudizio locale

**Stato:** ricerca v0, task sintetico *non blind*. **T1 PASS; T2 NO-GO; T3 non autorizzato**.

## Esecutore e freeze

L'esecuzione usa **direttamente** `spk_architecture_v1.pe_execution_v1b.execute_on_pes_v1b` e
`plan_v1a` per tre nodi `A→B→C`. Le classi Case/Node/Edge/Event sono il
fixture tipizzato A1 già presente in `search.spk_24n_independent_oracle_v0`.
Ogni episodio istanzia una rete nuova. Nessuna modifica a Core, Network,
Compiler, Architecture v1 o a `live_dual_scheduler_v0e.py`.
L'A1b è un PE executor a trasporto ideale, **non** il runtime BV v0e con
contesa reale: questo test non certifica budget/latency fisici né crediti BV.

## Obiettivo logico dell'isola

`C0=0`, `C1=1`, `P=2` in ingresso ad A; attesa C terminale su canale 7.
L'isola deve emettere uno spike **solo** per `C0 → P` a distanza di 1 tick.
Tutte le altre coppie, l'ordine invertito, `P→P` e gli ingressi isolati sono
negativi. Due passaggi di relay A→B (1 tick) e B→C (1 tick).

Una soluzione finita con gli operatori ammissibili esiste:

```python
(('SHIFT',1), ('ACC',(2,0)), ('ACC',(4,2)),
 ('CMP',5), ('EMIT',7), ('CMP',4), ('RESET',0))
```

Il secondo confronto e RESET sono importanti per evitare che due P consecutivi
vengano scambiati per C0→P. La memoria locale di A è il registro `raw`.

## Bracci esplorativi, non RL con politica nativa

- `overemit`: programma iniziale che emette per P senza verificare il contesto.
- `silent`: controllo che non emette mai.
- `temporal`: controllo positivo noto a priori. Non è stato appreso.

B usa il **solo output del relay** come feedback locale positivo. Questo non è
un giudizio semantico affidabile del risultato dell'isola: in una traccia
errata B emette comunque. La scelta `select_by_feedback` riceve soltanto
conteggi di ACK per candidato; non vede etichette né perdita. La condizione
placebo conserva quantità e costo astratto dei riscontri e ne cambia
l'associazione temporale; non equivale alla contabilità BV pagata di v4s–v4u.

## Divisione e limiti

- 21 episodi sintetici di scelta, con timestamp 0 e gap 1/2.
- 30 episodi sintetici di valutazione, con timestamp 5 e gap 1/2/3.
- 1 solo positivo nella valutazione: **sbilanciamento grave**. Per questo
  calcoliamo FP, FN e balanced error e **non** attestiamo miglioramenti statistici.
- Gli episodi vengono generati dallo stesso task noto agli sviluppatori:
  questo NON è un holdout cieco o una sorgente indipendente di verità.
- Il solo fatto che B accetti lo spike non gli conferisce accesso al label;
  a parità di osservazione locale, due obiettivi esterni diversi possono
  assegnare errori opposti.

La ricerca **non** dimostra apprendimento, reward causale, compatibilità
runtime BV pagato, fairness nativa, né Generalizzazione OOD.

## Gate e arresto preregistrato

T1 PASS se le sequenze e controlli avversi superano il test sul motore A1b,
comprese le tre collocazioni PE. T2 PASS solo se B produce informazione
predittiva sul *contributo all'obiettivo dell'isola*, indipendente dai label
di valutazione. La proxy attuale fallisce T2: riscontri positivi compaiono
anche nelle decisioni sbagliate. **Arrestare la promozione a T3/RL**.
Il confronto shadow illustrativo è una diagnosi, non una validazione A/B/C.

**Prossimo passo consentito:** definire un sensore di conseguenza locale in B,
con segnale negativo possibile, credito attribuibile ad A e verifica che B
non legga la risposta del test. Poi preregistrare il confronto A/B/C con
costo reale ACK/consumer pareggiato ed episodi indipendenti più equilibrati.
