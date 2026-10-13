// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The "Gruppi" and "Categorie" filters of the calendar (SPEC §9.1). `null`
// means all, including the ones created later; ticking every box gets back to
// `null`, so "all" never silently turns into "all those that existed then".
import type { Kind, TaxonomyItem } from '../lib/api'
import { t } from '../i18n/it'
import { Popover } from './Popover'

type Props = {
  kind: Kind
  /** The choices: not archived, in the user's order. */
  items: TaxonomyItem[]
  selected: number[] | null
  onChange: (ids: number[] | null) => void
}

export function FilterMenu({ kind, items, selected, onChange }: Props) {
  const isOn = (id: number) => selected === null || selected.includes(id)
  const count = selected === null ? items.length : items.filter((item) => isOn(item.id)).length
  const summary =
    selected === null || count === items.length
      ? t(`filter.${kind}.all`)
      : count === 0
        ? t(`filter.${kind}.none`)
        : t(`filter.${kind}.some`, { n: count })

  const toggle = (id: number) => {
    const next = items.filter((item) => (item.id === id ? !isOn(id) : isOn(item.id)))
    onChange(next.length === items.length ? null : next.map((item) => item.id))
  }

  return (
    <Popover
      label={t(`filter.${kind}.label`)}
      align="end"
      triggerClassName={`rounded-md border px-3 py-1 text-sm hover:bg-ink-700 ${
        selected === null ? 'border-ink-600 text-ink-200' : 'border-accent text-ink-50'
      }`}
      trigger={<span>{summary} ▾</span>}
    >
      {() => (
        <div className="max-h-[60vh] w-60 overflow-auto">
          <div className="flex gap-1 border-b border-ink-600 px-2 pb-1">
            <QuickButton onClick={() => onChange(null)}>{t('filter.selectAll')}</QuickButton>
            <QuickButton onClick={() => onChange([])}>{t('filter.selectNone')}</QuickButton>
          </div>
          {items.map((item) => (
            <label
              key={item.id}
              className="flex cursor-pointer items-center gap-2 px-3 py-1 hover:bg-ink-700"
            >
              <input
                type="checkbox"
                checked={isOn(item.id)}
                onChange={() => toggle(item.id)}
                className="h-4 w-4 accent-[var(--color-accent)]"
              />
              {item.color ? (
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: item.color }} />
              ) : null}
              <span className="truncate">{item.name}</span>
            </label>
          ))}
        </div>
      )}
    </Popover>
  )
}

function QuickButton({ onClick, children }: { onClick: () => void; children: string }) {
  return (
    <button type="button" onClick={onClick} className="rounded px-2 py-0.5 text-accent hover:bg-ink-700">
      {children}
    </button>
  )
}
