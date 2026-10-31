# SPK/* V5-T2c — domanda esogena simulata, chiusura osservabile, bandit shadow

**Stato:** esperimento di ricerca positivo *sul mondo sintetico dichiarato*, nessuna validazione blind, nessun learning nativo. **21 ottobre 2026**.

## 1. Ipotesi circoscritta

Il programma del neurone A può essere selezionato da feedback sul risultato dell'**isola logica A–B–C** quando C osserva due fatti distinti: (a) domanda ambientale *esplicita*, registrata tramite un proprio evento e (b) consegna/non consegna della risposta, con una **chiusura finale effettivamente elaborata**. La domanda è una variabile esogena del *simulatore*: viene scelta prima dell'azione, non in base al programma scelto. È definita dall'autore del benchmark ed è statisticamente correlata con gli ingressi di A. Non proviene da un sensore indipendente reale.

### Rapporto con T2b

T2b aveva un testimone C costruito direttamente per corroborare un pattern del compito. In T2c la variabile di domanda è campionata stocasticamente (con rumore condizionale non nullo), osservata in un **batch C separato** dopo la decisione di A, con due canali espliciti per vero/falso. Questo riduce il rischio di un feedback positivo automatico, ma **non** costituisce verità esterna indipendente: l'associazione domanda–contesto è scelta dal ricercatore.

## 2. Contratto dell'esperimento

- **A**: programma candidato congelato per la durata di un episodio, tra `overemit`, `silent`, `temporal`. A vede solo i propri eventi d'ingresso, **mai** la domanda C futura, né il reward.
- **B**: rilancio nativo A1b senza modifiche, unico arco A→B→C con `delay_ticks=1` per hop.
- **C**: il programma di *ricerca* emette canale 7 per ogni forward; canale 8 su **domanda vera** osservata (input C, ch4); canale 10 su **domanda falsa** osservata (input C, ch5); canale 9 su **chiusura** osservata (input C, ch6). Un batch sorgente deve essere effettivamente eseguito. L'ordine `ACC → CMP → EMIT → RESET` preserva i canali distinti.
- **Tempo:** il forward deve giungere prima di `t0+5`; domanda C a `t0+5`; chiusura C a `t0+6`. Il report confronta il segnale domanda *osservato*, non una precomputazione di `task_label()`.
- **Reward proxy**: `+1` se risposta e domanda concordano, `−1` se discordano, `None` se il sensore non esiste. L'eventuale omissione **può** generare `−1` soltanto dopo chiusura C e un batch C che afferma domanda vera. Mancanza di ACK, timeout o silenzio senza sensore **non** sono sentenze negative.
- **Tutela:** `ClosedReceipt` è verificata re-eseguendo il motore A1b in research; questo non autentica una sorgente reale, non crea una chiave di fiducia, non implementa un ritorno BV attraverso la rete nativa e non costituisce un ledger persistente.

## 3. Selezione per bandit, niente informazione controfattuale al learner

*Explore-then-commit* con 504 episodi di training, sei combinazioni negative e una positiva per template, e tre candidati: 168 scelte casualmente bilanciate per programma e per pattern. Per ciascun episodio viene **eseguito un solo programma**; lo shadow learner vede il solo reward di quel programma, e stima la sua media. Una volta terminata l'esplorazione, seleziona l'arm con media maggiore. Nessun algoritmo modifica un neurone o la sua memoria P/S/E/O.

Il **valutatore esterno** esegue successivamente i tre candidati su 70 episodi di valutazione in un seed separato, esclusivamente per il report. Questi episodi NON sono blind né soggetti indipendenti. La politica candidata è fissata prima della loro valutazione.

I quattro regimi sono:

- `aligned`: probabilità di domanda C vera 0,86 per template `C0→P` e 0,12 per gli altri;
- `inverted`: rispettivamente 0,14 e 0,88;
- `decoupled`: 0,5 per ogni pattern;
- `absent`: domanda C non osservabile; c'è soltanto la chiusura C, **nessuna ricompensa**.

**Placebo:** in ciascun regime, 32 permutazioni dei bit di domanda sui 504 episodi di training. Mantengono il multinsieme dei bit e l'esatta sequenza di programmi scelti: rompono la relazione con il contesto. Non pretendono di misurare PE/memoria/link del trasporto del feedback, ancora shadow.

## 4. Risultati di riferimento e limiti

La misura primaria di questo *pilot esplorativo* è errore binario rispetto alla domanda C negli episodi di valutazione, distinta dal numero di spike e da FP/FN. Per il rapporto completo, usare `docs/spk-v5-t2c-reference.json`.

- `aligned`: scelta temporal, errore 10/70; silent 18/70; overemit 44/70. Placebo: silent 30/32, temporal 2/32.
- `inverted`: scelta overemit, errore 25/70, inferiore a temporal 61/70.
- `decoupled`: non dimostra una relazione informativa sistematica; la scelta è dipendente dal campione casuale, non una prova di generalizzazione.
- `absent`: zero reward osservati su 504 episodi, 504 astensioni e scelta conservativa della baseline overemit. Il report sui 70 episodi senza sensore segna 70 **non valutabili**, non 70 successi.

### Evidenze negative / confini

1. Il nuovo segnale è un **proxy dell'obiettivo** installato nell'isola sperimentale, non un'utilità del destinatario emergente spontaneamente. L'obiettivo island è esplicito: soddisfare una domanda ambientale quando presente e non produrre falsi interventi.
2. La presenza di una domanda simulata trasporta informazione semantica esterna, quindi non dimostra che una rete possa inferire da soli ACK il proprio scopo.
3. L'esperimento bilancia la frequenza di prova ma non i veri costi di PE/memoria/backpressure della Back Validation in v0e. Il ritorno dei giudizi avviene soltanto nello shadow observer.
4. Il selettore usa esplorazione di una **lista finita predefinita** e un solo programma per episodio, non gradienti, pesi o modifiche autonome al codice nativo. È un contextualized stochastic-bandit proxy, **non** una validazione di RL multistadio.
5. Niente etichette di test custodite indipendentemente, inferenza statistica preregistrata, chiavi vere, hardware/mesh o program promotion.

## 5. Gate

```bash
bash search/spk_v5_t2c_exogenous_demand_gate.sh \
  /tmp/spk-v5-t2c-exogenous-demand.json
```

La destinazione deve essere nuova (create-only) e esterna alla repository. Il gate blocca drift dei sorgenti pin, regressioni, anomalie del report e sovrascritture. Il giudizio scientifico è limitato al mondo sintetico, non autorizza T3 blind o learning nativo.

## 6. Prossima attività

Prima di promuovere T3: definire e validare un **contratto di osservazione locale di un obiettivo d'isola in un ambiente distinto dal generatore dell'esperimento**, includendo trigger di domanda, termine di opportunità, feedback su non-azione, errori di sensore e accoppiamento ai veri costi BV; preregistrare metrica/soglie e tenere un holdout sotto altra custodia. Per V5-T3 shadow si potrà confrontare bandit, placebo e baseline in distribuzioni nuove. Non modificare freeze precedenti.
