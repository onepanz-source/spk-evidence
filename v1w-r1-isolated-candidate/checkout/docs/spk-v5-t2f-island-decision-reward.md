# SPK/* V5-T2f — Isola logica: decision custody & reward transport (ricerca)

**Stato:** gate software di ricerca; NON certificazione di apprendimento, semantica indipendente, né transport nativo. **Data:** 21 ottobre 2026.

## Questione affrontata

Il gate T2e contabilizza, nel sorgente immutato BV v0e, feedback retrogrado soltanto in presenza di uno spike con antenato causale. La decisione A di **non emettere** non dispone di tale antenato. Per un obiettivo d'isola che penalizza l'omissione, il solo ACK di spike è insufficiente.

La soluzione *sperimentata* è un **record esplicito di decisione** valido sia per emissione sia per silenzio. Il record è creato da un **host di ricerca separato**, NON da un'istruzione nativa di A: non si sostituisce furtivamente uno spike assente con uno spike gratuito. Il record è verificato mediante **riesecuzione reale del motore A1b congelato**, usando inizialmente un prefisso senza sensore futuro. Il token è identico per `C_demand=True`, `False` e `None`; C osserva successivamente il proprio sensore e il proprio evento di chiusura.

**Vincolo metodologico:** tutto avviene come *replay offline*, non come erogazione online dell'host al tick nominale. I tick codificano ordine causale proposto; non costituiscono prova di consegna sul runtime congelato. La ricompensa è una conseguenza osservata da C nella simulazione, non un'etichetta esterna affidabile.

## Contratto tipizzato, separato da BV v0e

| Fase | Offset dal primo input | Proprietario | Risorsa astratta addizionale |
|---|---:|---|---|
| Commit della decisione, anche silenziosa | +2 | host research/A | 1 PE, 1 memoria |
| A→B, propagazione del record | +3 | shadow A→B | 1 PE, 2 memoria, 1 link |
| B→C, inoltro record | +4 | shadow B→C | 1 PE, 2 memoria, 1 link |
| C osserva domanda e chiusura | +6 | shadow C | 1 PE, 2 memoria |
| C→B, valutazione (±1 o astensione) | +7 | shadow C→B | 1 PE, 2 memoria, 1 link |
| B→A, ritorno | +8 | shadow B→A | 1 PE, 2 memoria, 1 link |
| A consuma il riscontro | +9 | shadow A | 1 PE, 1 memoria |

La route completa costa **7 PE, 12 unità di memoria, 4 link**, in più rispetto all'esecuzione A1b. Le quote sono esplicite, con controllo di tipo, capacità totale e per tick; non vengono dichiarate prenotazioni riuscite nel vero scheduler BV v0e. La perdita durante il trasporto contabilizza soltanto le fasi **effettivamente tentate**, e **non genera credito negativo né certificati di assenza**. Non esiste spesa energetica fisica misurata.

## Controesempi verificati

1. Scelta silenziosa con domanda C=true: può produrre -1 con chiusura, registro di decisione e percorso *shadow* completo.
2. Scelta silenziosa con domanda C=false: può produrre +1.
3. Domanda sconosciuta: `abstain`, senza fabbricare un giudizio.
4. Perdita A→B, B→C, C→B, B→A: niente reward consegnato; conservazione dei costi già sostenuti.
5. Budget PE/memoria/link insufficiente: **reiezione**, mai premio senza risorse.
6. Token/identità/tick/arm/episodio/ricompensa/ledger contraffatti: replay dal sorgente differisce o duplicato di episodio respinto.
7. Nessuna ricompensa da un record di solo hash o da un impulso C osservato senza registrazione/chiusura.

## Matrice deterministica

21 episodi autonomi: sette template × tre osservazioni C (`False`, `True`, `None`), uno dei tre programmi assegnato per episodio. Tre scenari per lo stesso schedule: transport completo, perdita prima di C, perdita nel ritorno. **63 prove source-executed**; NON 63 episodi di addestramento statistico indipendenti. I costi delle route sono indipendenti dai costi retrogradi realmente misurati nel precedente T2e: non si sommano come se fossero già arbitrati insieme.

## Cosa rimane BLOCCATO

- Il *decisore nativo* non emette ancora il record esplicito di silenzio: oggi lo emette l'host esterno. Nessuna prova di autorità o identità crittografica indipendente.
- Il feedback semantico e i costi associati **non sono integrati nel scheduler BV v0e**. Non abbiamo misurato la contesa con gli spike nativi, né garantito deadline reali o fairness.
- La domanda di C resta generata da noi. Una sua osservazione manipolata può produrre un reward semanticamente falso pur con trasporto perfetto; resta valida la criticità T2d.
- Un test su dati terzi blind, criteri statistici preregistrati e un vero esperimento T3 A/B/C sono ancora **NO-GO**. Zero update a programmi o memoria native.

**Decisione di gate proposta:** **T2f shadow feasibility PASS** se la matrice e gli invarianti sono riproducibili; **native semantic reward route BLOCKED**. Il prossimo lavoro dovrebbe controllare su sorgente la contesa delle nuove classi di controllo e definire chi sia autorizzato a registrare decisioni silenziose, prima di scrivere un algoritmo di apprendimento.
