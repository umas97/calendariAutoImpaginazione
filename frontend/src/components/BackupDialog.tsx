// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Backup ora" (SPEC §10.4): a folder from the picker inside the program, a
// name (`calendariAutoImpaginazione backup AAAA-MM-GG.db` by default), and the whole
// database copied there. A name already taken becomes `… (2).db`: the server
// never replaces a file. Then where it went, and "Apri cartella".
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type BackupOptions } from '../lib/api'
import { longDateTime } from '../lib/dates'
import { t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'
import { FolderBrowser, tildePath } from './FolderBrowser'

export function BackupDialog({ onClose }: { onClose: () => void }) {
  const options = useQuery({ queryKey: ['backup'], queryFn: api.backupOptions, staleTime: 0 })
  if (!options.data) {
    return (
      <Dialog
        title={t('backup.title')}
        onClose={onClose}
        footer={
          <button className={buttonClass.secondary} onClick={onClose}>
            {t('common.close')}
          </button>
        }
      >
        <p className={options.error ? 'text-red-400' : 'text-ink-300'}>
          {options.error ? options.error.message : t('export.loading')}
        </p>
      </Dialog>
    )
  }
  return <BackupForm options={options.data} onClose={onClose} />
}

function BackupForm({ options, onClose }: { options: BackupOptions; onClose: () => void }) {
  const [folder, setFolder] = useState(options.default_folder)
  const [name, setName] = useState(options.default_name)
  const [browsing, setBrowsing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  const save = async () => {
    setBusy(true)
    setError(null)
    try {
      setSaved((await api.backupNow(folder, name)).path)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const openFolder = async () => {
    try {
      await api.openFolder(folder)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  if (saved) {
    return (
      <Dialog
        title={t('backup.done')}
        onClose={onClose}
        footer={
          <>
            <button className={buttonClass.secondary} onClick={() => void openFolder()}>
              {t('backup.openFolder')}
            </button>
            <button className={buttonClass.primary} onClick={onClose} autoFocus>
              {t('common.close')}
            </button>
          </>
        }
      >
        <p className="text-ink-200">{t('backup.savedIn')}</p>
        <p className="break-all rounded bg-ink-900 px-2 py-1 font-mono text-xs">{tildePath(saved, options.home)}</p>
        {error ? <p className="text-red-400">{error}</p> : null}
      </Dialog>
    )
  }

  return (
    <Dialog
      title={t('backup.title')}
      onClose={onClose}
      width="max-w-lg"
      footer={
        <>
          <button className={buttonClass.secondary} onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button className={buttonClass.primary} disabled={busy || !name.trim()} onClick={() => void save()}>
            {busy ? t('backup.saving') : t('backup.save')}
          </button>
        </>
      }
    >
      <p className="text-ink-200">{t('backup.intro')}</p>
      <div className="space-y-1">
        <span className="block text-ink-300">{t('backup.folder')}</span>
        <div className="flex items-center gap-2">
          <p title={folder} className="min-w-0 flex-1 truncate rounded border border-ink-600 bg-ink-900 px-2 py-1 font-mono text-xs">
            {tildePath(folder, options.home)}
          </p>
          <button type="button" className={buttonClass.secondary} onClick={() => setBrowsing(true)}>
            {t('backup.browse')}
          </button>
        </div>
      </div>
      <div className="space-y-1">
        <label htmlFor="backup-name" className="block text-ink-300">
          {t('backup.name')}
        </label>
        <input
          id="backup-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !busy && name.trim()) void save()
          }}
          className="w-full rounded border border-ink-600 bg-ink-900 px-2 py-1 text-sm"
        />
        <p className="text-xs text-ink-300">{t('backup.nameHint')}</p>
      </div>
      {error ? <p className="text-red-400">{error}</p> : null}
      <p className="text-xs text-ink-300">
        {t('backup.auto')}{' '}
        {options.last_auto ? t('backup.lastAuto', { when: longDateTime(options.last_auto) }) : t('backup.noAuto')}
      </p>
      {browsing ? (
        <FolderBrowser
          initial={folder}
          home={options.home}
          onClose={() => setBrowsing(false)}
          onChoose={(chosen) => {
            setBrowsing(false)
            setFolder(chosen)
          }}
        />
      ) : null}
    </Dialog>
  )
}
