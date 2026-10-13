# calendariParrocchia

Calendario dei gruppi parrocchiali con fogli A4 da distribuire.

Un programma desktop per Linux con cui chi coordina le attività della parrocchia tiene il
calendario dei gruppi (classi di catechismo, cresimandi, giovanissimi, coro, oratorio…) e ne
ricava **fogli A4 pronti da distribuire**: un foglio per gruppo, con i soli eventi di quel gruppo,
in ordine cronologico e colorati per categoria. In PDF da stampare o in PNG da mandare su WhatsApp.

Funziona senza Internet: i dati restano su questo computer.

La specifica completa è in [`docs/SPEC.md`](docs/SPEC.md) ed è la fonte di verità del progetto.

---

## Requisiti

- Linux con un desktop (provato su Ubuntu 26.04 con GNOME, Wayland).
- [`uv`](https://docs.astral.sh/uv/), che porta con sé Python 3.12 e le dipendenze Python.
- La libreria **Pango** (`libpango-1.0-0`), che compone il testo dei PDF. Su Ubuntu c'è già;
  altrimenti: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0`.
- **Google Chrome** o **Chromium** per la finestra del programma (senza, si apre una scheda del
  browser predefinito).
- Node.js e npm **solo** per costruire l'interfaccia dai sorgenti.

## Installazione

```sh
./install.sh      # per l'utente corrente, senza sudo; rilanciarlo aggiorna
./uninstall.sh    # toglie comando, voce di menu e icone; i dati restano salvo un «sì» esplicito
```

`install.sh` controlla i prerequisiti — `uv`, Python 3.12, Pango (con `ldconfig`, poi caricandolo
davvero attraverso WeasyPrint), il font Inter incluso nel pacchetto — e se manca qualcosa stampa il
comando esatto e si ferma: non installa mai pacchetti di sistema. Poi prepara l'ambiente Python con
`uv`, costruisce l'interfaccia (se c'è npm) e installa:

- il comando `~/.local/bin/calendariparrocchia`;
- le icone in `~/.local/share/icons/hicolor/{48x48,128x128,256x256,scalable}/apps/`;
- la voce di menu `~/.local/share/applications/calendariparrocchia.desktop`, il cui
  `StartupWMClass` è l'identità della finestra: è ciò che mette nella dock l'icona e il nome giusti.

### La finestra

Il programma si apre in una finestra propria, massimizzata, senza barra degli indirizzi né schede:
un browser della famiglia Chromium in modalità applicazione, con un profilo dedicato. Il browser
viene cercato in quest'ordine: `chromium`, `chromium-browser`, `google-chrome`,
`google-chrome-stable`, `brave-browser`, `microsoft-edge`, poi i rispettivi Flatpak; `--browser
PATH` o `CP_BROWSER` lo impongono. Senza nessuno di questi si apre una scheda del browser
predefinito e l'interfaccia spiega perché. Nessun browser viene mai installato. F11 = schermo
intero.

## Uso

```sh
calendariparrocchia                  # programma + finestra (è ciò che fa la voce di menu)
calendariparrocchia --no-window      # solo il server: sviluppo, SSH, script
```

Rilanciare il comando non apre una seconda istanza: chiede a quella in esecuzione di mostrare la
sua finestra ed esce. Chiudere la finestra chiude il programma; «Esci» nel menu «⋯» fa lo stesso
(un export in corso viene lasciato finire).

Il programma ha tre schede:

- **Calendario** — si apre sul mese corrente, con oggi evidenziato; viste Mese, Settimana ed
  Elenco; filtri per gruppi e categorie. Clic su un giorno per un nuovo evento, clic su un evento
  per modificarlo, trascinamento per spostarlo (con «Annulla» per 8 secondi). Un evento appartiene
  a uno o più gruppi e ha una o più categorie: la prima dà il colore. «Duplica…» copia un evento su
  più date (non ci sono eventi ricorrenti). Le **note** di un evento sono solo per te: non
  compaiono mai nei fogli esportati.
- **Gruppi e categorie** — creare, rinominare, ricolorare, riordinare (trascinando), archiviare i
  gruppi degli anni passati, eliminare (scegliendo cosa fare degli eventi che resterebbero senza
  gruppo o categoria).
- **Export** — periodo, modalità (un file per gruppo, PDF unico con una pagina per gruppo,
  calendario completo), formato (PDF e/o PNG a 150/200/300 dpi), gruppi e categorie, intestazione
  (nome della parrocchia e logo), cartella. A destra l'anteprima, che è lo stesso PDF che verrà
  salvato. Ogni foglio sta in una facciata A4: il testo si rimpicciolisce e, se serve, passa a due
  colonne; se nemmeno così ci sta, il programma lo dice e propone «Esporta su più pagine».

Gli export vanno in una sottocartella nuova, `Export AAAA-MM-GG HH-MM`, dentro la cartella scelta
(di default `~/Documenti/Calendari parrocchia/`): **nessun file esistente viene mai sovrascritto**.

## I tuoi dati e i backup

Tutto — eventi, gruppi, categorie, impostazioni, nome della parrocchia e logo — sta in un solo
database SQLite:

| Cosa | Dove |
|---|---|
| Database | `~/.local/share/calendariparrocchia/catalog.db` |
| Backup automatici | `~/.local/share/calendariparrocchia/backups/auto-AAAA-MM-GG.db` |
| Log (3 file da 1 MB al massimo) | `~/.local/state/calendariparrocchia/logs/` |

Dal menu «⋯»:

- **Backup ora** — una copia completa del database (fatta con `VACUUM INTO`, coerente anche a
  programma aperto) nella cartella che scegli, di default `~/Documenti`, col nome
  `calendariParrocchia backup AAAA-MM-GG.db`. Se il nome è già preso il backup diventa
  `… (2).db`: nessun file viene sostituito. Per spostare i dati su un altro computer basta questo
  file.
- **Backup automatico** — all'avvio, se l'ultimo ha più di 24 ore. Si tengono gli ultimi **14**;
  gli altri file della cartella non vengono toccati.
- **Ripristina da backup…** — il selettore si apre sulla cartella dei backup automatici e mostra
  anche i file `.db` (si può andare ovunque nella cartella personale). Il programma legge il file
  scelto e mostra quanti eventi, gruppi e categorie contiene prima di chiedere conferma. Rifiuta un
  file che non è un backup di calendariParrocchia, uno danneggiato e uno fatto da una versione più
  recente del programma; uno fatto da una versione più vecchia viene aggiornato. Il database di
  prima non viene cancellato: resta nella cartella dei dati come
  `catalog-prima-del-ripristino-AAAA-MM-GG-HHMMSS.db`. Il file scelto non viene mai modificato.
- **Apri cartella dei backup** — la apre nel file manager.

`./uninstall.sh` non tocca né il database né i backup senza un «sì» scritto nel terminale.

## Riservatezza

Il programma non fa **nessuna** chiamata di rete: niente telemetria, aggiornamenti, font o immagini
remoti. Il server ascolta solo su `127.0.0.1:8746` e rifiuta le richieste delle altre pagine del
browser. Il motore dei PDF può leggere solo i propri font e immagini incorporate: un logo SVG che
punta a indirizzi esterni o a file del sistema viene composto senza quelle risorse. Il programma
scrive solo nelle proprie cartelle e nelle cartelle che scegli tu, sempre dentro la cartella
personale.

## Sviluppo

Servono `uv` e, per l'interfaccia, Node.js.

```sh
uv sync                                   # dipendenze, incluse quelle di sviluppo
uv run python packaging/make_icons.py     # icone segnaposto (già fatto dallo scaffold)
uv run pytest -q                          # test (~45 s: gli export compongono PDF veri)
uv run ruff check . && uv run ruff format --check .
cd frontend && npm run typecheck          # controllo dei tipi dell'interfaccia

# interfaccia: server senza finestra su una porta fissa, Vite con il ricaricamento a caldo
CP_PORT=8746 uv run calendariparrocchia --no-window
# API esplorabili su http://127.0.0.1:8746/docs (solo con CP_DEV=1: Swagger UI carica il suo
# script da una CDN, quindi nell'uso normale la pagina non esiste)
CP_DEV=1 CP_PORT=8746 uv run calendariparrocchia --no-window
cd frontend && npm install && npm run dev  # http://localhost:5173
npm run build                              # scrive in backend/cp/static/
```

I test di prestazione (test 27, i budget di SPEC §14: avvio, memoria, query del mese con 10 000
eventi, anteprima, export) sono esclusi dalla suite rapida; si lanciano a parte, a macchina
ferma, e stampano ogni misura accanto al suo obiettivo:

```sh
uv run pytest -m bench tests/bench        # ~30 s
```

Fogli di prova dell'export (database temporaneo con dati sintetici: 10, 30 e 80 eventi su un
foglio ciascuno, più il calendario completo; la cartella deve stare sotto la home):

```sh
uv run python -m cp.export.samples out/prova          # solo PDF
uv run python -m cp.export.samples out/prova --png    # anche PNG a 200 dpi
```

## Struttura

```
backend/cp/
  __main__.py        riga di comando
  runtime.py         avvio e chiusura: lock, server, finestra, segnali, backup automatico
  config.py          impostazioni e cartelle XDG
  server.py          server HTTP locale (solo 127.0.0.1), API di base, router del progetto
  security.py        chi può parlare col server (Host/Origin)
  window.py          la finestra dell'applicazione
  single_instance.py un solo programma alla volta
  backup.py          backup manuale e automatico, ripristino
  db/                SQLite: modelli, sessioni brevi, migrazioni Alembic, il lock che il
                     ripristino prende per sostituire il file
  domain/            regole: eventi, gruppi e categorie, validazione, colori, impostazioni,
                     intestazione della parrocchia (nome e logo)
  export/            motore di export: selezione degli eventi per foglio, formattazione in
                     italiano, modelli HTML/CSS, adattamento all'A4, PDF (WeasyPrint), PNG
                     (pypdfium2), nomi dei file, job in background, anteprima in memoria;
                     assets/fonts/ contiene il font Inter (licenza OFL accanto)
  folders.py         selettore di cartelle (e dei file .db da ripristinare), sempre nella home
  api/               route HTTP (/api/groups, /api/categories, /api/events, /api/places,
                     /api/settings, /api/parish, /api/folders, /api/export, /api/backup,
                     /api/restore) e formato uniforme degli errori
  static/            l'interfaccia servita dal server (costruita da frontend/)
frontend/src/
  pages/             le tre schede
  components/        dialoghi, selettori, anteprima, menu «⋯»
  lib/               client delle API, date senza fuso orario, stato dei moduli
  i18n/              tutte le stringhe dell'interfaccia, in italiano
packaging/           icone e loro generatore
tests/               test (pytest); tests/bench/ i test di prestazione
docs/SPEC.md         la specifica
```

## Dipendenze

Quelle elencate nella SPEC (§4) più:

- `httpx2` (solo sviluppo): richiesto dal `TestClient` di FastAPI/Starlette per i test delle API
  senza avviare un server vero.
- `vite-plugin-pwa` (solo per costruire l'interfaccia, dallo scaffold): genera il service worker
  che tiene in cache i file dell'interfaccia.

Il font Inter 4.1 (`backend/cp/export/assets/fonts/`, solo Regular, SemiBold e Bold) è
distribuito con la SIL Open Font License 1.1, il cui testo è in `OFL.txt` nella stessa cartella.

## Licenza

GPL-3.0-or-later. Vedi [`LICENSE`](LICENSE).
