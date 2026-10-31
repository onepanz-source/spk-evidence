# SPK V5-T3g: protocollo prospettico di valutazione, ricerca

**Questa versione non valida alcun risultato su dati futuri.** Sigilla prima un file di sole misure e poi permette un rapporto dopo che sono state rese disponibili etichette esterne. I campi sono volutamente minimi e le soglie, il programma e i criteri vengono congelati in `spk-v5-t3g-protocol.json`.

## Motivazione scientifica

T3f ha rivelato che l'intero guadagno di `persist` derivava da due giornate senza presenze. L'endpoint primario del nuovo audit è perciò la differenza media **per giorno con almeno una presenza**, senza assumere indipendenza delle letture minuto per minuto. L'endpoint non contiene ore o etichette nelle caratteristiche presentate all'A1b.

## Flusso, due stadi

1. Il curatore prepara, con **nuove misure dopo il cutoff**, `features.csv` nel formato `timestamp_utc,light_lux`, UTC `Z`, strettamente ordinato, 59/60/61 s tra le letture valide. Servono almeno 10 giornate con >=60 coppie valide ciascuna. L'operatore invoca `precommit` **senza fornire etichette** e pubblica l'impronta SHA-256 della certificazione. Lo script NON legge etichette.
2. Solo dopo la registrazione del digest, un soggetto fornisce `labels.csv` con righe `timestamp_utc,occupied` (0/1), ordinato e in esatta corrispondenza. `evaluate` verifica sorgenti, timestamp, hash del precommit, protocollo e custodisce gli esiti per giornata. I dati UCI 2015 sono vietati dal formato/cutoff e dalla loro SHA nota.
3. I due candidati già esaminati sono `current` e `persist`, riconosciuti dalla tabella esaustiva dell'esecutore A1b in T3e; la politica candidata non è ottimizzata dopo la lettura delle nuove etichette. Si riportano numero di giorni con presenza, vinti/persi/pareggiati, errore medio giornaliero appaiato, test del segno *descrittivo*, aumento di falsi negativi e diagnostica giorni vuoti.
4. I risultati sono `INSUFFICIENT` (non abbastanza giorni con presenza o disaccordi), `NO_SUPPORT` (criteri non raggiunti), oppure `SCREEN_SIGNAL_ONLY` (criteri preregistrati raggiunti). Quest'ultimo **non** è dimostrazione causale, indipendenza né apprendimento nativo.

## Assicurazioni e limiti

- SHA-256 lega **byte** e codice di riferimento, non attesta l'origine fisica né impedisce a un operatore di conoscere le etichette. La custodia cieca richiederebbe un soggetto esterno non presente.
- Non esistono garanzie di indipendenza delle giornate; i test per giorno riducono la pseudoreplicazione ma non la eliminano. Nessun p-value può essere presentato come prova sufficiente da solo.
- La regola a due letture è identica alla versione Python booleana; una sua vittoria eventuale non dimostra superiorità neuromorfica.
- Nessun nuovo schema modifica Core, Compiler, Architecture v1, BV v0e, l'ammissione PE o la topologia. Nessun aggiornamento autonomo del programma.
- I file di QA usati nel gate sono **artificiali**; il milestone non contiene nuovi dati esterni, non esegue un blind holdout e non certifica un risultato empirico.

## Esempi di chiamata quando saranno disponibili dati nuovi

```bash
python search/spk_v5_t3g_prospective.py precommit \
  --features /path/to/new_features.csv --source-id independent-site-001 \
  --out /tmp/spk-v5-t3g-precommit.json

PILOT_SHA=$(sha256sum /tmp/spk-v5-t3g-precommit.json | awk '{print $1}')

python search/spk_v5_t3g_prospective.py evaluate \
  --features /path/to/new_features.csv --labels /path/to/later_labels.csv \
  --precommit /tmp/spk-v5-t3g-precommit.json --precommit-sha256 "$PILOT_SHA" \
  --out /tmp/spk-v5-t3g-evaluation.json
```

**NON usare i tre file UCI già analizzati come dati nuovi.**
