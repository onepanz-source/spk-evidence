# SPK/* · BV v0y: contratto teorico per giudizio e proposta locale

## Stato epistemico

**Solo ricerca, non promuovere.** v0x ha ricomputato nativamente 45 esecuzioni (15 celle, 3 bracci) con preservazione degli esiti forward; non ha dimostrato né un giudizio né un beneficio di apprendimento. v0y non crea tali oggetti retroattivamente. Non modifica Core/Network/Compiler/Architecture v1, né il runtime v0e.

## Semantica proposta

Sia una decisione locale `d=(neuron, episode, state_hash, context_hash, admissible_ops, chosen_op, tick)`.

1. Un **criterio** `c=(objective,evaluator,direction,registered_tick)` deve essere dichiarato **prima** della decisione. L'identificativo dell'objective è una dichiarazione, non la sua misurazione.
2. Un **giudizio** `j=(decision_id, observer,receiver,criterion,sign,evidence,origin,produced,available)` è un'opinione nominale `sign∈{-1,0,+1}` del vicino. Non è una probabilità, un reward, una verità o una misura di qualità. Il campo `available` deve essere ≥ `produced` > `decision.tick`.
3. Una **proposta** `p=(target_decision, judgment_ids, proposed_operator,created,window,verdict)` è ammissibile solo se `proposed_operator ∈ admissible_ops`, tutti i giudizi sono riferiti alla stessa decisione, sono disponibili all'inizio della finestra, e `criterion.registered_tick < decision.tick < window.start ≤ created ≤ window.end`.
4. Il solo `verdict` ammesso in v0y è **`noop`**: questo modulo **non applica update**. Un futuro operatore U richiederà un contratto di commit separato con boundedness, rollback, esclusione di future leakage e osservazione degli effetti su episodi successivi.

In forma astratta: `Observe(d) -> Judgment(d)` (ipotetico; nessun produttore nativo qui); `Admissible(d,j,t)` verifica riferimenti e tempi; `Propose(d,{j},t) -> (candidate_op, noop)`.

## Due identificazioni da NON confondere

- `causal_origin_id` è un **raggruppamento dichiarato**. Diversi mittenti o pacchetti provenienti dallo stesso antenato non rappresentano automaticamente voti indipendenti. Il validatore rifiuta giudizi di segno opposto dalla stessa origine dichiarata e segnala i raggruppamenti duplicati, ma non certifica **l'effettiva** indipendenza causale.
- L'attestazione SHA dei costi v0x/v0w significa che il rapporto v0x coincide esattamente con il riassunto ricostruito da v0w, e che v0x riporta una ricomputazione nativa. Non costituisce prova della correttezza dell'opinione dell'osservatore.

## Esperimento successivo necessario (NON incluso)

Registrare ex ante un criterio esterno misurabile, una finestra train e una sequenza futura holdout. Acquisire giudizi causalmente riferiti a decisioni reali. Confrontare in episodi successivi lo stesso stato/input e budget tra un braccio noop e un braccio di aggiornamento limitato, tenendo conto dei costi del feedback, della correlazione fra osservatori e della complessità incrementale. Solo allora formulare un'ipotesi falsificabile di miglioramento neuronale.

## Artefatti ed esecuzione

Il pacchetto incrementale contiene `spk_bv_research/judgment_contract_v0y.py`, `search/spk_bv_v0y_judgment_contract.py`, `search/spk_bv_v0y_research_gate.sh`, `tests/test_spk_bv_v0y_judgment_contract.py` e questa specifica.

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v0y_Shadow_Judgment_Contract.tar.gz
bash search/spk_bv_v0y_research_gate.sh
python -m search.spk_bv_v0y_judgment_contract \
  --v0x /tmp/spk-bv-v0x-native-verified.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v0y-shadow-judgment-contract.json
```

Il ledger è **vuoto** se `--ledger` viene omesso: un risultato non può inventare giudizi nativi. `--ledger <path>` accetta record espliciti, ancora e sempre **shadow-only**, verificati in fail-closed. Non scrivere file dentro il checkout e non sovrascrivere gli output precedenti. Il gate eredita i regressori precedenti; la sua completa esecuzione deve essere verificata su fwork. I test locali sono una prova del solo nuovo schema e dei regressori presenti in laboratorio.
