// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The bar over the calendar (SPEC §9.1): ‹ Oggi ›, the title, Mese / Settimana
// / Elenco, the two filters and "+ Nuovo evento" -- or, while there is no
// group or no category, the box that sends the user to create them (the
// filters would have nothing to offer then).
import { Link } from 'react-router-dom'
import type { CalendarFilters, CalendarView, TaxonomyItem } from '../lib/api'
import { t, type MessageKey } from '../i18n/it'
import { FilterMenu } from './FilterMenu'

type Props = {
  title: string
  view: CalendarView
  onView: (view: CalendarView) => void
  onPrev: () => void
  onToday: () => void
  onNext: () => void
  groups: TaxonomyItem[]
  categories: TaxonomyItem[]
  filters: CalendarFilters
  onFilters: (filters: CalendarFilters) => void
  canCreate: boolean
  onNew: () => void
}

const VIEWS: { view: CalendarView; label: MessageKey }[] = [
  { view: 'month', label: 'calendar.view.month' },
  { view: 'week', label: 'calendar.view.week' },
  { view: 'list', label: 'calendar.view.list' },
]

const navClass = 'rounded-md border border-ink-600 px-2.5 py-1 text-sm hover:bg-ink-700'

export function CalendarToolbar(props: Props) {
  const { filters, onFilters } = props
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-ink-700 px-4 py-2">
      <div className="flex items-center gap-1">
        <button type="button" className={navClass} onClick={props.onPrev} aria-label={t('calendar.prev')} title={t('calendar.prev')}>
          ‹
        </button>
        <button type="button" className={navClass} onClick={props.onToday}>
          {t('calendar.today')}
        </button>
        <button type="button" className={navClass} onClick={props.onNext} aria-label={t('calendar.next')} title={t('calendar.next')}>
          ›
        </button>
      </div>
      <h2 className="min-w-48 text-lg font-semibold text-ink-50">{props.title}</h2>

      <div role="group" className="flex overflow-hidden rounded-md border border-ink-600">
        {VIEWS.map(({ view, label }) => (
          <button
            key={view}
            type="button"
            aria-pressed={props.view === view}
            onClick={() => props.onView(view)}
            className={`px-3 py-1 text-sm ${
              props.view === view ? 'bg-ink-600 font-medium text-ink-50' : 'text-ink-200 hover:bg-ink-700'
            }`}
          >
            {t(label)}
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2">
        {props.canCreate ? (
          <>
            <FilterMenu
              kind="groups"
              items={props.groups}
              selected={filters.group_ids}
              onChange={(ids) => onFilters({ ...filters, group_ids: ids })}
            />
            <FilterMenu
              kind="categories"
              items={props.categories}
              selected={filters.category_ids}
              onChange={(ids) => onFilters({ ...filters, category_ids: ids })}
            />
            <button
              type="button"
              onClick={props.onNew}
              className="rounded-md bg-accent px-3 py-1 text-sm font-medium text-ink-950 hover:brightness-110"
            >
              {t('calendar.new')}
            </button>
          </>
        ) : (
          <div className="flex items-center gap-3 rounded-md border border-warn/60 px-3 py-1 text-sm text-ink-100">
            <span>{t('calendar.empty.text')}</span>
            <Link to="/gruppi" className="font-medium text-accent hover:underline">
              {t('calendar.empty.action')}
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
