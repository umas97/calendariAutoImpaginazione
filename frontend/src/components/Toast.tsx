// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A short notice at the bottom of the screen, with at most one action:
// "Evento spostato — Annulla" (SPEC §9.1). It goes away by itself; a new notice
// replaces the old one (the owner changes `id`).
import { useEffect } from 'react'
import { t } from '../i18n/it'

export type Notice = {
  id: number
  message: string
  action?: { label: string; run: () => void }
}

type Props = { notice: Notice; onDone: () => void; durationMs?: number }

export function Toast({ notice, onDone, durationMs = 8_000 }: Props) {
  useEffect(() => {
    const timer = window.setTimeout(onDone, durationMs)
    return () => window.clearTimeout(timer)
  }, [notice.id, onDone, durationMs])

  return (
    <div
      role="status"
      className="fixed bottom-5 left-1/2 z-40 flex -translate-x-1/2 items-center gap-4 rounded-md border border-ink-600 bg-ink-800 px-4 py-2 text-sm text-ink-50 shadow-xl"
    >
      <span>{notice.message}</span>
      {notice.action ? (
        <button
          type="button"
          onClick={() => {
            notice.action!.run()
            onDone()
          }}
          className="rounded px-2 py-0.5 font-medium text-accent hover:bg-ink-700"
        >
          {notice.action.label}
        </button>
      ) : null}
      <button
        type="button"
        aria-label={t('common.close')}
        title={t('common.close')}
        onClick={onDone}
        className="rounded px-1.5 text-ink-300 hover:bg-ink-700 hover:text-ink-50"
      >
        ×
      </button>
    </div>
  )
}
