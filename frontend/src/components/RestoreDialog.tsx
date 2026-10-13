// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Ripristina da backup…" (SPEC §10.4), in steps: the picker opens on the
// automatic backups and lists the `.db` files; the server reads the chosen one
// (nothing changes yet) and says what it holds, or why it cannot be restored;
// a confirmation; the restore; then the whole interface reloads, because every
// cached list now belongs to another database.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type BackupInfo } from '../lib/api'
import { longDateTime } from '../lib/dates'
import { plural, t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'
import { FolderBrowser, tildePath } from './FolderBrowser'

type Step =
  | { kind: 'pick' }
  | { kind: 'reading' }
  | { kind: 'invalid'; message: string }
  | { kind: 'confirm'; info: BackupInfo; error?: string }
  | { kind: 'restoring'; info: BackupInfo }
  | { kind: 'done'; aside: string }

const baseName = (path: string) => path.slice(path.lastIndexOf('/') + 1)

export function RestoreDialog({ onClose }: { onClose: () => void }) {
  const options = useQuery({ queryKey: ['backup'], queryFn: api.backupOptions, staleTime: 0 })
  const [step, setStep] = useState<Step>({ kind: 'pick' })
  const home = options.data?.home ?? ''
  const reload = () => window.location.reload()

  const read = async (path: string) => {
    setStep({ kind: 'reading' })
    try {
      setStep({ kind: 'confirm', info: await api.inspectBackup(path) })
    } catch (err) {
      setStep({ kind: 'invalid', message: (err as Error).message })
    }
  }

  const restore = async (info: BackupInfo) => {
    setStep({ kind: 'restoring', info })
    try {
      setStep({ kind: 'done', aside: (await api.restore(info.path)).aside })
    } catch (err) {
      setStep({ kind: 'confirm', info, error: (err as Error).message })
    }
  }

  if (!options.data) {
    return options.error ? (
      <Message title={t('restore.invalid.title')} text={options.error.message} onClose={onClose} />
    ) : null
  }

  if (step.kind === 'pick') {
    const start = options.data.auto_dir.startsWith(`${home}/`) ? options.data.auto_dir : home
    return (
      <FolderBrowser
        pickFile
        initial={start}
        home={home}
        title={t('restore.pick')}
        chooseLabel={t('restore.choose')}
        onClose={onClose}
        onChoose={(path) => void read(path)}
      />
    )
  }

  if (step.kind === 'reading') return <Message title={t('restore.pick')} text={t('restore.reading')} />

  if (step.kind === 'invalid') {
    return (
      <Message
        title={t('restore.invalid.title')}
        text={step.message}
        onClose={onClose}
        onBack={() => setStep({ kind: 'pick' })}
      />
    )
  }

  if (step.kind === 'done') {
    return (
      <Dialog
        title={t('restore.done.title')}
        onClose={reload}
        footer={
          <button className={buttonClass.primary} onClick={reload} autoFocus>
            {t('restore.done.reload')}
          </button>
        }
      >
        <p className="text-ink-200">{t('restore.done.text')}</p>
        <p className="break-all rounded bg-ink-900 px-2 py-1 font-mono text-xs">{tildePath(step.aside, home)}</p>
      </Dialog>
    )
  }

  const { info } = step
  const busy = step.kind === 'restoring'
  return (
    <Dialog
      title={t('restore.confirm.title')}
      width="max-w-lg"
      onClose={() => {
        if (!busy) onClose()
      }}
      footer={
        <>
          <button className={buttonClass.secondary} disabled={busy} onClick={() => setStep({ kind: 'pick' })}>
            {t('restore.otherFile')}
          </button>
          <button className={buttonClass.secondary} disabled={busy} onClick={onClose} autoFocus>
            {t('common.cancel')}
          </button>
          <button className={buttonClass.danger} disabled={busy} onClick={() => void restore(info)}>
            {busy ? t('restore.restoring') : t('restore.confirm.action')}
          </button>
        </>
      }
    >
      <p className="text-ink-200">
        {t('restore.confirm.file', { name: baseName(info.path), when: longDateTime(info.modified) })}
      </p>
      <p className="text-base text-ink-50">
        {[
          plural('restore.confirm.events', info.events),
          plural('restore.confirm.groups', info.groups),
          plural('restore.confirm.categories', info.categories),
        ].join(' · ')}
      </p>
      <p className="text-warn">{t('restore.confirm.warning')}</p>
      {step.kind === 'confirm' && step.error ? <p className="text-red-400">{step.error}</p> : null}
    </Dialog>
  )
}

type MessageProps = { title: string; text: string; onClose?: () => void; onBack?: () => void }

/** A sentence and a way out; without `onClose` it waits (and Esc does nothing). */
export function Message({ title, text, onClose, onBack }: MessageProps) {
  return (
    <Dialog
      title={title}
      onClose={() => onClose?.()}
      footer={
        <>
          {onBack ? (
            <button className={buttonClass.secondary} onClick={onBack}>
              {t('restore.otherFile')}
            </button>
          ) : null}
          {onClose ? (
            <button className={buttonClass.primary} onClick={onClose} autoFocus>
              {t('common.close')}
            </button>
          ) : null}
        </>
      }
    >
      <p className="text-ink-200">{text}</p>
    </Dialog>
  )
}
