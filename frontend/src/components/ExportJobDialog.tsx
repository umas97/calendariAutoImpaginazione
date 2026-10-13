// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The export under way and then its summary (SPEC §8.7, §9.1): a bar that
// counts the sheets, then the files made, the groups skipped with the reason,
// "Apri cartella", and "Esporta su più pagine" for the groups that did not fit
// one page. It cannot be closed while the export runs: there is nothing to
// interrupt, and it never takes long.
import { useState } from 'react'
import { api, type ExportJob } from '../lib/api'
import { plural, t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'
import { tildePath } from './FolderBrowser'

type Props = {
  job: ExportJob
  home: string
  onClose: () => void
  /** Redo these groups over several pages; absent when that is not possible. */
  onMultipage?: (groupIds: number[]) => void
}

export function ExportJobDialog({ job, home, onClose, onMultipage }: Props) {
  const [openError, setOpenError] = useState<string | null>(null)
  const running = job.status === 'running'
  const tooBig = job.skipped.filter((s) => s.reason === 'too_big' && s.group_id !== null)
  const title = running
    ? t('job.title')
    : job.status === 'done'
      ? t('job.done')
      : job.status === 'cancelled'
        ? t('job.cancelled')
        : t('job.failed')
  const percent = job.total ? Math.round((job.done / job.total) * 100) : 0

  const openFolder = async () => {
    if (!job.folder) return
    try {
      await api.openFolder(job.folder)
      setOpenError(null)
    } catch (err) {
      setOpenError((err as Error).message)
    }
  }

  return (
    <Dialog
      title={title}
      width="max-w-lg"
      onClose={() => {
        if (!running) onClose()
      }}
      footer={
        running ? (
          <span className="text-sm text-ink-300">{t('job.wait')}</span>
        ) : (
          <>
            {job.folder && job.files.length ? (
              <button className={buttonClass.secondary} onClick={() => void openFolder()}>
                {t('job.openFolder')}
              </button>
            ) : null}
            <button className={buttonClass.primary} onClick={onClose} autoFocus>
              {t('common.close')}
            </button>
          </>
        )
      }
    >
      {running ? (
        <div className="space-y-2">
          <p className="text-ink-200">{t('job.running', { done: job.done, total: job.total })}</p>
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={job.total}
            aria-valuenow={job.done}
            className="h-2 overflow-hidden rounded-full bg-ink-700"
          >
            <div className="h-full bg-accent transition-[width] duration-300" style={{ width: `${percent}%` }} />
          </div>
        </div>
      ) : (
        <>
          {job.message ? <p className="text-red-400">{job.message}</p> : null}
          {job.folder ? (
            <p className="text-ink-200">
              <span className="text-ink-300">{t('job.folder')}: </span>
              <span className="font-mono text-xs break-all">{tildePath(job.folder, home)}</span>
            </p>
          ) : null}
          <div>
            <p className="font-medium text-ink-50">{plural('job.files', job.files.length)}</p>
            {job.files.length ? (
              <ul className="mt-1 max-h-40 overflow-y-auto rounded border border-ink-700 px-3 py-1 font-mono text-xs text-ink-200">
                {job.files.map((file) => (
                  <li key={file} className="truncate py-0.5" title={file}>
                    {file}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          {job.skipped.length ? (
            <div>
              <p className="font-medium text-ink-50">{t('job.skipped')}</p>
              <ul className="mt-1 space-y-1">
                {job.skipped.map((skip) => (
                  <li key={`${skip.group_id}-${skip.reason}`} className="flex items-start gap-2">
                    <span className={`flex-1 ${skip.reason === 'empty' ? 'text-ink-300' : 'text-red-400'}`}>
                      {skip.group}: {skip.message}
                    </span>
                    {skip.reason === 'too_big' && onMultipage && tooBig.length === 1 ? (
                      <button
                        className={`${buttonClass.secondary} shrink-0`}
                        onClick={() => onMultipage([skip.group_id!])}
                      >
                        {t('job.multipage')}
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
              {onMultipage && tooBig.length > 1 ? (
                <button
                  className={`${buttonClass.secondary} mt-2`}
                  onClick={() => onMultipage(tooBig.map((s) => s.group_id!))}
                >
                  {t('job.multipageAll')}
                </button>
              ) : null}
            </div>
          ) : null}
          {openError ? <p className="text-red-400">{openError}</p> : null}
        </>
      )}
    </Dialog>
  )
}
