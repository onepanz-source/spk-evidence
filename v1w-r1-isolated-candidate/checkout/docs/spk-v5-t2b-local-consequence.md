# SPK/* V5-T2b — Conseguenza locale dell'isola (controllo positivo sintetico)

**Status:** T1 ereditato PASS; T2b CONTROLLO POSITIVO CONDIZIONALE; T2 indipendente **NON certificato**; T3 RL/blind **BLOCKED**. Ricerca soltanto, 21 ottobre 2026.

## 1. L'ipotesi ristretta che questa prova affronta

La Back Validation può essere informativa *quando* un neurone destinatario riceve effettivamente una **misura locale delle conseguenze** della decisione altrui, e quando tale misura è statisticamente coerente con un obiettivo condiviso dell'isola. La sola conferma di ricezione non lo è (T1/T2 già chiuso).

Questo banco non scopre spontaneamente un reward semantico: **C riceve un secondo segnale contestuale deliberatamente allineato al compito**. È un controllo positivo di interfaccia, di causalità e di identificabilità condizionata. Un risultato positivo non dimostra l'esistenza di un sensore utile in un caso reale. L'obiettivo rimane dell'isola logica, non del singolo neurone.

## 2. Sorgente e osservazioni

- Si esegue direttamente `spk_architecture_v1.pe_execution_v1b.execute_on_pes_v1b` con tre nodi `A→B→C`, immutato e con collocazioni PE `single/split/spread`.
- A sceglie uno dei *tre programmi già dichiarati*: `overemit` (baseline), `silent`, `temporal` (soluzione positiva *già nota*, non appresa). Non si modificano programmi nativi.
- La risposta applicativa dell'isola resta l'emissione **C:7**. C genera inoltre **C:8** quando la propria memoria locale valida uno spike proveniente da B con un evento contestuale recente. **C:8 non è la risposta applicativa** e non viene conteggiato tra gli output classificati.
- In regime `aligned`, un evento esterno su C:0 compare a `t_first+2` **solo se il primo canale di A è C0**. Questa ridondanza è *progettata*: non costituisce una prova di osservazione indipendente in una rete reale. C non riceve il risultato atteso né il nome del programma candidato.
- In `inverted`, la medesima sorgente ridondante osserva invece C1; in `absent` il sensore è indisponibile. I tre regimi mantengono **lo stesso corpus, gli stessi programmi A e lo stesso output C:7**.
- Ogni A:7 raggiunge B dopo un tick, quindi C dopo un altro tick. L'osservatore **shadow** costruisce un receipt con i tre tempi e l'esito della *batch realmente elaborata da C*. In `aligned/inverted`, C:8 presente significa +1 e C:8 assente **dopo esecuzione confermata della batch** significa -1. In `absent` il giudizio è 0/ABSTAIN, mai -1 da mancata disponibilità sensoriale.
- La ricomputazione adversarial di un receipt è eseguita con lo **stesso motore A1b**: non è una testimonianza crittografica indipendente o un issuer production-grade. Non esiste messaggio di ritorno C→B→A nativo; B riceve l'esito solo tramite questa proiezione shadow.

## 3. Confronti e vincoli metodologici

**Corpo di sviluppo:** 8 blocchi × 7 pattern = 56 episodi; 8 positivi, 48 negativi. **Corpo di valutazione:** 6 blocchi × 7 pattern = 42 episodi; 6 positivi, 36 negativi. Ogni blocco usa lo stesso repertorio di pattern con timestamp traslati: questi **non sono soggetti/statistiche indipendenti**, né un holdout cieco. Un episodio può emettere due spike, quindi il numero di receipt non è uguale al numero di episodi. I pattern includono `C0→P` con gap 1 (positivo), `C1→P`, `P→P`, `C0→P` gap 2, `P`, `P→C0`, `C0→C0` (negativi).

Lo shadow selector osserva solo la **somma dei reward locali della singola candidatura**; la valutazione del compito resta separata dalla selezione. Usa una scansione fuori linea di tutti i candidati su tutti gli episodi, **non** una politica RL o contextual bandit in cui si osserva una sola azione per turno.

**Placebo:** 32 permutazioni a semi deterministici (`seed+1701`, seed da 0 a 31) riassegnano i segni alle vere emissioni A/B/C, mantenendo il totale dei receipt, il totale dei +1/-1/0 e il numero di eventi per candidato/episodio. La decisione sul credito è scorporata dalla sua sorgente, distruggendo la corrispondenza causale del *segno*. Il placebo **non** dimostra parità di consumo PE/memoria o scheduling BV v0e; confronti di quelle risorse sono esplicitamente fuori perimetro.

## 4. Risultati osservati

| Regime | Selezione shadow | Errori della politica scelta su 42 episodi | Placebo |
| --- | --- | ---: | --- |
| `aligned` | `temporal` | 0 | `silent` in 32/32, 6 errori |
| `inverted` | `silent` | 6 | `silent` 31/32, `temporal` 1/32 |
| `absent` | `overemit` | 30 | `overemit` 32/32 |

**Controlli candidati indipendenti dal regime sensoriale:** baseline `overemit` 30 errori (30 FP, 0 FN), `silent` 6 (0 FP, 6 FN), `temporal` 0. Il beneficio `aligned` **dipende intenzionalmente** dal test locale costruito per riconoscere il contesto. Inversione/assenza sono controesempi alla validità universale di un reward locale.

## 5. Cosa non è stato provato

1. Non esiste *task truth* esterna e blind, né custode indipendente. Il sensore duplicato è una costruzione del test, non un meccanismo SPK che generi da sé un reward valido.
2. La selezione offline di un programma già noto non dimostra reinforcement learning, credit assignment appreso, né causalità controfattuale. Una politica `silent` senza emissioni non riceve premi: questa asimmetria resta da modellare in RL.
3. Il canale di attestazione è **shadow**; non sono stati implementati delivery C→B→A, ACK paid, consumo P/S/E, firma production, fairness o adozione di programmi nel runtime BV v0e.
4. Le 42 osservazioni derivano da appena 7 pattern ripetuti a timestamp diversi: impossibile usare 42 come numerosità statistica indipendente. Gli errori sono conteggi descrittivi di questa fixture.
5. Nessuna topologia fisica/isola distribuita, nessun peso di sorgente e nessun nuovo chip.

## 6. Gate e prosecuzione

- **Gate SW:** verifica SHA dei sorgenti fissati, adversarial T2b, T1/T2 ereditato, test A1b, riferimento canonico identico e assenza di modifica ai sorgenti congelati.
- **Gate scientifico:** `T2b ENGINEERED POSITIVE CONTROL` dimostra soltanto che è *possibile* avere un giudizio locale utile in condizioni costruite. **T2 reale rimane BLOCKED**, non promosso a GO; **T3 vera validazione RL/blind rimane BLOCKED**.
- **Prossimo lavoro:** definire una conseguenza locale misurabile in modo indipendente dall'etichetta del task e dal sensore costruito su misura; introdurre esplorazione on-policy, credito anche per non-emissione e un dataset con obiettivo/holdout gestito da un custode realmente separato. Preregistrare la regola di aggiornamento, parità di costo e condizioni di stop prima della valutazione.

**Principio:** l'isola possiede l'obiettivo, il neurone possiede la scelta, il giudizio deve essere informativo e causalmente attribuibile. Un ACK valido senza utilità osservabile non diventa reward per decreto.
