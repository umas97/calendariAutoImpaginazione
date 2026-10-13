// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Chips to choose several groups or categories (SPEC §9.1, event dialog). The
// selection keeps the order of the clicks: for categories the first one is the
// main one (its colour paints the event), marked with a star; clicking the
// star of another selected chip makes that one the main.
import type { TaxonomyItem } from '../lib/api'
import { t } from '../i18n/it'

type Props = {
  /** The choices, already in the user's order (archived ones only if selected). */
  items: TaxonomyItem[]
  selected: number[]
  onChange: (ids: number[]) => void
  /** Categories: colour dots and the main-category star. */
  withMain?: boolean
  invalid?: boolean
  labelledBy: string
}

export function ChipSelect({ items, selected, onChange, withMain, invalid, labelledBy }: Props) {
  const toggle = (id: number) =>
    onChange(selected.includes(id) ? selected.filter((each) => each !== id) : [...selected, id])
  const makeMain = (id: number) => onChange([id, ...selected.filter((each) => each !== id)])

  return (
    <div
      role="group"
      aria-labelledby={labelledBy}
      className={`flex flex-wrap gap-1.5 rounded ${invalid ? 'outline outline-1 outline-offset-2 outline-red-400' : ''}`}
    >
      {items.map((item) => {
        const on = selected.includes(item.id)
        const main = withMain && on && selected[0] === item.id
        return (
          <span
            key={item.id}
            className={`inline-flex items-center rounded-full border text-sm ${
              on ? 'border-accent bg-accent/15 text-ink-50' : 'border-ink-600 text-ink-200'
            }`}
          >
            <button
              type="button"
              aria-pressed={on}
              onClick={() => toggle(item.id)}
              className="inline-flex items-center gap-1.5 rounded-full py-0.5 pr-2.5 pl-2.5 hover:bg-ink-700/60"
            >
              {item.color ? (
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
              ) : null}
              {item.name}
              {item.archived ? (
                <span className="text-xs text-ink-300">({t('event.archived')})</span>
              ) : null}
            </button>
            {withMain && on ? (
              <button
                type="button"
                aria-pressed={main}
                title={main ? t('event.mainCategory') : t('event.makeMain')}
                aria-label={main ? t('event.mainCategory') : t('event.makeMain')}
                onClick={() => makeMain(item.id)}
                className={`-ml-1.5 rounded-full py-0.5 pr-2 pl-1 ${
                  main ? 'text-amber-300' : 'text-ink-400 hover:text-amber-200'
                }`}
              >
                {main ? '★' : '☆'}
              </button>
            ) : null}
          </span>
        )
      })}
    </div>
  )
}
