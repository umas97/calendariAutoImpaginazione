// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A date field that reads in Italian ("sab 18 ottobre 2026") whatever the
// browser's language: a button that opens the small month. The native date
// input would follow the system locale (SPEC §4, decision 12).
import { t } from '../i18n/it'
import { longDate, type IsoDate } from '../lib/dates'
import { MiniMonth } from './MiniMonth'
import { Popover } from './Popover'

type Props = {
  value: IsoDate
  onChange: (iso: IsoDate) => void
  invalid?: boolean
  id?: string
}

export function DateField({ value, onChange, invalid, id }: Props) {
  return (
    <Popover
      label={t('datepicker.choose')}
      align="start"
      triggerId={id}
      triggerClassName={`rounded border bg-ink-900 px-2 py-1 text-left text-sm hover:border-ink-400 ${
        invalid ? 'border-red-400' : 'border-ink-600'
      }`}
      trigger={<span>{longDate(value)}</span>}
    >
      {(close) => (
        <div className="px-3 py-2">
          <MiniMonth
            initial={value}
            isSelected={(iso) => iso === value}
            onPick={(iso) => {
              close()
              onChange(iso)
            }}
          />
        </div>
      )}
    </Popover>
  )
}
