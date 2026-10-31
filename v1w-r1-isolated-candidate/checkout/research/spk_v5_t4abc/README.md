# SPK V5 T4ABC | Causal-origin dossier (research-only)

Checkpoint additivo per `~/workspace/spk-backvalidation-v0`.

Scopo: con la traccia T3XYZ recuperata ed il report originale, identificare
**dove** si collocano i passaggi Python fra `_compute_local`, il bridge
BV-v0e e la logica di credito C. Non produrre, sintetizzare, né attribuire
un verdetto semantico nativo.

Gate cumulativi:

- T4A: verifica SHA dei report T3XYZ e dei tre sorgenti congelati usati.
- T4B: analisi AST (solo sintattica) dei 2-5 moduli con nomi ammessi;
  conservazione SHA, linee, firme nominali e chiamate rilevate.
- T4C: censimento streaming dei 64.615 eventi di chiamata Python;
  associazione del percorso di origine senza dichiarare completa una
  cattura saturata. Costruzione di piccolo archivio sorgente dedicato
  a un successivo intervento puntuale.

Comando:

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_V5_T4ABC_Causal_Origin_Dossier_Milestone_20261022.tar.gz

bash search/spk_v5_t4abc_causal_origin_gate.sh \
  /tmp/spk-v5-t4abc-causal-origin.json \
  /tmp/spk-v5-t3xyz-trace-recovery.json \
  "$HOME/workspace/spk-evidence/spk-v5-t3xyz-20261021/spk-v5-t3xyz-passive-observation-profile.jsonl" \
  "$HOME/workspace/spk-evidence/spk-v5-t4abc-source-bundle.tar.gz"
```

Per l'analisi del successivo checkpoint usare il JSON e, se appropriato,
l'archivio sorgenti generato dal gate. L'archivio contiene *solo* file `.py`
selezionati per nome e non contiene dotfiles, dataset o file di configurazione.
Si consiglia comunque di ispezionarlo prima di condividerlo.

I contatori dei moduli possono sovrapporsi. Una chiamata `_compute_local`
può figurare contemporaneamente nelle categorie C/bridge/BV-v0e.

Limitazioni: AST non prova la dinamica; sys.setprofile non registra eventi
neuromorfici nativi; la traccia T3XYZ ha due processi saturati; nessuna
attestazione indipendente dei sensori e nessuna inferenza blind. Il prodotto
non autorizza la promozione di Architecture o policy.

Se l'output esiste già il gate si ferma anziché sovrascrivere dati precedenti.
Fornire percorsi nuovi per una seconda esecuzione.
