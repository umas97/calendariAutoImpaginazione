// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The backup entries of the "⋯" menu (SPEC §10.4): "Backup ora", "Ripristina
// da backup…", "Apri cartella dei backup".
export const itBackup = {
  'backup.title': 'Backup ora',
  'backup.intro': 'Una copia completa dei dati: eventi, gruppi, categorie, impostazioni e logo.',
  'backup.folder': 'Cartella',
  'backup.browse': 'Sfoglia…',
  'backup.name': 'Nome del file',
  'backup.nameHint': 'Se esiste già un file con questo nome, il backup prende un nome nuovo: nessun file viene sostituito.',
  'backup.save': 'Salva backup',
  'backup.saving': 'Salvataggio…',
  'backup.done': 'Backup salvato',
  'backup.savedIn': 'Il backup è stato salvato in:',
  'backup.openFolder': 'Apri cartella',
  'backup.auto': 'Ogni giorno, all’avvio, il programma fa anche un backup automatico (tiene gli ultimi 14).',
  'backup.lastAuto': 'Ultimo backup automatico: {when}.',
  'backup.noAuto': 'Nessun backup automatico, per ora.',

  'restore.pick': 'Scegli il backup da ripristinare',
  'restore.choose': 'Ripristina questo backup…',
  'restore.reading': 'Lettura del backup…',
  'restore.confirm.title': 'Ripristinare questo backup?',
  'restore.confirm.file': '«{name}», del {when}, contiene:',
  'restore.confirm.events.one': '{n} evento',
  'restore.confirm.events.many': '{n} eventi',
  'restore.confirm.groups.one': '{n} gruppo',
  'restore.confirm.groups.many': '{n} gruppi',
  'restore.confirm.categories.one': '{n} categoria',
  'restore.confirm.categories.many': '{n} categorie',
  'restore.confirm.warning':
    'Tutti i dati di adesso saranno sostituiti da quelli del backup. Per sicurezza, il database attuale viene conservato nella cartella del programma.',
  'restore.confirm.action': 'Ripristina',
  'restore.otherFile': 'Scegli un altro file',
  'restore.invalid.title': 'Impossibile ripristinare',
  'restore.restoring': 'Ripristino in corso…',
  'restore.done.title': 'Ripristino completato',
  'restore.done.text': 'I dati del backup sono di nuovo al loro posto. Quelli di prima sono conservati in:',
  'restore.done.reload': 'Ricarica il programma',

  'backupFolder.errorTitle': 'Cartella dei backup',
} as const
