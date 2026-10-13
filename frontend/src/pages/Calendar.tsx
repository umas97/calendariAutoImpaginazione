// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Calendario" (SPEC §9.1): the calendar fills the space under the bar and
// opens on today. A click on a day (or a selected slot in the week) starts a
// new event there, a click on an event edits it, dragging moves it with an
// "Annulla" for 8 seconds. View and filters are remembered (SPEC §10.2); the
// date is not: the program always opens on today. Within a session the
// position survives a visit to another tab.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type FullCalendar from '@fullcalendar/react'
import type { DateSelectArg, DatesSetArg, EventDropArg } from '@fullcalendar/core'
import type { CalendarEvent, CalendarFilters, CalendarView, EventInput, Settings, TaxonomyItem } from '../lib/api'
import { addDays, isoOf, monthTitle, rangeTitle, timeOf, today } from '../lib/dates'
import {
  matchesFilters,
  movedTo,
  toFullCalendar,
  toInput,
  useEventActions,
  useEventSource,
  useEventsInvalidated,
} from '../lib/events'
import { useSaveSetting, useSettings } from '../lib/settings'
import { useItems } from '../lib/taxonomy'
import { plural, t } from '../i18n/it'
import { CalendarGrid, FC_VIEW, useStableHandlers } from '../components/CalendarGrid'
import { CalendarToolbar } from '../components/CalendarToolbar'
import { DuplicateDialog } from '../components/DuplicateDialog'
import { EventDialog } from '../components/EventDialog'
import { EventTooltip } from '../components/EventContent'
import { Toast, type Notice } from '../components/Toast'

/** Where the calendar was, for the next visit to the tab in this session. */
let lastDate: string | undefined

export function CalendarPage() {
  const settings = useSettings()
  const groups = useItems('groups')
  const categories = useItems('categories')
  const error = settings.error ?? groups.error ?? categories.error
  if (error) return <p className="p-6 text-red-400">{error.message}</p>
  if (!settings.data || !groups.data || !categories.data) {
    return <p className="p-6 text-ink-300">{t('calendar.loading')}</p>
  }
  return <CalendarScreen settings={settings.data} groups={groups.data} categories={categories.data} />
}

type Editing = { event: CalendarEvent | null; draft: EventInput }
type Hover = { event: CalendarEvent; anchor: DOMRect }

type ScreenProps = { settings: Settings; groups: TaxonomyItem[]; categories: TaxonomyItem[] }

function CalendarScreen({ settings, groups, categories }: ScreenProps) {
  const calendar = useRef<FullCalendar>(null)
  const [initialView] = useState(settings['calendar.view'])
  const [view, setView] = useState(initialView)
  const filters = settings['calendar.filters']
  const saveView = useSaveSetting('calendar.view')
  const saveFilters = useSaveSetting('calendar.filters')
  const [title, setTitle] = useState('')
  const [editing, setEditing] = useState<Editing | null>(null)
  const [duplicating, setDuplicating] = useState<CalendarEvent | null>(null)
  const [hover, setHover] = useState<Hover | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const { update } = useEventActions()
  /** The events on screen, after the filters. */
  const [shown, setShown] = useState<CalendarEvent[]>([])

  const groupLookup = useMemo(() => new Map(groups.map((g) => [g.id, g])), [groups])
  const categoryLookup = useMemo(() => new Map(categories.map((c) => [c.id, c])), [categories])
  const activeGroups = useMemo(() => groups.filter((g) => !g.archived), [groups])
  const activeCategories = useMemo(() => categories.filter((c) => !c.archived), [categories])
  const canCreate = activeGroups.length > 0 && activeCategories.length > 0

  const source = useEventSource((events) => {
    const visible = events.filter((e) => matchesFilters(e, filters))
    setShown(visible)
    return visible.map((e, i) => toFullCalendar(e, i, (id) => categoryLookup.get(id)?.color))
  })
  const slots = useMemo(() => slotRange(shown), [shown])

  // Filters and colours are applied on delivery: a change asks for the events again
  // (from the cache, so at once), and so does an edit anywhere in the program.
  const api = () => calendar.current?.getApi()
  const mounted = useRef(false)
  useEffect(() => {
    if (mounted.current) api()?.refetchEvents()
    mounted.current = true
  }, [filters, categoryLookup])
  useEventsInvalidated(() => api()?.refetchEvents())

  const say = (message: string, action?: Notice['action']) =>
    setNotice({ id: Date.now(), message, action })
  const dismiss = useCallback(() => setNotice(null), [])

  /** A new event, with the group (or category) preselected if the filter shows only one. */
  const draft = (start_date: string, extra: Partial<EventInput> = {}): EventInput => ({
    title: '',
    start_date,
    end_date: null,
    all_day: false,
    start_time: null,
    end_time: null,
    place: '',
    notes: '',
    group_ids: onlyOne(filters.group_ids, activeGroups),
    category_ids: onlyOne(filters.category_ids, activeCategories),
    ...extra,
  })

  const handlers = useStableHandlers({
    onDatesSet: (info: DatesSetArg) => {
      const { currentStart, activeStart, activeEnd, type } = info.view
      lastDate = isoOf(currentStart)
      setTitle(
        type === FC_VIEW.week
          ? rangeTitle(isoOf(activeStart), addDays(isoOf(activeEnd), -1))
          : monthTitle(currentStart.getUTCFullYear(), currentStart.getUTCMonth()),
      )
    },
    onSelect: (info: DateSelectArg) => {
      info.view.calendar.unselect()
      if (!canCreate) return
      const start = isoOf(info.start)
      if (info.allDay) {
        const last = addDays(isoOf(info.end), -1)
        const extra = { end_date: last !== start ? last : null, all_day: info.view.type === FC_VIEW.week }
        setEditing({ event: null, draft: draft(start, extra) })
      } else {
        const end = isoOf(info.end)
        const extra = { start_time: timeOf(info.start), end_time: timeOf(info.end), end_date: end !== start ? end : null }
        setEditing({ event: null, draft: draft(start, extra) })
      }
    },
    onEventClick: (event: CalendarEvent) => {
      setHover(null)
      setEditing({ event, draft: toInput(event) })
    },
    onEventDrop: (info: EventDropArg) => {
      const original = info.event.extendedProps.source as CalendarEvent
      const body = movedTo(original, info.event.start!, info.event.end, info.event.allDay)
      const undo = () =>
        update.mutate(
          { id: original.id, body: toInput(original) },
          { onSuccess: () => say(t('calendar.undone')), onError: (err) => say(err.message) },
        )
      update.mutate(
        { id: original.id, body },
        {
          onSuccess: () => say(t('calendar.moved'), { label: t('calendar.undo'), run: undo }),
          onError: (err) => {
            info.revert()
            say(t('calendar.moveFailed', { message: err.message }))
          },
        },
      )
    },
    onHover: (event, anchor) => setHover(event && anchor ? { event, anchor } : null),
  })

  const changeView = (next: CalendarView) => {
    api()?.changeView(FC_VIEW[next])
    setView(next)
    saveView.mutate(next)
  }
  const changeFilters = (next: CalendarFilters) => saveFilters.mutate(next)
  const startNew = () => {
    const current = api()?.view
    const now = today()
    const inView = current && now >= isoOf(current.currentStart) && now < isoOf(current.currentEnd)
    setEditing({ event: null, draft: draft(inView || !current ? now : isoOf(current.currentStart)) })
  }

  return (
    <div className="flex h-full flex-col">
      <CalendarToolbar
        title={title}
        view={view}
        onView={changeView}
        onPrev={() => api()?.prev()}
        onToday={() => api()?.today()}
        onNext={() => api()?.next()}
        groups={activeGroups}
        categories={activeCategories}
        filters={filters}
        onFilters={changeFilters}
        canCreate={canCreate}
        onNew={startNew}
      />
      <div className="min-h-0 flex-1 p-2">
        <CalendarGrid
          ref={calendar}
          initialView={initialView}
          initialDate={lastDate}
          events={source}
          categories={categoryLookup}
          canCreate={canCreate}
          slotMinTime={slots.min}
          slotMaxTime={slots.max}
          handlers={handlers}
        />
      </div>

      {hover && !editing ? (
        <EventTooltip event={hover.event} anchor={hover.anchor} groups={groupLookup} categories={categoryLookup} />
      ) : null}
      {editing ? (
        <EventDialog
          event={editing.event}
          draft={editing.draft}
          groups={groups}
          categories={categories}
          onClose={() => setEditing(null)}
          onDuplicate={(event) => {
            setEditing(null)
            setDuplicating(event)
          }}
          onDeleted={() => {
            setEditing(null)
            say(t('calendar.deleted'))
          }}
        />
      ) : null}
      {duplicating ? (
        <DuplicateDialog
          event={duplicating}
          onClose={() => setDuplicating(null)}
          onDone={(created) => {
            setDuplicating(null)
            say(plural('calendar.duplicated', created))
          }}
        />
      ) : null}
      {notice ? <Toast notice={notice} onDone={dismiss} /> : null}
    </div>
  )
}

function onlyOne(ids: number[] | null, items: TaxonomyItem[]): number[] {
  return ids?.length === 1 && items.some((item) => item.id === ids[0]) ? [ids[0]] : []
}

const hourOf = (time: string) => Number(time.slice(0, 2)) + Number(time.slice(3, 5)) / 60

/**
 * The hours of the week view: 7:00-23:00 (SPEC §9.1), widened when an event
 * falls outside, so that no event is ever out of sight.
 */
function slotRange(events: CalendarEvent[]): { min: string; max: string } {
  let min = 7
  let max = 23
  for (const event of events) {
    if (event.all_day || !event.start_time) continue
    const start = hourOf(event.start_time)
    const end = event.end_time ? hourOf(event.end_time) : start + 1
    min = Math.min(min, Math.floor(start), Math.floor(end))
    max = Math.max(max, Math.ceil(start + 0.5), Math.ceil(end))
  }
  const fmt = (h: number) => `${String(Math.min(h, 24)).padStart(2, '0')}:00:00`
  return { min: fmt(min), max: fmt(max) }
}
