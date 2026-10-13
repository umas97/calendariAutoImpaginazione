// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The period of the export, free (SPEC §4, decision 3), with the shortcuts of
// SPEC §9.1. The shortcuts come from the server, which knows "today" and the
// pastoral year the same way the sheets do.
import type { Period, ShortcutKey } from '../lib/api'
import { t } from '../i18n/it'
import { DateField } from './DateField'

const SHORTCUTS: ShortcutKey[] = ['this_month', 'next_month', 'next_3_months', 'pastoral_year']

type Props = {
  period: Period
  shortcuts: Record<ShortcutKey, Period>
  onChange: (period: Period) => void
  /** The server's objection, if any (a period over 400 days). */
  error?: string
}

export function ExportPeriod({ period, shortcuts, onChange, error }: Props) {
  const reversed = period.to < period.from
  const message = reversed ? t('export.period.reversed') : error
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <label htmlFor="export-from" className="text-ink-300">
          {t('export.period.from')}
        </label>
        <DateField id="export-from" value={period.from} onChange={(from) => onChange({ ...period, from })} />
        <label htmlFor="export-to" className="text-ink-300">
          {t('export.period.to')}
        </label>
        <DateField
          id="export-to"
          value={period.to}
          invalid={Boolean(message)}
          onChange={(to) => onChange({ ...period, to })}
        />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {SHORTCUTS.map((key) => {
          const range = shortcuts[key]
          const on = range.from === period.from && range.to === period.to
          return (
            <button
              key={key}
              type="button"
              aria-pressed={on}
              onClick={() => onChange(range)}
              className={`rounded-full border px-2.5 py-0.5 text-xs ${
                on ? 'border-accent bg-accent/15 text-ink-50' : 'border-ink-600 text-ink-200 hover:bg-ink-700'
              }`}
            >
              {t(`export.period.${key}`)}
            </button>
          )
        })}
      </div>
      {message ? <p className="text-sm text-red-400">{message}</p> : null}
    </div>
  )
}
