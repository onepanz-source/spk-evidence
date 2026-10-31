# SPK/* V5-T2d — osservazione dell'isola, guasti del sensore e shift

**21 ottobre 2026 · stato: ricerca sintetica diagnostica, NON GO per T3 blind.**

## Scopo

Dopo T2c, non assumere che il giudizio causale positivo o negativo proveniente da C sia semanticamente vero. La chiusura dell'episodio e il corretto arrivo del bit di domanda **non certificano** né la qualità del sensore né l'utilità effettiva per l'isola.

Questo milestone usa davvero il motore **A1b congelato** per A→B→C e l'elaborazione a C dei segnali di domanda e chiusura. Il segnale di feedback è letto da un observer shadow, non percorre il canale BV nativo; i costi del ritorno BV non sono contabilizzati.

Due registri logici distinti:

1. **Mondo sintetico**: la domanda viene estratta *prima* della scelta del programma A e non dipende da questa. Il bit del mondo e le sue identità di episodio vengono conservati esclusivamente dall'auditor per stimare il risultato del compito. Si tratta del medesimo mondo simulato T2c: non è verità di terza parte e non è crittograficamente separato.
2. **Osservazione del neurone C**: uno stream distinta, che può perdere o invertire domanda e non-domanda. Soltanto questa osservazione, effettivamente elaborata da C con chiusura verificata, produce un `ClosedReceipt` e una ricompensa per lo shadow bandit. L'auditor non viene consultato per la selezione.

La policy A è scelta *una sola volta per episodio* in esplorazione; 504 episodi, 168 scelte per ciascun candidato e sequenza dei programmi fissata e uguale per tutti i scenari. Non esiste correzione della policy nativa. L'auditor valuta in seguito 70 episodi distinti contro il bit originale del mondo sintetico; questi 70 episodi **non sono blind**.

## Stress test

| Sensore C durante training | Programma scelto | Errori veri su 70, mondo aligned | Osservazioni mancanti su 504 | Bit osservati erronei su 504 |
| --- | --- | ---: | ---: | ---: |
| Corretto | temporal | 10 | 0 | 0 |
| Flip probabilità 0,10 | temporal | 10 | 0 | 56 |
| Flip probabilità 0,35 | temporal | 10 | 0 | 186 |
| Tutti i bit invertiti | overemit | 44 | 0 | 504 |
| Drop casuale probabilità 0,30 | temporal | 10 | 158 | 0 |
| Drop 0,90 delle vere e 0,05 delle false | silent | 18 | 129 | 0 |
| Sensore totalmente assente | overemit, baseline conservata | 44 | 504 | 0 |

I tassi indicati sono **parametri del guasto**, non percentuali osservate esatte: il conteggio avviene su un unico campione deterministico. La permanenza della scelta temporal con flip al 35% NON certifica una soglia di robustezza; altri seed o altre condizioni potrebbero fallire prima.

La perdita selettiva è istruttiva: **zero valori falsi**, ma osservazioni mancanti prevalentemente quando la domanda vera avrebbe premiato un'azione. Il learner seleziona `silent` e peggiora la misura vera. L'assenza di dato va quindi modellata come `unknown`, non come `false`, ma questa precauzione da sola non risolve il *missing not at random*.

### Shift del mondo

Mantenendo la policy scelta nello scenario `clean`, ma valutando un mondo in cui è invertita la probabilità di domanda dato il contesto, `temporal` commette 61 errori su 70 contro 10 nell'ambiente iniziale; `overemit` commette 25 errori nel mondo invertito. I due mondi sono **costruiti dallo sperimentatore**. Non segue alcuna inferenza sulla robustezza a distribuzioni naturali o nel tempo reale.

### Controlli

- Una ricompensa positiva prodotta da C a sensore falso è causalmente riproducibile, ma può essere un errore per l'obiettivo dell'isola; la prova avversaria confronta il `ClosedReceipt` con il bit custodito dal solo auditor.
- Un sensore assente produce `None/abstain`, anche con chiusura corretta. La mancanza della chiusura causa rifiuto, **mai** una ricompensa negativa inventata.
- Il report contiene per ogni regime un placebo di 16 rimescolamenti delle osservazioni, che preservano azioni e distribuzione marginale di veri/falsi/assenti ma rompono l'associazione episodio-osservazione. Non è un p-value preregistrato.
- Ogni report è esatto byte per byte, vincolato a SHA-256; gli hash controllano drift accidentale o non autorizzato rispetto ai pin, **non** stabiliscono fiducia esterna se lo stesso attore può sostituire insieme manifest e file.
- I test rifiutano replays/alterazioni dei receipt, chiusure assenti, modifiche di identità e drift dei registri. Il tutto è nel perimetro di un laboratorio in-process, senza identità di rete reale.

## Verdetto

**T2d capacità sperimentale: PASS. T2 semantica indipendente: NON CERTIFICATA. T3 blind / learning nativo: BLOCCATI.**

Il risultato in negativo è significativo per il design del contratto BV: il giudizio deve portare non soltanto causalità e timestamp, ma **qualità della misura, astensione, provenienza semantica, contesto del campionamento e validità temporale dell'obiettivo**. Non introdurli ora nei contratti congelati: sono condizioni per la futura ricerca di RL, non una promozione di Architecture v1.

## Passaggio successivo consigliato

Non fare altri cinque studi con probabilità arbitrarie. Servono: (1) una sorgente di compiti o un ambiente realmente indipendente, con semantica degli esiti documentata e criteri di partizione congelati; (2) un contratto di feedback il cui costo di reverse BV sia verificato contro la ricerca v0e e non ipotizzato gratuito; (3) una prova registrata in anticipo di apprendimento shadow con shift e missingness. Nessuna modifica a Core/Network v0, Compiler v0, Architecture v1 o BV v0e senza distinto release process.

## Esecuzione

```bash
cd ~/workspace/spk-backvalidation-v0
bash search/spk_v5_t2d_sensor_robustness_gate.sh /tmp/spk-v5-t2d-sensor-robustness.json
```

La destinazione dev'essere esterna al repository e non preesistente (create-only). I file distribuiti sono solo nuovi, nessuna sovrascrittura del congelato.
