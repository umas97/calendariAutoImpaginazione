// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Every string the user can read lives here: no visible literal in a component,
// so another language is translation work, not a refactor. Keys read like
// paths: screen, then element. Each screen has its own file (it.taxonomy.ts,
// ...), spread in here; what the whole program shares stays in this one.
import { itBackup } from './it.backup'
import { itCalendar } from './it.calendar'
import { itExport } from './it.export'
import { itTaxonomy } from './it.taxonomy'

export const it = {
  'app.name': 'calendariAutoImpaginazione',
  'app.description':
    'Calendario delle attività che impagina da sé i fogli A4 da distribuire: uno per gruppo, con i soli eventi che lo riguardano.',
  'nav.calendar': 'Calendario',
  'nav.taxonomy': 'Gruppi e categorie',
  'nav.export': 'Export',
  'nav.quit': 'Esci',
  'nav.quitting': 'Chiusura in corso…',
  'nav.install': 'Installa come app',
  'menu.label': 'Altre funzioni',
  'menu.backup': 'Backup ora',
  'menu.restore': 'Ripristina da backup…',
  'menu.backupFolder': 'Apri cartella dei backup',
  'menu.about': 'Informazioni',
  'about.title': 'Informazioni',
  'about.version': 'Versione {version}',
  'about.features': 'Cosa fa',
  'about.feature.calendar':
    'Calendario: viste Mese, Settimana ed Elenco, filtri, eventi spostabili trascinandoli e duplicabili su più date. Le note di un evento restano private e non finiscono mai nei fogli.',
  'about.feature.taxonomy':
    'Gruppi e categorie: ogni evento appartiene a uno o più gruppi e ha una o più categorie, ciascuna con il suo colore.',
  'about.feature.export':
    'Export: PDF da stampare o PNG da condividere, un foglio per gruppo in ordine cronologico. Ogni foglio si adatta da solo alla pagina A4, con intestazione e logo a scelta.',
  'about.data': 'I tuoi dati',
  'about.offline':
    'Funziona senza Internet e non invia nulla: i dati restano su questo computer. Ogni giorno, all’avvio, viene salvato un backup automatico (restano gli ultimi 14); dal menu «⋯» puoi farne uno quando vuoi o ripristinarlo.',
  'about.license': 'Software libero, distribuito con licenza GPL-3.0 o successiva.',
  'common.close': 'Chiudi',
  'common.cancel': 'Annulla',
  'window.tabNotice.title': 'Aperto in una scheda del browser',
  'window.tabNotice.dismiss': 'Non mostrare più',
  'quit.done': 'calendariAutoImpaginazione è stato chiuso. Puoi chiudere questa finestra.',
  'error.network': 'Il programma non risponde: è ancora in esecuzione?',
  'error.title': 'Qualcosa è andato storto',
  'error.reload': 'Ricarica',
  ...itCalendar,
  ...itTaxonomy,
  ...itExport,
  ...itBackup,
} as const

export type MessageKey = keyof typeof it

/** The string for `key`, with `{name}` placeholders filled from `vars`. */
export function t(key: MessageKey, vars: Record<string, string | number> = {}): string {
  return it[key].replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? `{${name}}`))
}

/** `key.one` for 1, `key.many` otherwise, with `{n}` filled in. */
export function plural(key: PluralKey, n: number): string {
  return t(`${key}.${n === 1 ? 'one' : 'many'}` as MessageKey, { n })
}

type PluralKey = {
  [K in MessageKey]: K extends `${infer Base}.one` ? (`${Base}.many` extends MessageKey ? Base : never) : never
}[MessageKey]
