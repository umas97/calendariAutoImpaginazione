// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A 24-hour time field (SPEC §4, decision 12). Plain text rather than the
// native time input, which shows AM/PM when the system speaks English: "9",
// "930", "15.30" become "09:00", "09:30", "15:30" on leaving the field.
import { t } from '../i18n/it'
import { normalizeTime } from '../lib/dates'

type Props = {
  id: string
  value: string
  onChange: (value: string) => void
  invalid?: boolean
}

export function TimeInput({ id, value, onChange, invalid }: Props) {
  return (
    <input
      id={id}
      value={value}
      inputMode="numeric"
      maxLength={5}
      placeholder={t('event.timePlaceholder')}
      aria-invalid={invalid}
      onChange={(event) => onChange(event.target.value)}
      onBlur={() => {
        const clean = normalizeTime(value)
        if (clean !== value) onChange(clean)
      }}
      className={`w-20 rounded border bg-ink-900 px-2 py-1 text-sm tabular-nums outline-none focus:border-accent ${
        invalid ? 'border-red-400' : 'border-ink-600'
      }`}
    />
  )
}
