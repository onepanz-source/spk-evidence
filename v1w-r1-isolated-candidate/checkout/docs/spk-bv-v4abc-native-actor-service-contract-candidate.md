# SPK/* Back Validation — contratto candidato di servizio nativo vNext

**Stato: BOZZA NON AMMESSA, NON IMPLEMENTATA.** Ricerca cumulativa v4a–v4c.
Questa specifica non modifica Architecture v1, né
`spk_backvalidation_v0/live_dual_scheduler_v0e.py`, né Core, Network o
Compiler congelati. Nessuna nuova garanzia viene attribuita al runtime.

## 1. Motivazione verificata (v4a)

L'esecutore `execute_live_v0e` ammette due classi di trasporto (spike
forward e pacchetti BV). Decide la priorità **sul link**, con risorse PE,
memoria e trasporto condivise; non possiede una coda nativa di ACK
receiver→actor, un registro del credito dell'attore o l'esecuzione
dell'applicazione di quel credito. Le implementazioni v2h–v3v di queste
funzioni sono *derivate* e verificate per proiezione sul nativo originale.

Il report canonico v3t–v3v, SHA-256
`f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827`,
contiene 72 replay derivati da 18 workload nativi, 36 null e 329 grant
ACK source-backed. Il nuovo audit non genera workload artificiali:
controlla le 2.560 righe di tick effettivamente già osservate.

| Finestra osservata | Contesti con almeno una finestra di ACK pronto e 0 grant | Finestre sovrapposte |
|:--|--:|--:|
| 1 tick | 72/72 | 1.812 |
| 2 tick | 72/72 | 1.615 |
| 4 tick | 65/72 | 1.359 |
| 8 tick | 56/72 | 955 |

Queste finestre misurano la *mancanza osservata di un grant a fronte di
controlli in attesa*; includono anche casi che una nuova policy potrebbe
non ammettere per credito, saturazione, durata o risorse. Non sono dunque
una misura di violazioni di una SLA ancora inesistente. Massimo intervallo
di ACK pronti senza grant: **36 tick** nel campione.

## 2. Risultato di impossibilità e lemma condizionale (v4b)

Con capacità globale `1 PE/tick`, se al tick `t` un batch forward richiede
quell'unico grant e un ACK richiede anch'esso `1 PE`, non possono entrambi
essere eseguiti in `t`. Un contratto che richieda sia esatta temporizzazione
forward sia ACK nello stesso tick è inconsistente, salvo nuova capacità
fisica/logica indipendente o una diversa definizione esplicita delle risorse.

**Lemma di servizio condizionato:** data una coda FIFO non elusiva ordinata
da `(due_tick, judgment_id)`, un ACK in posizione `r` al tick di ammissione
`t₀` viene servito entro `t₀ + rW − 1` **soltanto se** finché vi sono ACK
ammissibili in attesa si realizza almeno un grant alla testa della coda in
ogni blocco di `W` tick, compreso il blocco che inizia a `t₀`, e non
subentrano eventi che saltino davanti a quell'ACK.

Dimostrazione: per induzione sui blocchi di `W` tick. Al termine di ogni
blocco non vuoto la coda FIFO ha perso almeno una delle `r` posizioni
iniziali. Dopo al massimo `r` blocchi l'ACK è stato servito. Senza
l'ipotesi del tasso minimo esiste un'estensione con **zero grant futuri**,
indistinguibile da ogni prefisso finito: nessuna deadline segue dal solo
rango FIFO. Il verificatore enumera 682 sequenze finite (finestre e ranghi
1–3), senza controesempi al lemma sotto le sue premesse; l'induzione è
l'argomento generale, l'enumerazione è controllo avversariale limitato.

Se `t₀` arriva troppo vicino all'orizzonte nativo per ospitare `rW` tick,
il risultato è `HORIZON_INCOMPLETE_NO_CERTIFICATE`, non giudizio negativo,
silenzio provato o ACK riuscito.

## 3. Modello di evento proposto (v4c)

Quattro classi *distinte*, tutte con identificatori causali e proprietà:

1. **Forward batch:** calcolo e aggiornamento dello stato neuronale con
   riserva atomica della memoria prevista dal contratto esistente.
2. **BV transport:** pacchetto di ritorno della valutazione del ricevente;
   l'avvenuta consegna non equivale a servizio dell'attore.
3. **Actor ACK:** presa in carico una volta sola, dopo la consegna causale
   e all'interno dell'epoca dell'attore proprietario.
4. **Actor consume/apply:** applicazione autorizzata del credito all'attore;
   *distinta* dall'ACK e dalla mutazione dello stato/P del neurone nativo.

Le ultime due classi richiedono ciascuna un grant PE proprio e una
contabilizzazione autonoma della memoria (ricerca derivata: `1 PE + 2 unità
astratte`, domini O/E). La specifica finale dovrà fissare *quali PE*,
quale allocazione O/E e quali autorizzazioni P/S/E/O; la quantità derivata
non è ancora una misura fisica o una concessione di autorità a scrivere P/S.

La fase di servizio attore non può inventare un giudizio a partire da
assenza, overflow, perdita di trasporto, timeout o mancata ammissione.
ACK e applicazione devono avere ricevute separate, una catena causale
monotona, deduplicazione esatta e comportamento fail-closed contro replay,
errore del ricevente e cambio proprietario dell'attore.

### Interfaccia minima futura — da formalizzare

| Campo | Semantica richiesta |
|:--|:--|
| `source_emission` / `judgment_id` | Origine causale stabile e unica; non autenticazione crittografica |
| `receiver_id`, `actor_owner`, `actor_epoch` | Custodia, per-actor isolation e rifiuto di epoche obsolete |
| `due_tick`, `delivery_tick` | Rispettivamente ammissibilità temporale e consegna reale |
| `ack_seq`, `ack_grant_tick` | ACK esattamente una volta, FIFO sorgente verificabile |
| `consume_seq`, `consume_grant_tick` | Applicazione distinta, con proprio budget e autorizzazione |
| `owner_PE`, `global_PE`, `domain_O`, `domain_E` | Permessi atomici reali, mai shadow-only |
| `pending_rank`, `admitted_queue_bound` | Limite di backlog che condiziona la deadline |
| `window_W`, `reservation_receipt` | Prenotazione verificabile, non contatore di intenzioni |
| `outcome` | `COMMITTED`, `DEFERRED`, `POLICY_BLOCKED`, `HORIZON_INCOMPLETE`, `REJECTED` |

## 4. Due modalità versionate e non intercambiabili

### A. `NATIVE_COMPATIBLE` — baseline di migrazione

- Preserva la priorità e i risultati temporali dell'esecutore originale.
- Non preleva risorse riservate o preemptive per gli ACK.
- Può osservare/censurare/derivare ACK senza attribuirli allo stato nativo.
- `window_W = null`, grant minimo garantito `0`, deadline `null`.
- È l'unica modalità che può reclamare compatibilità temporale *senza*
  dimostrare una nuova capacità disgiunta.

### B. `RESERVED_ACK_WINDOW` — **opzione di progetto**, non adottata

- Richiede una nuova politica di prenotazione esplicita che garantisca
  **almeno un ACK per la testa FIFO ogni W tick** mentre la coda contiene
  un controllo dovuto, effettivamente ammesso e con credito valido.
- Il grant deve esistere contemporaneamente nel **budget PE globale e nel
  PE proprietario**, e deve avere memoria O/E disponibile e autorizzata.
  Una riserva solo nominale non soddisfa la premessa.
- Se forward occupa continuativamente le risorse, la policy deve decidere
  una preemption o una capacità aggiuntiva, con conseguente possibile
  differenza temporale nel calcolo forward.
- L'ammissione richiede una soglia massima **esplicita** di rango `Q` e una
  finestra `W` compatibile con il residuo d'orizzonte: quando le premesse
  sono effettivamente mantenute, la bound relativa è `rW−1`, con `r≤Q`.
- Esempio *puramente illustrativo*, da validare: `W=4`, `Q=16`, bound
  condizionale ≤63 tick. Non è il contratto scelto per i dispositivi SPK.
- Non può affermare parità temporale con il nativo storico. Neppure
  l'uguaglianza funzionale è universale: la computazione può dipendere dal
  timestamp; serviranno nuove verifiche semantiche.

**Il controllo statico di una bozza non è una prova di eseguibilità:** il
validatore verifica che la proposta non sia logicamente auto-contraddittoria,
ma non può attestare che un arbitro nativo futuro realizzerà le riserve.

## 5. Obblighi di prova prima di un'adozione nativa

1. **Nuova versione dell'architettura** e del contratto, con tag separati;
   nessun cambiamento retroattivo ad Architecture v1.
2. **Admission proof:** inventario delle PE per proprietario, O/E, backlog
   massimo e credito/epoca; rigetto se le risorse sono insufficienti.
3. **Source-causal custody:** delivery→ACK→consumer vincolata ad attore,
   ricevente e sorgente, esattamente una volta; spoof e replay fail-closed.
4. **Resource conservation:** ACK e consumer addebitati separatamente;
   impossibile superare capacità globali, per PE, per dominio e per tick.
5. **Policy arbitro:** dimostrare sul runtime *nuovo* che ogni finestra W
   ammessa contiene un grant utile alla testa FIFO, non soltanto un token.
6. **Bounded horizon:** dichiarare completamento solo se il tempo residuo
   consente i grant richiesti; in caso contrario incompleto senza prova
   di silenzio/negatività.
7. **Semantica forward:** in modalità compatibile output nativo identico;
   in modalità riservata nuova verifica funzionale e temporale esplicita.
8. **Null/fault matrix:** perdita, errore ricevente, assenza credito,
   saturazione, riserve mancanti, crash e replay non generano apprendimento.
9. **Separate promotion gate:** l'applicazione al neurone nativo richiede
   autorità P/S, modalità operativa, rollback e contratto di apprendimento
   autonomamente approvati. Il servizio dell'ACK da solo non li implica.
10. **Test indipendenti in checkout isolato**, completo frozen regression,
    SHA-manifest, riproducibilità e decisione di accettazione documentata.

La garanzia di servizio **del consumer** richiede a sua volta un contratto
separato: la deadline dell'ACK non equivale alla deadline dell'applicazione.

## 6. Esito della presente proposta

La ricerca v4a–v4c chiude il *diagnostico* dell'inadeguatezza del contratto
attuale per una deadline individuale. Fornisce alternative rigorose, una
prova condizionale e un validatore che rifiuta assunzioni implicite.

**Non è una milestone di adozione nativa**: `DRAFT`, nessun operatore, stato
neuronale, fairness universale o percentuale di release viene promosso.

### Riproduzione su `fwork`

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v4abc_Native_Actor_Service_Contract_Candidate.tar.gz

bash search/spk_bv_v4abc_native_actor_contract_candidate_gate.sh \
  /tmp/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4abc-native-contract-candidate.json

bash search/spk_bv_v4abc_inherited_regression_gate.sh
```

Nota per la regressione ereditata: il gate dipende dai report canonici
completi di tutte le fasi precedenti. Nello snapshot locale di ricerca il
file `spk-bv-v2o-native-causal-admission.json` misura 2.173.952 byte e
termina con un JSON incompleto: la suite v2p incontra due `JSONDecodeError`
prima di analizzare il contratto candidato. Non sanare la fixture alterando
la traccia: usare il report sorgente integro e verificarne la firma SHA.
Il gate locale v4a–v4c, indipendente da quel file, resta 14/14 PASS.

| Roadmap Simulator/Compiler | Avanzamento | Δ |
|:--|--:|--:|
| S1 | 100% | 0 pp |
| S2 | 100% | 0 pp |
| S3 | 60% | 0 pp |
| S4 | 0% | 0 pp |
| S5 | 0% | 0 pp |
| **Totale (media paritaria)** | **52%** | **0 pp** |
