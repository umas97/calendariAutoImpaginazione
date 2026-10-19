// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The calendar title as a button (SPEC §9.1): it opens the year with its twelve
// months, ‹ › change the year, a click on a month goes there. Faster than the
// arrows for months or years away; the month on screen is filled, today's ringed.
import { useState } from 'react'
import { t } from '../i18n/it'
import { monthName, today, type IsoDate } from '../lib/dates'
import { Popover } from './Popover'

type Props = {
  title: string
  /** A day of the period on screen: the panel opens on its year and marks its month. */
  current: IsoDate
  onPick: (first: IsoDate) => void
}

export function MonthJump({ title, current, onPick }: Props) {
  return (
    <Popover
      label={t('calendar.jump')}
      align="start"
      trigger={
        <>
          {title}
          <span aria-hidden className="ml-1.5 text-sm text-ink-300">
            ▾
          </span>
        </>
      }
      triggerClassName="min-w-48 rounded-md px-2 py-0.5 text-left text-lg font-semibold text-ink-50 hover:bg-ink-700"
    >
      {(close) => (
        <MonthGrid
          current={current}
          onPick={(first) => {
            close()
            onPick(first)
          }}
        />
      )}
    </Popover>
  )
}

function MonthGrid({ current, onPick }: { current: IsoDate; onPick: (first: IsoDate) => void }) {
  const [year, setYear] = useState(() => Number(current.slice(0, 4)))
  const shown = current.slice(0, 7)
  const now = today().slice(0, 7)

  return (
    <div className="w-72 select-none px-2 py-1">
      <div className="mb-1 flex items-center justify-between">
        <YearButton label={t('calendar.jump.prevYear')} onClick={() => setYear(year - 1)}>
          ‹
        </YearButton>
        <span className="text-sm font-medium tabular-nums text-ink-50">{year}</span>
        <YearButton label={t('calendar.jump.nextYear')} onClick={() => setYear(year + 1)}>
          ›
        </YearButton>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {Array.from({ length: 12 }, (_, month0) => {
          const month = `${year}-${String(month0 + 1).padStart(2, '0')}`
          const selected = month === shown
          return (
            <button
              key={month0}
              type="button"
              aria-pressed={selected}
              onClick={() => onPick(`${month}-01`)}
              className={`h-9 rounded text-sm ${
                selected ? 'bg-accent font-semibold text-ink-950' : 'text-ink-100 hover:bg-ink-700'
              } ${month === now && !selected ? 'ring-1 ring-accent ring-inset' : ''}`}
            >
              {monthName(month0)}
            </button>
          )
        })}
      </div>
    </div>
  )
}

type YearButtonProps = { label: string; onClick: () => void; children: string }

function YearButton({ label, onClick, children }: YearButtonProps) {
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
