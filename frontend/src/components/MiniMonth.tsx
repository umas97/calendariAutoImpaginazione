// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A small month to pick dates in: one date for the event's date field, many for
// "Duplica…" (SPEC §7.4). Monday first, today ringed; the owner decides what a
// click means and which days are selected.
import { useState } from 'react'
import { t } from '../i18n/it'
import { addDays, monthTitle, shiftMonth, today, weekday, weekdayName, type IsoDate } from '../lib/dates'

type Props = {
  /** The month shown first: the one containing this date. */
  initial: IsoDate
  isSelected: (iso: IsoDate) => boolean
  onPick: (iso: IsoDate) => void
  /** A day to mark without selecting it (the original of a duplicate). */
  marked?: IsoDate
  markedLabel?: string
}

export function MiniMonth({ initial, isSelected, onPick, marked, markedLabel }: Props) {
  const [first, setFirst] = useState(() => shiftMonth(initial, 0))
  const now = today()
  const gridStart = addDays(first, -weekday(first))
  const days = Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
  const [year, month] = first.split('-').map(Number)

  return (
    <div className="w-64 select-none">
      <div className="mb-1 flex items-center justify-between">
        <NavButton label={t('datepicker.prev')} onClick={() => setFirst(shiftMonth(first, -1))}>
          ‹
        </NavButton>
        <span className="text-sm font-medium text-ink-50">{monthTitle(year, month - 1)}</span>
        <NavButton label={t('datepicker.next')} onClick={() => setFirst(shiftMonth(first, 1))}>
          ›
        </NavButton>
      </div>
      <div className="grid grid-cols-7 text-center text-[11px] text-ink-300">
        {Array.from({ length: 7 }, (_, i) => (
          <span key={i} className="py-1">
            {weekdayName(i)}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-0.5">
        {days.map((iso) => {
          const selected = isSelected(iso)
          const outside = iso.slice(0, 7) !== first.slice(0, 7)
          return (
            <button
              key={iso}
              type="button"
              aria-pressed={selected}
              title={iso === marked ? markedLabel : undefined}
              onClick={() => onPick(iso)}
              className={`h-8 rounded text-sm tabular-nums ${
                selected
                  ? 'bg-accent font-semibold text-ink-950'
                  : `hover:bg-ink-700 ${outside ? 'text-ink-400' : 'text-ink-100'}`
              } ${iso === now && !selected ? 'ring-1 ring-accent ring-inset' : ''} ${
                iso === marked && !selected ? 'underline decoration-2 underline-offset-4' : ''
              }`}
            >
              {Number(iso.slice(8))}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function NavButton({ label, onClick, children }: { label: string; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="rounded px-2 py-0.5 text-lg leading-none text-ink-200 hover:bg-ink-700"
    >
      {children}
    </button>
  )
}
