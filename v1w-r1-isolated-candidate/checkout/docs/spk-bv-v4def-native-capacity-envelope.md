# SPK/* BV v4d–v4f — capacità nativa osservata vs riserva ACK candidata

**Ricerca source-backed, nessuna adozione nativa.** Estende la bozza v4a–v4c
con 18 replay indipendenti dal ledger derivato: per ogni scenario, il digest
completo del risultato nativo resta identico alla sorgente v3t–v3v firmata.
Non modifica `execute_live_v0e`, Architecture v1, Core, Network o Compiler.

## Verifica di continuità

Il gate `fwork` dell'antecedente v4a–v4c ha superato **14 test nuovi e 217
ereditati**, incluse le 20 prove v2p. Il precedente errore locale v2p era
causato soltanto da una copia JSON storica troncata nella snapshot di
ricerca, non da codice del contratto candidato.

## V4d: accoppiamento fra risorse native e ACK osservati

Si sono letti i vettori `resources.timeline` dello scheduler congelato,
ricostruendo i 18 run (3 sequenze × 3 modalità × 2 capacità PE) e allineando
ogni tick alle 72 tracce ACK derivate (2 politiche × 2 quote per run).
Le capacità PE globali `1` e `2` sono **unità logiche del simulatore**,
non throughput di un microcontrollore. Le 72 tracce condividono i 18
background nativi e non rappresentano 72 esperimenti indipendenti.

L'attore sorgente `A` appartiene a `PE0`; si controllano separatamente:

- budget PE globale e quello di `PE0`;
- memoria globale, memoria proprietario `PE0` e domini O/E;
- un eventuale ACK aggiuntivo come costo controfattuale `1 PE + 2 memoria`.

Un tick con ACK effettivamente concesso deve trovare spazio *reale* nel
budget nativo prima del servizio derivato. Il sistema verifica questa
condizione per tutti i 329 grant originali senza creare nuovi ACK.

| Misura su 72 contesti source-backed | Conteggio |
|:--|--:|
| Tick sorgente complessivi | 2.560 |
| ACK realmente concessi | 329 |
| Tick con ACK pronto, 0 grant | 1.812 |
| Di cui PE globale pieno | **1.294** |
| Di cui PE globale libero ma PE owner pieno | 0 |
| Di cui PE disponibili ma memoria O/E insufficiente | 0 |
| Di cui tutte le risorse native con margine | **518** |

I 518 tick con margine indicano *possibilità di allocazione*, non servizio
garantito: mancano ancora credito valido, ammissione, precedenza e arbitro.
Viceversa, i 1.294 tick senza PE globale libero non possono aggiungere un
ACK simultaneo conservando tutti i grant nativi a capacità invariata.

## V4e: costo inferiore per finestra sotto saturazione

| Lunghezza W | Finestre ACK pronto e nessun grant | Di cui senza slot nativo disponibile durante tutta la finestra | Con almeno uno slot potenzialmente libero |
|--:|--:|--:|--:|
| 1 | 1.812 | 1.294 | 518 |
| 2 | 1.615 | 1.128 | 487 |
| 4 | 1.359 | **950** | 409 |
| 8 | 955 | **708** | 247 |

Le finestre **si sovrappongono**: la somma delle colonne non equivale a
un numero di servizi da preemptare. Per ogni singola finestra senza slack,
però, garantire almeno un ACK richiede almeno una delle seguenti opzioni:

1. sottrarre un'unità PE a un servizio nativo esistente (forward **oppure** BV);
2. aumentare la capacità fisica/logica e definirne il contratto;
3. non ammettere quella finestra/rango e dichiarare l'incompletezza.

Per il caso limite di saturazione **continua**, la quota media minima di
capacità globale occupata dalla riserva di un ACK per finestra è:

\[ \frac{1}{W\,C_{PE}}. \]

| Finestra W | PE globale 1 | PE globale 2 |
|--:|--:|--:|
| 2 | 50% | 25% |
| 4 | **25%** | **12,5%** |
| 8 | 12,5% | 6,25% |

Queste percentuali sono un **envelope analitico condizionato** su piena
saturazione, non perdite forward misurate. Senza un nuovo scheduler non è
determinabile quale servizio nativo sarà spostato, di quanti tick o con
quale effetto computazionale. Non è corretto chiamarle penalità di
prestazione effettiva.

## V4f: controllo dell'orizzonte e del rango

La durata delle 18 tracce native varia da **17 a 45 tick**, con clock di
inizio non sempre `1`. La precedente finestra illustrativa `W=4, Q=16`
richiederebbe fino a **64 tick dal momento dell'ammissione**: nessuna
traccia nativa corrente possiede un orizzonte così lungo. Nemmeno
`W=8, Q=16` è coperta. Il profilatore conta i tick in cui la **lunghezza
della coda pronta** supera il rango massimo certificabile nel tempo residuo:

- 1.274 tick sorgente per W=4;
- 1.679 tick sorgente per W=8.

Questo numero non è un conteggio di violazioni né una stima di tempi
reali: il servizio W non è mai stato ammesso. Indica precisamente cosa
non può diventare una prova di deadline nei run esistenti.

**Ne segue una scelta progettuale ancora aperta:** decidere quali
backlog/ranghi ammettere, quali PE riservare, quanta latenza forward
accettare e quale orizzonte usare nel *nuovo* esecutore candidato.

## Gate riproducibile su fwork

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v4def_Native_Capacity_Envelope_Milestone.tar.gz

bash search/spk_bv_v4def_native_capacity_envelope_gate.sh \
  /tmp/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4abc-native-contract-candidate.json \
  /tmp/spk-bv-v4def-native-capacity-envelope.json

bash search/spk_bv_v4def_inherited_regression_gate.sh
```

Lo stato del report resta
`SOURCE_REPLAY_RESOURCE_OPPORTUNITY_ONLY_NO_RESERVED_ACK_ADMISSION`.
Non sono state introdotte deadline native, fairness universale,
apprendimento nativo o variazioni ai congelamenti esistenti.

| Roadmap Simulator/Compiler | Avanzamento | Δ |
|:--|--:|--:|
| S1 | 100% | 0 pp |
| S2 | 100% | 0 pp |
| S3 | 60% | 0 pp |
| S4 | 0% | 0 pp |
| S5 | 0% | 0 pp |
| **Totale (media paritaria)** | **52%** | **0 pp** |
