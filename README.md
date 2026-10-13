# calendariParrocchia

Calendario dei gruppi parrocchiali con fogli A4 da distribuire

La specifica completa è in [`docs/SPEC.md`](docs/SPEC.md) ed è la fonte di verità del progetto.

---

## Installazione

```sh
./install.sh      # per l'utente corrente, senza sudo; rilanciarlo aggiorna
./uninstall.sh    # toglie comando, voce di menu e icone; i dati restano salvo un «sì» esplicito
```

`install.sh` controlla i prerequisiti (se manca qualcosa stampa il comando esatto e si ferma: non
installa mai pacchetti di sistema), prepara l'ambiente Python con `uv`, poi installa:

- il comando `~/.local/bin/calendariparrocchia`;
- le icone in `~/.local/share/icons/hicolor/{48x48,128x128,256x256,scalable}/apps/`;
- la voce di menu `~/.local/share/applications/calendariparrocchia.desktop`, il cui `StartupWMClass` è
  l'identità della finestra: è ciò che mette nella dock l'icona e il nome giusti.

### La finestra

Il programma si apre in una finestra propria, senza barra degli indirizzi né schede: un browser
della famiglia Chromium in modalità applicazione, con un profilo dedicato. Il browser viene
cercato in quest'ordine: `chromium`, `chromium-browser`, `google-chrome`, `google-chrome-stable`,
`brave-browser`, `microsoft-edge`, poi i rispettivi Flatpak; `--browser PATH` o
`CP_BROWSER` lo impongono. Senza nessuno di questi si apre una scheda del browser
predefinito e l'interfaccia spiega perché. Nessun browser viene mai installato.

I dati stanno in `~/.local/share/calendariparrocchia/`, i log in `~/.local/state/calendariparrocchia/logs/`.

## Uso

```sh
calendariparrocchia                  # programma + finestra (è ciò che fa la voce di menu)
calendariparrocchia --no-window      # solo il server: sviluppo, SSH, script
```

Rilanciare il comando non apre una seconda istanza: chiede a quella in esecuzione di mostrare la
sua finestra ed esce.
Chiudere la finestra chiude il programma; «Esci» nell'interfaccia fa lo stesso.

## Sviluppo

Serve [`uv`](https://docs.astral.sh/uv/).

```sh
uv sync                                   # dipendenze, incluse quelle di sviluppo
uv run python packaging/make_icons.py     # icone segnaposto (già fatto dallo scaffold)
uv run pytest -q                          # test
uv run ruff check . && uv run ruff format --check .

# interfaccia: server senza finestra su una porta fissa, Vite con il ricaricamento a caldo
CP_PORT=8746 uv run calendariparrocchia --no-window
# API esplorabili su http://127.0.0.1:8746/docs (solo con CP_DEV=1: Swagger UI carica il suo
# script da una CDN, quindi nell'uso normale la pagina non esiste)
CP_DEV=1 CP_PORT=8746 uv run calendariparrocchia --no-window
cd frontend && npm install && npm run dev  # http://localhost:5173
npm run build                              # scrive in backend/cp/static/
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
  runtime.py         avvio e chiusura: lock, server, finestra, segnali
  config.py          impostazioni e cartelle XDG
  server.py          server HTTP locale (solo 127.0.0.1), API di base, router del progetto
  security.py        chi può parlare col server (Host/Origin)
  window.py          la finestra dell'applicazione
  single_instance.py un solo programma alla volta
  db/                SQLite: modelli, sessioni brevi, migrazioni Alembic
  domain/            regole: eventi, gruppi e categorie, validazione, colori, impostazioni,
                     intestazione della parrocchia (nome e logo)
  export/            motore di export: selezione degli eventi per foglio, formattazione in
                     italiano, modelli HTML/CSS, adattamento all'A4, PDF (WeasyPrint), PNG
                     (pypdfium2), nomi dei file, job in background, anteprima in memoria;
                     assets/fonts/ contiene il font Inter (licenza OFL accanto)
  folders.py         selettore di cartelle, sempre dentro la home
  api/               route HTTP (/api/groups, /api/categories, /api/events, /api/places,
                     /api/settings, /api/parish, /api/folders, /api/export) e formato
                     uniforme degli errori
  static/            l'interfaccia servita dal server
frontend/            sorgenti React + TypeScript + Vite
packaging/           icone e loro generatore
tests/               test (pytest)
docs/SPEC.md         la specifica
```

## Dipendenze

Quelle elencate nella SPEC (§4) più:

- `httpx2` (solo sviluppo): richiesto dal `TestClient` di FastAPI/Starlette per i test delle API
  senza avviare un server vero.

Il font Inter 4.1 (`backend/cp/export/assets/fonts/`, solo Regular, SemiBold e Bold) è
distribuito con la SIL Open Font License 1.1, il cui testo è in `OFL.txt` nella stessa cartella.

## Licenza

GPL-3.0-or-later. Vedi [`LICENSE`](LICENSE).
