// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Where the export goes (SPEC §9.1): the folder, "Sfoglia…" for the picker,
// and the default (`~/Documenti/calendariAutoImpaginazione/`, created by the first
// export) one click away.
import { useState } from 'react'
import { t } from '../i18n/it'
import { buttonClass } from './Dialog'
import { FolderBrowser, tildePath } from './FolderBrowser'

type Props = {
  /** `null`: the default folder. */
  value: string | null
  defaultDir: string
  home: string
  onChange: (path: string | null) => void
  error?: string
}

export function FolderField({ value, defaultDir, home, onChange, error }: Props) {
  const [browsing, setBrowsing] = useState(false)
  const path = value ?? defaultDir
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <p
          title={path}
          className={`min-w-0 flex-1 truncate rounded border bg-ink-900 px-2 py-1 font-mono text-xs ${
            error ? 'border-red-400' : 'border-ink-600'
          }`}
        >
          {tildePath(path, home)}
        </p>
        <button type="button" className={buttonClass.secondary} onClick={() => setBrowsing(true)}>
          {t('export.folder.browse')}
        </button>
      </div>
      {value !== null && value !== defaultDir ? (
        <button type="button" className="rounded px-1 text-xs text-accent hover:bg-ink-700" onClick={() => onChange(null)}>
          {t('export.folder.useDefault')}
        </button>
      ) : null}
      {error ? <p className="text-sm text-red-400">{error}</p> : <p className="text-xs text-ink-300">{t('export.folder.hint')}</p>}
      {browsing ? (
        <FolderBrowser
          initial={path}
          home={home}
          onClose={() => setBrowsing(false)}
          onChoose={(chosen) => {
            setBrowsing(false)
            onChange(chosen === defaultDir ? null : chosen)
          }}
        />
      ) : null}
    </div>
  )
}
