// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Gruppi e categorie" (SPEC §6, §9.1). Keys that differ by kind carry it in the
// path (`taxonomy.groups.…` / `taxonomy.categories.…`), because Italian needs the
// gender: "nuovo gruppo", "nuova categoria".
export const itTaxonomy = {
  'taxonomy.showArchived': 'Mostra archiviati',
  'taxonomy.archivedHint':
    'Un elemento archiviato non si sceglie più per i nuovi eventi, ma resta su quelli che lo hanno già.',
  'taxonomy.loading': 'Caricamento…',
  'taxonomy.count.zero': 'nessun evento',
  'taxonomy.count.one': '1 evento',
  'taxonomy.count.many': '{n} eventi',
  'taxonomy.actions': 'Azioni',
  'taxonomy.rename': 'Fai clic per rinominare',
  'taxonomy.archive': 'Archivia',
  'taxonomy.restore': 'Ripristina',
  'taxonomy.delete': 'Elimina…',
  'taxonomy.dragHandle': 'Trascina per riordinare, oppure usa le frecce ↑ ↓',
  'taxonomy.color': 'Cambia colore',
  'taxonomy.color.palette': 'Colori predefiniti',
  'taxonomy.color.custom': 'Altro colore…',

  'taxonomy.groups.title': 'Gruppi',
  'taxonomy.groups.empty':
    'Nessun gruppo. Aggiungi le classi di catechismo, i cresimandi, il coro, l’oratorio…',
  'taxonomy.groups.add': '+ Aggiungi gruppo',
  'taxonomy.groups.placeholder': 'Nome del nuovo gruppo, poi Invio',
  'taxonomy.groups.archived': 'archiviato',

  'taxonomy.categories.title': 'Categorie',
  'taxonomy.categories.empty':
    'Nessuna categoria. Aggiungi Catechesi, Messa, Ritiro, Festa… Ognuna ha un colore.',
  'taxonomy.categories.add': '+ Aggiungi categoria',
  'taxonomy.categories.placeholder': 'Nome della nuova categoria, poi Invio',
  'taxonomy.categories.archived': 'archiviata',

  // Deletion (SPEC §6.3): the dialog says what happens to the linked events.
  'delete.groups.title': 'Eliminare il gruppo «{name}»?',
  'delete.categories.title': 'Eliminare la categoria «{name}»?',
  'delete.loading': 'Controllo degli eventi collegati…',
  'delete.none': 'Nessun evento è collegato: l’eliminazione non tocca il calendario.',
  'delete.groups.linked.one': '1 evento perde il collegamento a questo gruppo.',
  'delete.groups.linked.many': '{n} eventi perdono il collegamento a questo gruppo.',
  'delete.categories.linked.one': '1 evento perde il collegamento a questa categoria.',
  'delete.categories.linked.many': '{n} eventi perdono il collegamento a questa categoria.',
  'delete.groups.orphans.one': '1 evento ha solo questo gruppo. Che cosa ne facciamo?',
  'delete.groups.orphans.many': '{n} eventi hanno solo questo gruppo. Che cosa ne facciamo?',
  'delete.categories.orphans.one': '1 evento ha solo questa categoria. Che cosa ne facciamo?',
  'delete.categories.orphans.many':
    '{n} eventi hanno solo questa categoria. Che cosa ne facciamo?',
  'delete.reassign.one': 'Spostalo in…',
  'delete.reassign.many': 'Spostali in…',
  'delete.reassign.choose': 'Scegli…',
  'delete.groups.noTarget': 'Non ci sono altri gruppi in cui spostarli.',
  'delete.categories.noTarget': 'Non ci sono altre categorie in cui spostarli.',
  'delete.alsoEvents.one': 'Elimina anche questo evento',
  'delete.alsoEvents.many': 'Elimina anche questi {n} eventi',
  'delete.groups.archiveHint':
    'Se è un gruppo di un anno passato, puoi archiviarlo: sparisce dalle scelte ma resta sugli eventi.',
  'delete.categories.archiveHint':
    'Se non la usi più, puoi archiviarla: sparisce dalle scelte ma resta sugli eventi.',
  'delete.archiveInstead': 'Archivia invece',
  'delete.confirm': 'Elimina',
  'delete.working': 'Eliminazione…',
} as const
