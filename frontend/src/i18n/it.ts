// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Every string the user can read lives here: no visible literal in a component,
// so another language is translation work, not a refactor. Keys read like
// paths: screen, then element. Each screen has its own file (it.taxonomy.ts,
// ...), spread in here; what the whole program shares stays in this one.
import { itTaxonomy } from './it.taxonomy'

export const it = {
  'app.name': 'calendariParrocchia',
  'app.description': 'Calendario dei gruppi parrocchiali con fogli A4 da distribuire.',
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
  'menu.soon': 'Arriva in una prossima versione',
  'about.title': 'Informazioni',
  'about.version': 'Versione {version}',
  'about.offline': 'Funziona senza Internet: i dati restano su questo computer.',
  'about.license': 'Software libero, distribuito con licenza GPL-3.0 o successiva.',
  'common.close': 'Chiudi',
  'common.cancel': 'Annulla',
  'calendar.soon': 'Qui comparirà il calendario: arriva con la Fase 3.',
  'export.soon': 'Qui si prepareranno i fogli da stampare: arriva con la Fase 5.',
  'window.tabNotice.title': 'Aperto in una scheda del browser',
  'window.tabNotice.dismiss': 'Non mostrare più',
  'quit.done': 'calendariParrocchia è stato chiuso. Puoi chiudere questa finestra.',
  'error.network': 'Il programma non risponde: è ancora in esecuzione?',
  'error.title': 'Qualcosa è andato storto',
  'error.reload': 'Ricarica',
  ...itTaxonomy,
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
