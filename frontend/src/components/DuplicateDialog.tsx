// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Duplica…" (SPEC §7.4): pick any number of dates, up to 100, in a small month;
// one copy per date, in one transaction on the server. This is how a weekly
// meeting is entered: there are no recurrence rules (SPEC §4, decision 1).
import { useState } from 'react'
import type { CalendarEvent } from '../lib/api'
import { useEventActions } from '../lib/events'
import { longDate } from '../lib/dates'
import { plural, t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'
import { MiniMonth } from './MiniMonth'

const MAX_DATES = 100

type Props = {
  event: CalendarEvent
  onClose: () => void
  onDone: (created: number) => void
}

export function DuplicateDialog({ event, onClose, onDone }: Props) {
  const { duplicate } = useEventActions()
  const [dates, setDates] = useState<string[]>([])
  const full = dates.length >= MAX_DATES

  const toggle = (iso: string) => {
    if (dates.includes(iso)) setDates(dates.filter((each) => each !== iso))
    else if (!full) setDates([...dates, iso].sort())
  }

  const submit = () =>
    duplicate.mutate(
      { id: event.id, dates },
      { onSuccess: (answer) => onDone(answer.ids.length) },
    )

  return (
    <Dialog
      title={t('duplicate.title', { title: event.title })}
      onClose={onClose}
      width="max-w-xl"
      footer={
        <>
          <button className={buttonClass.secondary} onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button
            className={buttonClass.primary}
            disabled={dates.length === 0 || duplicate.isPending}
            onClick={submit}
          >
            {duplicate.isPending ? t('duplicate.working') : t('duplicate.confirm')}
          </button>
        </>
      }
    >
      <p className="text-ink-300">{t('duplicate.hint')}</p>
      <div className="flex gap-5">
        <MiniMonth
          initial={event.start_date}
          isSelected={(iso) => dates.includes(iso)}
          onPick={toggle}
          marked={event.start_date}
          markedLabel={t('duplicate.original')}
        />
        <ul className="max-h-72 min-w-0 flex-1 space-y-0.5 overflow-auto text-ink-200">
          {dates.map((iso) => (
            <li key={iso} className="flex items-center justify-between gap-2">
              <span>{longDate(iso)}</span>
              <button
                type="button"
                aria-label={t('duplicate.remove')}
                title={t('duplicate.remove')}
                onClick={() => toggle(iso)}
                className="rounded px-1.5 text-ink-400 hover:bg-ink-700 hover:text-ink-50"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex items-center gap-3">
        <p className="font-medium text-ink-50">
          {dates.length === 0 ? t('duplicate.count.zero') : plural('duplicate.count', dates.length)}
        </p>
        {dates.length > 0 ? (
          <button type="button" onClick={() => setDates([])} className="text-accent hover:underline">
            {t('duplicate.clear')}
          </button>
        ) : null}
      </div>
      {full ? <p className="text-warn">{t('duplicate.limit', { max: MAX_DATES })}</p> : null}
      {duplicate.error ? <p className="text-red-400">{duplicate.error.message}</p> : null}
    </Dialog>
  )
}
