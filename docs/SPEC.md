# calendariParrocchia — Specifica di implementazione

> **Destinatario:** agente di coding (Claude Code) che implementa il progetto.
> **Lingua del codice/commenti:** inglese. **Lingua della UI e dei messaggi:** italiano.
> Questo documento è la fonte di verità. Se una scelta implementativa lo contraddice, vince
> questo file; se è ambiguo su un dettaglio, chiedi prima di inventare.

---

## 1. Obiettivo

calendariParrocchia è un programma desktop per Linux con cui **una sola persona** (chi coordina
le attività della parrocchia) tiene il calendario delle attività dei gruppi parrocchiali
(classi di catechismo, cresimandi, giovanissimi, coro, oratorio…) e ne ricava **fogli A4
pronti da distribuire**: un foglio per gruppo, con soltanto gli eventi che interessano a quel
gruppo, in ordine cronologico, colorati per categoria.

Il programma si apre su un **calendario che riempie la finestra, posizionato sul mese
corrente con la data di oggi evidenziata**. Qui si inseriscono gli eventi. Ogni evento
appartiene a **uno o più gruppi** ed è etichettato da **una o più categorie** (Catechesi,
Messa, Ritiro, Festa…). Ogni categoria ha un colore. Gruppi e categorie si gestiscono in una
scheda separata. Una terza scheda produce gli export in PDF o PNG.

Ordini di grandezza da cui partire: 5–25 gruppi, 5–15 categorie, 200–800 eventi per anno
pastorale, uso pluriennale (fino a ~10 000 eventi nel database). Un export tipico copre un
anno pastorale (settembre–giugno) per 10–15 gruppi con 15–60 eventi ciascuno.

### Non-obiettivi (v1)

- **Eventi ricorrenti** (regole «ogni sabato»): si usa **Duplica** su più date (§7.4).
  Decisione presa nell'intervista: la semplicità del modello vale più del tempo risparmiato.
- Più utenti, sincronizzazione, server condiviso, account: un solo utente su questo PC.
- Import/export iCalendar (.ics), Google Calendar, CalDAV.
- Promemoria e notifiche.
- Stampa diretta dal programma: si stampa il PDF prodotto.
- Layout di export diversi dall'elenco per mese (niente griglia mensile).
- Lingue diverse dall'italiano; uso da smartphone.
- Dati di esempio precaricati: **al primo avvio la base è vuota** (decisione dell'utente).

## 2. Invarianti assoluti

### 2.1 Nessuna rete, dati solo in locale

- **Il programma non fa alcuna chiamata di rete**: niente telemetria, controllo aggiornamenti,
  font o immagini remoti, CDN. Il frontend è servito interamente dal pacchetto.
- Il motore di export (WeasyPrint) usa un **`url_fetcher` personalizzato** che consente solo
  `data:` e i file dentro le cartelle risorse del pacchetto (`backend/cp/export/assets/`);
  qualsiasi altro schema (`http`, `https`, `ftp`, `file` fuori da quelle cartelle) solleva
  un errore registrato a livello WARNING e la risorsa viene saltata. Vale anche per un logo
  SVG che contenga riferimenti esterni.
- Test dedicato (test 19): durante un export completo `socket.socket.connect` è sostituito da
  una funzione che fa fallire il test.

### 2.2 Gli export non sovrascrivono mai nulla

- Ogni export scrive in una **sottocartella nuova** (`Export AAAA-MM-GG HH-MM`) dentro la
  cartella scelta. Se il nome esiste già, si aggiunge ` (2)`, ` (3)`…; lo stesso vale per i
  singoli file.
- Una sola funzione, `export/output.py::reserve_path(dir, name) -> Path`, decide i nomi e
  apre i file con `open(path, "xb")`: un file esistente non può essere sovrascritto nemmeno
  in caso di race. Test 18.
- Il programma scrive **solo** nella cartella di export scelta e nelle proprie cartelle XDG
  (`config.py`). Il percorso di export è risolto (`Path.resolve()`) e deve stare sotto `$HOME`
  (§10.3).

## 3. Vincoli di ambiente (macchina target, verificata il 2026-10-13)

| Voce | Valore |
|---|---|
| OS | Ubuntu 26.04.1 LTS (kernel 7.0.0-38-generic) |
| Sessione grafica | wayland / ubuntu:GNOME |
| CPU | 13th Gen Intel Core i5-13500H — 16 thread logici |
| RAM | 14.8 GB totali, ~6.0 GB disponibili |
| GPU | Intel Raptor Lake-P Iris Xe (integrata) |
| Spazio libero in $HOME | 49 GB |
| Python di sistema | 3.14.4; uv gestisce cpython 3.12.13, 3.14.x |
| uv | 0.11.18 |
| Node / npm | v24.21.0 / 11.19.0 |
| Browser | google-chrome, google-chrome-stable, firefox |
| GTK + WebKit | sì (Gtk 3 + WebKit2GTK 4.1) |
| Pango (per WeasyPrint) | libpango-1.0-0 1.57.0 |
| Font di sistema | Inter, Cantarell, DejaVu |

**Conseguenze vincolanti:**

- C'è Google Chrome: il percorso normale è la **finestra dedicata** Chromium `--app`, non la
  scheda del browser.
- Pango ≥ 1.44 è presente: WeasyPrint funziona senza pacchetti di sistema aggiuntivi;
  `install.sh` verifica comunque `libpango-1.0-0` e, se manca, stampa il comando `apt` e si
  ferma.
- **Il font Inter è incluso nel pacchetto** (`export/assets/fonts/`, licenza OFL nel
  repository) e usato dagli export via `@font-face`: i PDF vengono identici anche su una
  macchina senza Inter installato.
- Nessun lavoro pesante: niente processi worker, niente GPU.

## 4. Stack tecnologico (vincolante)

Variante dello scaffold: **completa** — server fastapi, finestra chromium, interfaccia react,
istanza singola. Il calendario interattivo (tre viste, dialoghi di modifica, selezioni
multiple di gruppi e categorie, anteprima dell'export con impaginazione automatica) su tre
schede è un'interfaccia ricca: React la regge senza riscritture future. Il backend ha logica
vera (database, generazione PDF/PNG, file su disco).

### Backend

- **Python 3.12**, ambiente con **`uv`** (`pyproject.toml`, niente `requirements.txt`).
- **FastAPI + uvicorn** (dallo scaffold): API tipizzate con Pydantic, documentazione su
  `/docs` in sviluppo.
- **SQLAlchemy 2.x** + **Alembic**: database SQLite (§10).
- **WeasyPrint ≥ 63** (BSD-3): HTML/CSS → PDF. Scelto perché permette di **misurare** quante
  pagine produce un documento, cosa che serve all'adattamento automatico all'A4 (§8.4).
- **Jinja2** (BSD-3): modelli HTML degli export.
- **pypdfium2** (Apache-2.0/BSD-3): rasterizzazione del PDF in PNG, conteggio pagine nei test.
- **Pillow** (HPND): normalizzazione del logo e scrittura dei PNG (passa da dev a runtime).
- **python-multipart**: caricamento del logo.
- **pytest**, **ruff**.

### Frontend

- React 18 + TypeScript + Vite + Tailwind 4 + TanStack Query + react-router (dallo scaffold).
- **FullCalendar 6** con i soli plugin MIT: `@fullcalendar/react`, `core`, `daygrid`,
  `timegrid`, `list`, `interaction`, locale `it`. **Nessun plugin premium.**
- **Nessuna stringa visibile nei componenti**: tutte in `frontend/src/i18n/it.ts`, via
  `t('chiave')`.

### Dipendenze

- Ogni dipendenza oltre a quelle elencate qui va motivata nel README.
- Dipendenze di sistema: `libpango-1.0-0` (verificata da `install.sh`), Google Chrome o
  Chromium per la finestra (già gestito dallo scaffold).

### Decisioni prese (non riaprirle)

1. **Eventi solo singoli**, niente ricorrenze; «Duplica» su più date.
2. **Export = elenco cronologico raggruppato per mese**, non griglia.
3. **Periodo dell'export libero** (dal… al…) con scorciatoie (§9.1).
4. **Una facciata A4 per gruppo**, con adattamento automatico (rimpicciolimento del testo,
   poi due colonne); solo il «calendario completo» può andare su più pagine.
5. **Tre modalità di export**: un file per gruppo; PDF unico con una pagina per gruppo;
   calendario completo con gli eventi di tutti i gruppi selezionati (§8.1).
6. **Intestazione**: nome della parrocchia e logo facoltativo, impostati una volta.
7. **Eventi «tutto il giorno» e su più giorni** ammessi.
8. **Un solo utente su questo PC**, nessuna rete.
9. **Vista iniziale: mese corrente**, con passaggio a settimana ed elenco.
10. **Base vuota al primo avvio**, nessun dato di esempio.
11. **Date e ore senza fuso orario**: si salvano data e ora «da orologio a muro»
    (`AAAA-MM-GG`, `HH:MM`). Il cambio dell'ora legale non sposta nulla.
12. **Settimana da lunedì, orari a 24 ore**, nomi di giorni e mesi in italiano da una tabella
    del programma (non dal `locale` di sistema, che potrebbe mancare).

## 5. Architettura

```
calendariParrocchia/
├── backend/cp/
│   ├── __main__.py            # CLI: nudo = apri il programma (scaffold)
│   ├── runtime.py             # avvio/chiusura, server + finestra (scaffold)
│   ├── config.py              # cartelle XDG (scaffold)
│   ├── server.py              # app FastAPI; include i router qui sotto
│   ├── security.py, controls.py, single_instance.py, window.py   # scaffold
│   ├── db/
│   │   ├── session.py         # engine, pragma, session_scope()
│   │   ├── models.py          # Group, Category, Event, tabelle ponte, Setting, Asset
│   │   └── migrations/        # Alembic
│   ├── domain/
│   │   ├── schemas.py         # modelli Pydantic dell'API (EventIn, EventOut, …)
│   │   ├── validation.py      # regole di §7.2
│   │   ├── events.py          # CRUD, query per intervallo, duplica, ordinamento
│   │   ├── taxonomy.py        # gruppi e categorie, eliminazione con orfani, archivio
│   │   └── palette.py         # palette predefinita, assegnazione, contrasto
│   ├── export/
│   │   ├── selection.py       # ExportRequest → righe ordinate per foglio (contratto §5.1)
│   │   ├── formatting.py      # date/ore/periodi in italiano
│   │   ├── render.py          # HTML → PDF (WeasyPrint), url_fetcher sicuro
│   │   ├── autofit.py         # scelta di corpo e colonne per stare in un A4
│   │   ├── raster.py          # PDF → PNG (pypdfium2)
│   │   ├── output.py          # nomi file, sottocartella, reserve_path (§2.2)
│   │   ├── jobs.py            # export in un thread, stato interrogabile
│   │   ├── templates/         # sheet.html.j2, combined.html.j2, sheet.css
│   │   └── assets/fonts/      # Inter (OFL) + OFL.txt
│   ├── api/
│   │   ├── routes_taxonomy.py # /api/groups, /api/categories
│   │   ├── routes_events.py   # /api/events, /api/places
│   │   ├── routes_parish.py   # /api/parish (nome, logo)
│   │   ├── routes_export.py   # /api/export/*
│   │   ├── routes_folders.py  # /api/folders (selettore cartelle)
│   │   ├── routes_settings.py # /api/settings
│   │   └── routes_backup.py   # /api/backup, /api/restore
│   └── backup.py              # VACUUM INTO, backup automatico, ripristino
├── frontend/src/
│   ├── pages/Calendar.tsx, Taxonomy.tsx, Export.tsx
│   ├── components/            # EventDialog, DuplicateDialog, ChipSelect, ColorPicker,
│   │                          # FolderBrowser, ExportPreview, AppMenu, …
│   ├── lib/api.ts, dates.ts   # client API, utilità date
│   └── i18n/it.ts
├── tests/
└── docs/SPEC.md
```

Ogni modulo resta sotto ~400 righe (§18).

### 5.1 Principio architetturale non negoziabile

**Una sola selezione, un solo renderer.** L'anteprima, il conteggio degli eventi mostrato
nella scheda Export e l'export vero passano tutti da:

1. `export/selection.py::build_sheets(request: ExportRequest) -> list[Sheet]`: decide quali
   eventi vanno in quale foglio, in che ordine, con quali colori e quali etichette;
2. `export/render.py` + `autofit.py`: producono il PDF di ogni `Sheet`;
3. l'anteprima è **lo stesso PDF** rasterizzato a bassa risoluzione.

Nessun'altra parte del codice filtra o ordina eventi per l'export. Le **note interne** (§7.1)
non entrano nei `Sheet`: il renderer non può mostrarle nemmeno per sbaglio (test 12). Così ciò che si vede
nell'anteprima è esattamente ciò che si salva.

L'ordinamento cronologico degli eventi è definito **una volta sola**, in
`domain/events.py::chronological_key` (§7.3), e usato sia dall'API del calendario sia
dall'export.

## 6. Gruppi e categorie

### 6.1 Modello

| Campo | Gruppo | Categoria | Regole |
|---|---|---|---|
| `id` | ✓ | ✓ | intero |
| `name` | ✓ | ✓ | 1–60 caratteri dopo `strip()`; spazi interni multipli ridotti a uno; **unico senza distinzione di maiuscole** (`casefold`) tra gli elementi dello stesso tipo, archiviati compresi |
| `color` | — | ✓ | `#RRGGBB` (6 cifre esadecimali, salvato in maiuscolo) |
| `position` | ✓ | ✓ | ordine scelto dall'utente; decide l'ordine in tutte le liste e nella legenda |
| `archived` | ✓ | ✓ | booleano, default falso |

I gruppi non hanno colore: il colore appartiene alle categorie.

### 6.2 Colori delle categorie

- Palette predefinita di 12 colori distinguibili e stampabili, assegnati in ordine al primo
  colore **non ancora usato** da una categoria (archiviate comprese); se sono tutti usati si
  riparte dal primo:
  `#E63946` rosso · `#F4A261` arancio · `#E9C46A` ocra · `#43AA8B` verde · `#2A9D8F` verde
  acqua · `#00A6ED` azzurro · `#277DA1` blu · `#577590` ardesia · `#9B5DE5` viola ·
  `#F15BB5` rosa · `#8D6E63` marrone · `#6C757D` grigio.
- L'utente può scegliere un colore della palette o uno libero (selettore colore).
- Dove il colore colora **testo** su bianco (il numero del giorno negli export, §8.3), si usa
  `palette.text_color(hex)`: lo stesso tono scurito in passi di 5% di luminosità finché il
  contrasto WCAG con il bianco è ≥ 4.5:1. Le barre colorate usano il colore originale. Test 21.

### 6.3 Operazioni

- **Crea, rinomina, ricolora, riordina** (trascinamento nella lista; `POST …/reorder` con la
  lista completa degli id).
- **Archivia / ripristina**: un elemento archiviato non compare nelle scelte per i nuovi
  eventi né nella scheda Export (salvo l'interruttore «Mostra archiviati»), ma gli eventi già
  collegati lo mantengono e lo mostrano. Serve per i gruppi degli anni passati.
- **Elimina**, con gestione degli eventi che resterebbero senza gruppo/categoria («orfani»):
  - nessun orfano: conferma semplice che dice quanti eventi perdono il collegamento;
  - con orfani: il dialogo mostra «N eventi hanno solo questo gruppo» e chiede di scegliere
    tra **«Spostali in…»** (un altro gruppo/categoria) e **«Elimina anche questi N eventi»**;
    senza scelta non si elimina. L'API lo impone: `DELETE` con orfani e senza
    `orphans=reassign&to=<id>` o `orphans=delete` risponde **409** con il conteggio.
  - Tutto in una sola transazione. Test 9–10.
- Il conteggio degli eventi collegati è mostrato accanto a ogni elemento.

## 7. Eventi

### 7.1 Modello

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| `title` | testo 1–120 | sì | dopo `strip()` |
| `start_date` | data | sì | |
| `end_date` | data | no | solo per eventi su più giorni; se presente `> start_date` (uguale = normalizzato a nullo) |
| `all_day` | booleano | sì | default falso |
| `start_time` | `HH:MM` | sì se non `all_day` | nullo se `all_day` |
| `end_time` | `HH:MM` | no | nullo se `all_day` |
| `place` | testo 0–120 | no | vuoto = non mostrato |
| `notes` | testo 0–2000, anche su più righe | no | **note interne**: si vedono solo nel programma (dialogo e passaggio del mouse), **mai negli export**; tolti solo gli spazi agli estremi. Decisione dell'utente del 2026-10-13 |
| `groups` | lista di id | **≥ 1** | ordine irrilevante |
| `categories` | lista ordinata di id | **≥ 1** | **la prima è la principale** (colore nel calendario) |
| `created_at`, `updated_at` | timestamp | auto | |

Tabelle ponte `event_group(event_id, group_id)` e
`event_category(event_id, category_id, position)`, con chiavi esterne e `ON DELETE` gestito
dal codice di §6.3, non in cascata cieca.

### 7.2 Validazione (`domain/validation.py`, test 4–5)

Messaggi in italiano, restituiti come 422 con il campo interessato:

| Caso | Esito |
|---|---|
| titolo vuoto o > 120 | «Il titolo è obbligatorio (massimo 120 caratteri).» |
| non `all_day` e `start_time` mancante | «Indica l'ora di inizio, oppure scegli “Tutto il giorno”.» |
| stesso giorno, `end_time ≤ start_time` | «L'ora di fine deve essere dopo l'inizio.» |
| più giorni, con orari | ammesso: inizio = `start_date start_time`, fine = `end_date end_time` |
| `end_date < start_date` | «La data di fine è prima della data di inizio.» |
| durata > 31 giorni | «Un evento può durare al massimo 31 giorni.» |
| nessun gruppo / nessuna categoria | «Scegli almeno un gruppo.» / «Scegli almeno una categoria.» |
| id di gruppo/categoria inesistente | 422 con l'id |
| gruppo/categoria archiviati | ammessi solo se l'evento li aveva già (modifica), non sui nuovi |

### 7.3 Ordine cronologico (`chronological_key`, test 7)

Chiave di ordinamento, sempre la stessa ovunque:
1. data di inizio effettiva (vedi sotto);
2. eventi «tutto il giorno» prima di quelli con orario;
3. ora di inizio;
4. ora di fine (nulla dopo le altre);
5. titolo (`casefold`);
6. `id`.

Interrogazioni per intervallo `[from, to]` (estremi inclusi): un evento è incluso se
`start_date ≤ to` **e** `coalesce(end_date, start_date) ≥ from` (sovrapposizione). Negli export
la «data di inizio effettiva» di un evento che inizia prima di `from` è `from` (finisce sotto
il primo mese del periodo), ma il testo mostra sempre le date vere. Test 6.

### 7.4 Duplica

- Da un evento: «Duplica…» apre un mini-calendario in cui si selezionano **più date** (clic
  per aggiungere/togliere, fino a **100** date). Sotto, «Verranno creati N eventi».
- Ogni copia mantiene titolo, orari, `all_day`, durata in giorni (la `end_date` si sposta di
  conseguenza), luogo, note, gruppi e categorie (con lo stesso ordine).
- `POST /api/events/{id}/duplicate {dates: [...]}` crea tutte le copie in una transazione e
  restituisce i nuovi id. Date duplicate nella richiesta: una sola copia. Test 8.

### 7.5 Luoghi

Nessuna tabella dei luoghi: `GET /api/places?q=` restituisce i valori distinti di `place` già
usati (ordinati per frequenza, massimo 10, confronto `casefold`, `q` per prefisso o
sottostringa) per l'autocompletamento nel dialogo.

## 8. Export: contenuti e impaginazione

### 8.1 Modalità

Il contratto è `ExportRequest` (Pydantic):

```
ExportRequest
  period: {from: date, to: date}           # to ≥ from, al massimo 400 giorni
  mode: "per_group" | "single_pdf" | "combined"
  formats: {"pdf", "png"} (almeno uno)
  dpi: 150 | 200 | 300                     # solo PNG, default 200
  selections: [{group_id, category_ids: [..] (≥ 1)}]   # ≥ 1 gruppo
  output_dir: path                         # sotto $HOME (§10.3)
```

| Modalità | Cosa produce | Pagine |
|---|---|---|
| **Un file per gruppo** (`per_group`) | per ogni gruppo un PDF e/o un PNG | **esattamente 1 per gruppo** |
| **PDF unico per gruppi** (`single_pdf`) | un PDF con una pagina per gruppo, nell'ordine dei gruppi; con PNG attivo si ottiene in più un PNG per gruppo | 1 per gruppo |
| **Calendario completo** (`combined`) | un unico documento con gli eventi di tutti i gruppi selezionati | **anche più pagine**; PNG = un file per pagina |

**Regola di inclusione** (identica in tutte le modalità): un evento entra nel foglio del gruppo
G se G è tra i suoi gruppi **e** almeno una delle sue categorie è tra quelle selezionate per G.
Nel **calendario completo** un evento entra se soddisfa la regola per almeno uno dei gruppi
selezionati, e **compare una volta sola**; accanto al titolo si mostrano in piccolo i nomi dei
suoi gruppi selezionati, nell'ordine dei gruppi (§8.3). Test 12.

Un gruppo **senza eventi** nel periodo non produce file: la scheda Export lo segnala prima
(«0 eventi») e il riepilogo finale lo elenca come «saltato: nessun evento».

### 8.2 Formattazione in italiano (`export/formatting.py`, test 13)

Giorni: `lun mar mer gio ven sab dom`. Mesi: `gennaio … dicembre` (abbreviati a 3 lettere
nei formati compatti: `gen feb mar apr mag giu lug ago set ott nov dic`).

| Caso | Colonna data | Colonna orario |
|---|---|---|
| un giorno, inizio e fine | `sab` / `18` | `15:00 – 16:30` |
| un giorno, solo inizio | `sab` / `18` | `ore 15:00` |
| tutto il giorno | `dom` / `26` | `tutto il giorno` |
| più giorni, tutto il giorno | `ven–dom` / `14–16` | `tutto il giorno` |
| più giorni, con orari | `ven–dom` / `14–16` | `ven 18:00 – dom 16:00` |
| più giorni a cavallo di due mesi | `gio–sab` / `30 apr – 2 mag` | come sopra |

Intestazione del periodo:
- `from` è il primo e `to` l'ultimo giorno di un mese → solo i mesi: `ottobre 2026 – giugno
  2027`, oppure `ottobre – dicembre 2026` nello stesso anno, oppure `ottobre 2026` se è un
  solo mese;
- altrimenti date complete: `13 ottobre – 20 dicembre 2026`, `13 ottobre 2026 – 6 gennaio
  2027`.

Intestazioni di mese nell'elenco: `OTTOBRE 2026` (maiuscolo, spaziatura larga).

### 8.3 Aspetto del foglio (minimal, colorato, leggibile)

A4 verticale (210 × 297 mm), margini 14 mm, font Inter incluso.

```
┌──────────────────────────────────────────────┐
│ [logo]  PARROCCHIA SAN …            (grigio)  │
│         Cresimandi                  (22 pt)   │
│         ottobre 2026 – giugno 2027            │
│  ● Catechesi   ● Messa   ● Ritiro   (legenda) │
│ ──────────────────────────────────────────── │
│ OTTOBRE 2026                                  │
│ ▌ sab   15:00 – 16:30   Incontro di gruppo    │
│ ▌ 18                    Oratorio              │
│ ▌ dom   10:30 – 11:30   Messa con i genitori  │
│ ▌ 26                    Chiesa parrocchiale   │
│ NOVEMBRE 2026                                 │
│ …                                             │
│                        aggiornato al 13/10/2026│
└──────────────────────────────────────────────┘
```

- **Intestazione**: logo a sinistra (altezza massima 18 mm, proporzioni mantenute; assente
  se non impostato), nome della parrocchia in piccolo maiuscoletto grigio, nome del gruppo
  grande e in grassetto, periodo sotto. Nel calendario completo il titolo è «Calendario» e
  sotto il periodo compare l'elenco dei gruppi inclusi.
- **Legenda**: un pallino colorato + nome per ogni categoria selezionata **che compare in
  almeno un evento del foglio**, nell'ordine delle categorie.
- **Riga evento**: barra verticale sinistra larga 1.2 mm col colore della categoria; se
  l'evento ha più categorie selezionate, la barra è divisa in segmenti uguali nell'ordine
  delle categorie dell'evento. Mostra **solo le categorie selezionate** per quell'export.
  Colonna data (giorno della settimana piccolo, numero grande colorato con
  `text_color` della categoria principale tra quelle selezionate), colonna orario, titolo in
  grassetto, luogo sotto in grigio (omesso se vuoto). Il titolo va a capo, al massimo 2 righe,
  poi ellissi.
- Nel calendario completo, dopo il titolo, i gruppi in piccolo grigio: `· Cresimandi,
  5ª elementare`.
- **Piè di pagina**: «aggiornato al GG/MM/AAAA» in piccolo grigio a destra; nel calendario
  completo anche «pagina N di M».
- Nessuno sfondo pieno, nessuna ombra: bianco, testo quasi nero (`#1F2328`), grigio
  `#6B7280` per le informazioni secondarie, colore solo su barre, pallini e numeri dei giorni.
- Le righe non si spezzano tra pagine/colonne (`break-inside: avoid`); un'intestazione di
  mese non resta da sola in fondo a una colonna (`break-after: avoid`).

### 8.4 Adattamento a una facciata (`export/autofit.py`, test 14)

Per i fogli a una pagina (`per_group`, `single_pdf`) il programma prova, nell'ordine, le
impaginazioni dalla più leggibile alla più compatta e tiene **la prima che sta in una pagina**:

1. una colonna, corpo del titolo da **11 pt** a **8.5 pt** a passi di 0.5;
2. due colonne, da **9.5 pt** a **7.5 pt** a passi di 0.5.

Il conteggio delle pagine è monotono rispetto al corpo: dentro ciascuna fase si usa una
ricerca binaria (al massimo ~7 composizioni WeasyPrint per foglio). Gli altri testi scalano
in proporzione al corpo del titolo.

Se nemmeno 7.5 pt su due colonne basta, il foglio di quel gruppo **non viene prodotto** e
l'utente vede: «Cresimandi: 112 eventi non entrano in un foglio A4. Riduci il periodo o le
categorie.», con il pulsante **«Esporta su più pagine»** che rifà quel gruppo come calendario
a più pagine (corpo 10 pt). Gli altri gruppi vengono esportati normalmente.

Il calendario completo non usa l'adattamento: corpo fisso **10 pt**, una colonna, più pagine.

Obiettivi da verificare in Fase 4 con titoli e luoghi di lunghezza realistica (titolo medio
~30 caratteri, luogo ~20): **30 eventi** stanno in una colonna a ≥ 9 pt; **80 eventi** stanno
in due colonne a ≥ 7.5 pt. Se non si raggiungono, ricalibrare la riga **dopo aver chiesto**.

### 8.5 PDF e PNG (test 15–17)

- PDF: pagine A4 (595 × 842 pt ± 1), font incorporato, testo selezionabile, metadati
  `Title` = titolo del foglio, `Creator` = calendariParrocchia.
- PNG: rasterizzazione del PDF con pypdfium2. A 150/200/300 dpi le dimensioni sono
  1240 × 1754, 1654 × 2339, 2480 × 3508 px (± 1). Sfondo bianco opaco (niente trasparenza:
  su WhatsApp lo sfondo trasparente diventa nero).

### 8.6 Nomi dei file (`export/output.py`, test 18)

Dentro `<cartella scelta>/Export AAAA-MM-GG HH-MM/`:

| Modalità | Nome |
|---|---|
| per gruppo | `<Gruppo> <from>_<to>.pdf` / `.png` |
| PDF unico | `Calendari per gruppo <from>_<to>.pdf` (+ PNG per gruppo come sopra) |
| completo | `Calendario completo <from>_<to>.pdf`; PNG: `… p1.png`, `… p2.png` |

Date ISO (`2026-10-01`). Dal nome del gruppo si tolgono `/ \ : * ? " < > |` e i caratteri di
controllo, si comprimono gli spazi, si tronca a 80 caratteri. Collisioni → ` (2)`, ` (3)`.

### 8.7 Esecuzione

- `POST /api/export` valida la richiesta, crea un job in memoria e lo esegue in **un thread**
  (un export alla volta; una seconda richiesta durante un export risponde 409 «C'è già un
  export in corso»). `GET /api/export/jobs/{id}` restituisce stato, `done/total` fogli, file
  prodotti, gruppi saltati con il motivo.
- Un errore su un gruppo **non ferma** gli altri; il riepilogo li mostra tutti.
- `POST /api/export/preview` (stessa richiesta, senza `output_dir`) restituisce per ogni
  foglio: numero di eventi, impaginazione scelta (`{columns, font_pt}` o «non entra»), e le
  pagine come PNG a 110 dpi (URL temporanei in memoria, scartati dopo 5 minuti o alla
  richiesta successiva). Una nuova anteprima annulla il risultato della precedente.
- WeasyPrint è importato **pigramente** alla prima anteprima/export (pesa ~80 MB).
- Da misurare in Fase 4: se durante un export le altre API rispondono in più di 300 ms,
  spostare la composizione in un processo separato (chiedere prima).

### 8.8 Intestazione della parrocchia

- `name`: 0–80 caratteri; vuoto = riga omessa.
- `logo`: PNG, JPEG o SVG, al massimo 2 MB. PNG/JPEG vengono ridotti a 600 px sul lato
  lungo e salvati come PNG; l'SVG si salva così com'è (al massimo 512 KB) e le sue risorse
  esterne sono bloccate dall'`url_fetcher` (§2.1). Il logo vive **nel database** (tabella
  `asset`), così il backup è un file solo. Test 25.

## 9. Interfaccia

### 9.1 Schermate

Barra superiore fissa: nome del programma in piccolo, tre schede **Calendario · Gruppi e
categorie · Export** (route `/`, `/gruppi`, `/export`), a destra il menu «⋯» con **Backup
ora**, **Ripristina da backup…**, **Apri cartella dei backup**, **Informazioni**, **Esci**.
La finestra si apre **massimizzata** (flag `--start-maximized` della finestra Chromium, da
aggiungere in `window.py`); F11 = schermo intero.

**Calendario** (`/`)
- Il calendario occupa tutto lo spazio sotto la barra, senza scorrimento della pagina.
- All'apertura: **vista Mese sul mese corrente, oggi evidenziato**. Barra del calendario:
  `‹` `Oggi` `›`, titolo («ottobre 2026»), selettore vista **Mese / Settimana / Elenco**,
  filtri **Gruppi** e **Categorie** (selezione multipla, «tutti» di default), **+ Nuovo
  evento**.
- Eventi colorati con la categoria principale; se ne hanno altre, piccoli pallini dei loro
  colori. Passando sopra un evento: orario, luogo, gruppi, categorie.
- Settimana: fascia oraria visibile 7:00–23:00, scorrimento iniziale all'ora corrente
  (o alle 8:00 se fuori fascia); riga «tutto il giorno» in alto.
- Elenco: eventi del mese visualizzato in ordine cronologico (§7.3).
- **Clic su un giorno vuoto** → nuovo evento con quella data; **selezione di una fascia**
  in Settimana → nuovo evento con data e orari; **clic su un evento** → modifica.
- **Trascinamento** di un evento su un altro giorno/orario lo sposta (durata invariata);
  compare un avviso «Evento spostato — Annulla» per 8 secondi.
- Base vuota (nessun gruppo o nessuna categoria): al posto del pulsante «+ Nuovo evento» un
  riquadro «Per inserire eventi crea almeno un gruppo e una categoria» con il pulsante che
  porta a Gruppi e categorie.
- I filtri e la vista scelta si ricordano (§10.2); all'apertura si torna comunque **a oggi**.

**Dialogo evento**
- Campi nell'ordine: Titolo · Data (+ interruttore «Più giorni» che mostra «fino al») ·
  interruttore «Tutto il giorno» · Ora inizio · Ora fine · Luogo (autocompletamento §7.5) ·
  Gruppi (chip a selezione multipla) · Categorie (chip a selezione multipla col colore; la
  prima scelta è la principale, contrassegnata da una stella; clic sulla stella per cambiarla) ·
  Note (area di testo, con la dicitura «Solo per te: non compaiono nei fogli esportati»).
- Pulsanti: **Salva**, **Annulla**; in modifica anche **Duplica…** e **Elimina** (con
  conferma). Errori di validazione accanto al campo.
- Scorciatoie: `Ctrl+Invio` salva, `Esc` chiude (chiedendo conferma se ci sono modifiche).

**Gruppi e categorie** (`/gruppi`)
- Due colonne affiancate, Gruppi e Categorie. Ogni riga: maniglia di trascinamento, nome
  (modificabile in linea), colore (solo categorie, con palette + selettore libero), numero di
  eventi, menu con Archivia/Ripristina ed Elimina (§6.3). In fondo «+ Aggiungi».
- Interruttore «Mostra archiviati».

**Export** (`/export`)
- Colonna sinistra (impostazioni), colonna destra (anteprima).
- **Periodo**: «dal» / «al» + scorciatoie **Questo mese**, **Prossimo mese**, **Prossimi 3
  mesi**, **Anno pastorale** (1 settembre – 30 giugno che contiene oggi; in luglio e agosto
  quello che inizia a settembre).
- **Modalità**: Un file per gruppo · PDF unico per gruppi · Calendario completo.
- **Formato**: PDF ☑ PNG ☐ (almeno uno) e, con PNG, la risoluzione (150 schermo / 200 /
  300 stampa).
- **Gruppi**: elenco con casella di spunta e numero di eventi nel periodo (aggiornato al
  volo); ogni gruppo si espande e mostra le categorie come chip colorati, **tutte attive di
  default**, con «Tutte / Nessuna». «Seleziona tutti i gruppi».
- **Intestazione**: nome della parrocchia e logo (carica / rimuovi, con miniatura).
- **Cartella**: percorso + **Sfoglia…** (selettore dentro l'app, §10.3), default
  `~/Documenti/Calendari parrocchia/` (creata al primo export se non esiste).
- **Esporta**: barra di avanzamento per fogli, poi riepilogo (file prodotti, gruppi saltati
  con il motivo) e **Apri cartella** (`gio open`, ripiego `xdg-open`).
- **Anteprima**: le pagine di ogni foglio, navigabili per gruppo; per ciascuno un'etichetta
  «1 colonna, 10 pt» / «2 colonne, 8 pt» / «non entra in un A4» in rosso. Si aggiorna
  400 ms dopo l'ultima modifica.

### 9.2 Requisiti della finestra applicativa

- La navigazione vive tutta dentro l'app: ogni schermata ha un percorso di ritorno visibile
  (le schede sono sempre visibili).
- Nessuna funzione raggiungibile solo digitando un URL.
- Un errore fatale del frontend non lascia una finestra bianca: messaggio + «Ricarica»
  (`ErrorBoundary` dello scaffold).
- Utilizzabile da 1280 × 800 in su.

### 9.3 Reattività

- Cambio di mese/settimana con 2 000 eventi nel database: nuovo intervallo disegnato in
  < 150 ms (query `GET /api/events?from&to` < 50 ms, indice su `start_date`/`end_date`).
- Salvataggio di un evento: chiusura del dialogo e calendario aggiornato in < 200 ms.
- Conteggi della scheda Export aggiornati in < 200 ms.
- Anteprima di un foglio con 40 eventi in < 1.5 s.

## 10. Dati e persistenza

### 10.1 Database

- File `~/.local/share/calendariparrocchia/catalog.db` (SQLite). Pragma a ogni connessione:
  `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=15000`, `foreign_keys=ON`.
- Sessioni brevi con `session_scope()` (commit o rollback). Mai una sessione aperta durante
  la composizione dei PDF: si leggono i dati, si chiude, poi si compone.
- Schema gestito da **Alembic**, migrazioni applicate all'avvio; versione dello schema anche
  nella tabella `setting` (chiave `schema_version`) per il controllo dei backup.
- Tabelle: `group`, `category`, `event`, `event_group`, `event_category`, `setting(key,
  value JSON)`, `asset(key, mime, data BLOB, updated_at)`. Indici su `event.start_date`,
  `event.end_date`, chiavi delle tabelle ponte.

### 10.2 Impostazioni persistenti

`GET /api/settings`, `PUT /api/settings/{key}`, con un validatore per chiave (tabella
`_WRITABLE`; chiavi sconosciute → 404, valori non validi → 422). Test 22.

| Chiave | Contenuto |
|---|---|
| `calendar.view` | `month` / `week` / `list` |
| `calendar.filters` | id di gruppi e categorie selezionati (id spariti ignorati) |
| `export.last` | periodo, modalità, formati, dpi, gruppi e categorie per gruppo, cartella |
| `parish.name` | nome della parrocchia |

Il logo sta nella tabella `asset` (chiave `parish.logo`).

### 10.3 Selettore di cartelle

- `GET /api/folders?path=` elenca le sottocartelle (non i file) di `path`, nascoste escluse
  salvo `hidden=1`; `POST /api/folders` crea una cartella («Nuova cartella»).
- **Ogni percorso è risolto (`Path.resolve()`) e deve stare sotto `$HOME`**: altrimenti 403.
  Vale anche per `output_dir` dell'export e per i symlink che puntano fuori. Test 20.
- `POST /api/folders/open` apre una cartella nel file manager.

### 10.4 Backup e ripristino (`backup.py`, test 23–24)

- **Backup ora**: `VACUUM INTO` (copia coerente anche a programma aperto) nel file scelto con
  il selettore di cartelle; nome di default `calendariParrocchia backup AAAA-MM-GG.db`.
  Contiene tutto, logo compreso.
- **Backup automatico**: all'avvio, se l'ultimo ha più di 24 ore, copia in
  `~/.local/share/calendariparrocchia/backups/auto-AAAA-MM-GG.db`; si tengono gli ultimi
  **14**.
- **Ripristino**: si sceglie un file; il programma verifica che sia un database di questa app
  (tabella `setting` con `app = calendariparrocchia`) con `schema_version` ≤ quella corrente
  (se è più vecchia, applica le migrazioni). Poi, sotto un lock che sospende le scritture:
  chiude il motore SQLAlchemy, sposta il database attuale in
  `catalog-prima-del-ripristino-AAAA-MM-GG-HHMMSS.db`, copia il backup, riapre, e
  l'interfaccia si ricarica. File non valido → messaggio chiaro, nulla cambia.

### 10.5 Cartelle

- Dati: `~/.local/share/calendariparrocchia/` (database, backup automatici).
- Impostazioni del programma: nel database (§10.2).
- Log: `~/.local/state/calendariparrocchia/logs/` (scaffold, 3 × 1 MB).
- Export: dove sceglie l'utente, sotto `$HOME`.
- Nessuna cache su disco: le anteprime vivono in memoria.

## 11. Server locale e finestra (garantiti dallo scaffold)

- Server solo su `127.0.0.1:8746`, nessuna opzione per esporlo; richieste da pagine estranee
  rifiutate (controllo Host/Origin).
- Istanza singola: il secondo avvio mostra la finestra esistente ed esce con 0; lockfile
  stantio rimosso; porta occupata da altri → errore con l'indicazione di `--port`, mai
  un'altra porta in silenzio.
- Finestra Chromium `--app` con profilo dedicato e identità propria nella dock; senza
  Chromium, scheda del browser + avviso. Da aggiungere: apertura massimizzata (§9.1).
- Chiudere la finestra chiude il programma; «Esci» nel menu fa lo stesso. Se un export è in
  corso, chiudere la finestra lo lascia finire prima di uscire (al massimo 30 s), senza file
  a metà: un file incompleto viene eliminato.

## 12. Errori e diagnostica

- Messaggi all'utente in italiano comprensibile, mai un traceback in un dialogo; il dettaglio
  tecnico va nel log.
- Un errore su un gruppo non ferma l'export degli altri; il riepilogo lo mostra (§8.7).
- Nessuna chiamata di rete (§2.1).
- Errori delle API in formato uniforme `{"error": {"code", "message", "field?"}}`.

## 13. Distribuzione e installazione

`install.sh` (dallo scaffold): idempotente, senza sudo; se manca qualcosa stampa il comando
esatto e si ferma. Installa comando, icone, voce di menu (`Categories=Office;Calendar;`).
`uninstall.sh` non tocca i dati senza un «sì» esplicito.

Aggiunte specifiche:
- verifica `libpango-1.0-0` (`ldconfig -p | grep libpango-1.0`), altrimenti stampa
  `sudo apt install libpango-1.0-0 libpangoft2-1.0-0` e si ferma;
- il font Inter e la sua licenza OFL entrano nel pacchetto (`export/assets/fonts/`).

## 14. Prestazioni e budget

| Misura | Target | Come si misura |
|---|---|---|
| Avvio fino alla finestra pronta | < 2 s | dal lancio a `GET /api/health` + finestra |
| RAM del backend a riposo | ≤ 150 MB (prima del primo export) | RSS del processo Python |
| RAM del backend dopo un export | ≤ 300 MB | RSS dopo l'export di 15 gruppi |
| Query eventi di un mese, 10 000 eventi nel DB | < 50 ms | test di prestazione in `tests/bench/` |
| Anteprima di un foglio da 40 eventi | < 1.5 s | idem |
| Export di un foglio (PDF + PNG 200 dpi) | < 3 s | idem |
| Export di 15 gruppi, PDF | < 30 s | idem |

La finestra Chromium (~150–300 MB) non entra nel budget del backend.

## 15. Test richiesti

Numerati: i commenti e STATO.md li citano («test 7»).

1. Database creato da zero con le migrazioni; un secondo avvio non cambia nulla.
2. Gruppi e categorie: nome ripulito, unicità senza maiuscole (anche contro archiviati) → 409,
   limiti di lunghezza → 422, riordino.
3. Colori: formato `#RRGGBB` validato e salvato in maiuscolo; assegnazione automatica del
   primo colore libero della palette, poi ripartenza.
4. Validazione evento: ogni riga della tabella di §7.2.
5. Gruppi/categorie obbligatori, id inesistenti, archiviati vietati sui nuovi eventi e
   ammessi in modifica se già presenti.
6. Query per intervallo: sovrapposizione con eventi su più giorni a cavallo di `from` e `to`,
   estremi inclusi.
7. Ordine cronologico: casi misti (tutto il giorno, stessa ora, fine nulla, titoli uguali)
   in ordine deterministico.
8. Duplica: N date → N eventi con orari, durata, luogo, gruppi e categorie (ordine compreso);
   date ripetute ignorate; > 100 date → 422.
9. Eliminazione di un gruppo: senza orfani; con orfani → 409 senza scelta, `reassign`,
   `delete`; tutto atomico.
10. Lo stesso per le categorie (incluso il cambio di categoria principale quando si elimina
    la prima).
11. Archivio: elementi archiviati esclusi dalle liste di scelta, eventi intatti.
12. Selezione per l'export: regola gruppo ∧ categoria; categorie non selezionate escluse da
    barre e legenda; calendario completo senza duplicati e con le etichette dei gruppi;
    gruppi senza eventi saltati; le note interne non compaiono nei `Sheet` né nel testo del PDF.
13. Formattazione in italiano: ogni riga delle tabelle di §8.2, intestazioni di periodo,
    anno pastorale in ogni mese dell'anno.
14. Adattamento: 0 eventi (saltato), 1, 30 (una colonna, ≥ 9 pt), 80 (due colonne, ≥ 7.5 pt),
    200 (non entra → errore dedicato); ogni foglio prodotto ha **esattamente una pagina**
    (contata con pypdfium2).
15. PDF: pagine A4 595 × 842 ± 1, font Inter incorporato, testo estraibile contiene titoli,
    luoghi e orari; metadati `Title`.
16. PNG: dimensioni esatte a 150/200/300 dpi, sfondo opaco; calendario completo su più
    pagine → un PNG per pagina.
17. Modalità: `per_group` → un file per gruppo; `single_pdf` → pagine = gruppi; `combined` →
    più pagine con «pagina N di M».
18. Nomi dei file: caratteri vietati tolti, troncamento, collisioni ` (2)`; un file
    preesistente con lo stesso nome resta intatto (hash prima/dopo).
19. Nessuna rete: export completo con logo SVG che punta a `https://…` e `file:///etc/…`
    senza alcuna `connect` e senza leggere file fuori dalle risorse.
20. Cartelle: percorsi fuori da `$HOME`, `..` e symlink verso l'esterno → 403; elenco delle
    sole sottocartelle; nascoste solo con `hidden=1`.
21. Contrasto: `text_color` porta ogni colore della palette (e un giallo chiaro libero) a
    ≥ 4.5:1 sul bianco; un colore già scuro resta uguale.
22. Impostazioni: lettura/scrittura delle chiavi di §10.2, chiave sconosciuta → 404, valore
    non valido → 422, id spariti ignorati in lettura.
23. Backup e ripristino: il backup è un database valido con gli stessi dati; il ripristino
    rifiuta un file qualsiasi e uno con schema più nuovo; dopo il ripristino i dati
    coincidono e il database precedente è stato messo da parte.
24. Backup automatico: uno solo al giorno, conservati gli ultimi 14.
25. Logo: tipi e dimensioni ammessi/rifiutati, PNG ridotto a 600 px, salvato nel database,
    presente nel PDF.
26. Frontend: `npm run typecheck` e `npm run build` senza errori.
27. Prestazioni (in `tests/bench/`, esclusi dalla suite rapida): i numeri di §14.

## 16. Fasi di sviluppo

- **Fase 0 — Scaffold** (fatta): server, finestra, istanza singola, installazione, test di
  base verdi.
- **Fase 1 — Dati e API**: modelli, migrazioni Alembic, CRUD di gruppi, categorie ed eventi,
  validazione, query per intervallo, ordine cronologico, duplica, eliminazione con orfani,
  archivio, luoghi, impostazioni. *Accettazione:* test 1–11 e 22 verdi; API esplorabili su
  `/docs`.
- **Fase 2 — Scheda Gruppi e categorie**: liste con modifica in linea, colori (palette +
  libero), riordino, archivio, eliminazione con dialogo degli orfani; barra con le tre schede
  e menu «⋯». *Accettazione:* test 2–3, 9–11 ancora verdi, test 26; controllo a mano
  descritto in STATO.md.
- **Fase 3 — Calendario**: FullCalendar con viste Mese/Settimana/Elenco aperte su oggi,
  dialogo evento, Duplica, trascinamento con Annulla, filtri, stato vuoto, scorciatoie,
  finestra massimizzata. *Accettazione:* test 26; con 2 000 eventi generati il cambio di mese
  rispetta §9.3 (misurato, annotato in STATO.md).
- **Fase 4 — Motore di export**: selezione, formattazione, modelli HTML/CSS, adattamento, PDF,
  PNG, tre modalità, nomi file, `url_fetcher` sicuro, logo, job. *Accettazione:* test 12–21 e
  25 verdi; **l'utente approva l'aspetto** su PDF di prova (10, 30, 80 eventi e calendario
  completo) generati con un comando di sviluppo prima di passare alla Fase 5.
- **Fase 5 — Scheda Export**: impostazioni, conteggi al volo, anteprima, selettore cartelle,
  avanzamento, riepilogo, «Apri cartella», memoria delle ultime scelte. *Accettazione:*
  test 20, 26; anteprima e export entro §14.
- **Fase 6 — Backup, rifiniture, installazione**: backup manuale e automatico, ripristino,
  verifica di `install.sh` (Pango, font), README completo. *Accettazione:* test 23–24 e 27
  verdi; installazione provata, icona e nome corretti nella dock.

## 17. Licenza

**GPL-3.0-or-later.** Compatibile con le dipendenze: WeasyPrint (BSD-3), Jinja2 (BSD-3),
pypdfium2 (Apache-2.0/BSD-3), Pillow (HPND), SQLAlchemy e Alembic (MIT), FastAPI (MIT),
FullCalendar (MIT, solo plugin standard), font Inter (SIL OFL 1.1, testo della licenza nel
repository accanto al font).

## 18. Regole di lavoro per l'agente

- **Test insieme al codice**: ogni fase si chiude solo con i suoi test verdi; per l'export si
  usano dati sintetici generati nei test (0, 1, 30, 80, 200 eventi), mai dati reali
  committati.
- **File sotto ~400 righe**, backend e frontend: se un modulo cresce, si divide.

## 19. Punti aperti

- Feste liturgiche e festività (Natale, Pasqua mobile) mostrate nel calendario: v2?
- Avviso quando due categorie hanno colori troppo simili.
- Gruppi «padre» (es. «Catechismo» che comprende le cinque classi) per esportare più gruppi
  in un colpo: da valutare dopo l'uso reale.

## 20. Primo passo

1. Leggi `STATO.md` e questo file.
2. Implementa la Fase 1.
