// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Events as the calendar sees them. The server answers in chronological order
// (SPEC §7.3, `chronological_key`), and FullCalendar is told to keep that order
// (`order`) instead of inventing its own: the program has one order, not two.
import { useCallback, useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { EventInput as FcEvent, EventSourceFunc } from '@fullcalendar/core'
import { api, type CalendarEvent, type CalendarFilters, type EventInput } from './api'
import { addDays, diffDays, isoOf, shiftMonth, timeOf, weekday, type IsoDate } from './dates'

const rangeKey = (from: IsoDate, to: IsoDate) => ['events', from, to] as const

/** The grids next to `[from, toExclusive)`: same view, one step back and one forward. */
function neighbours(from: IsoDate, toExclusive: IsoDate): [IsoDate, IsoDate][] {
  const days = diffDays(toExclusive, from)
  if (days === 7) return [-7, 7].map((d) => [addDays(from, d), addDays(toExclusive, d)])
  if (days === 42) {
    // A month grid always has six weeks: the middle tells which month it shows.
    const middle = addDays(from, 15)
    return [-1, 1].map((delta) => monthGrid(shiftMonth(middle, delta)))
  }
  // A list of one month.
  return [-1, 1].map((delta) => [shiftMonth(from, delta), shiftMonth(from, delta + 1)])
}

function monthGrid(first: IsoDate): [IsoDate, IsoDate] {
  const start = addDays(first, -weekday(first))
  return [start, addDays(start, 42)]
}

/**
 * The calendar's event source. A month already in the cache is handed over at
 * once, so FullCalendar draws the new grid a single time, with its events; the
 * grids before and after are fetched in advance, so going back and forth never
 * waits for the server. `deliver` turns the server's events into the calendar's
 * (filters, colours) and is read when called, so it can be a fresh closure.
 */
export function useEventSource(deliver: (events: CalendarEvent[]) => FcEvent[]): EventSourceFunc {
  const client = useQueryClient()
  const latest = useRef(deliver)
  latest.current = deliver
  return useCallback<EventSourceFunc>(
    (info, success, failure) => {
      const from = isoOf(info.start)
      const toExclusive = isoOf(info.end)
      const load = (a: IsoDate, b: IsoDate) =>
        client.fetchQuery({
          queryKey: rangeKey(a, b),
          queryFn: () => api.events(a, addDays(b, -1)),
          staleTime: Infinity, // an edit invalidates; nothing else changes the events
        })
      const cached = client.getQueryData<CalendarEvent[]>(rangeKey(from, toExclusive))
      const fresh = cached && !client.getQueryState(rangeKey(from, toExclusive))?.isInvalidated
      if (fresh) success(latest.current(cached))
      else load(from, toExclusive).then((events) => success(latest.current(events)), failure)
      for (const [a, b] of neighbours(from, toExclusive)) void load(a, b).catch(() => {})
    },
    [client],
  )
}

/** Runs `onChange` whenever an edit makes the cached events stale. */
export function useEventsInvalidated(onChange: () => void) {
  const client = useQueryClient()
  const latest = useRef(onChange)
  latest.current = onChange
  useEffect(
    () =>
      client.getQueryCache().subscribe((event) => {
        if (event.type === 'updated' && event.action.type === 'invalidate' && event.query.queryKey[0] === 'events') {
          latest.current()
        }
      }),
    [client],
  )
}

export function useEventActions() {
  const client = useQueryClient()
  // The counts on "Gruppi e categorie" change with the events.
  const refresh = () =>
    Promise.all(
      (['events', 'groups', 'categories'] as const).map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    )
  const create = useMutation({ mutationFn: api.createEvent, onSuccess: refresh })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: EventInput }) => api.updateEvent(id, body),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: api.deleteEvent, onSuccess: refresh })
  const duplicate = useMutation({
    mutationFn: ({ id, dates }: { id: number; dates: string[] }) => api.duplicateEvent(id, dates),
    onSuccess: refresh,
  })
  return { create, update, remove, duplicate }
}

export function toInput(event: CalendarEvent): EventInput {
  return {
    title: event.title,
    start_date: event.start_date,
    end_date: event.end_date,
    all_day: event.all_day,
    start_time: event.start_time,
    end_time: event.end_time,
    place: event.place,
    notes: event.notes,
    group_ids: event.group_ids,
    category_ids: event.category_ids,
  }
}

/** An event passes if it shares a group and a category with the filters (`null` = all). */
export function matchesFilters(event: CalendarEvent, filters: CalendarFilters): boolean {
  const meets = (ids: number[], wanted: number[] | null) =>
    wanted === null || ids.some((id) => wanted.includes(id))
  return meets(event.group_ids, filters.group_ids) && meets(event.category_ids, filters.category_ids)
}

/** Black or white, whichever reads better on `hex`. */
export function inkOn(hex: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luminance > 0.36 ? '#111111' : '#ffffff'
}

const FALLBACK_COLOR = '#6C757D'

/**
 * The event in FullCalendar's terms. Ends are exclusive there: an all-day event
 * ends the day after its last; a timed event on several days without an end
 * time runs to the end of its last day.
 */
export function toFullCalendar(
  event: CalendarEvent,
  order: number,
  colorOf: (categoryId: number) => string | undefined,
): FcEvent {
  const last = event.end_date ?? event.start_date
  const color = colorOf(event.category_ids[0]) ?? FALLBACK_COLOR
  let start: string
  let end: string | undefined
  if (event.all_day) {
    start = event.start_date
    end = addDays(last, 1)
  } else {
    start = `${event.start_date}T${event.start_time}`
    if (event.end_time) end = `${last}T${event.end_time}`
    else if (event.end_date) end = `${addDays(last, 1)}T00:00`
  }
  return {
    id: String(event.id),
    title: event.title,
    start,
    end,
    allDay: event.all_day,
    backgroundColor: color,
    borderColor: color,
    textColor: inkOn(color),
    extendedProps: { source: event, order },
  }
}

/**
 * `original` after being dragged to `start` (and `end`, `allDay`) as FullCalendar
 * reports them: the length in days never changes (SPEC §9.1), the times follow
 * the drop in the week view, and nothing else is touched.
 */
export function movedTo(
  original: CalendarEvent,
  start: Date,
  end: Date | null,
  allDay: boolean,
): EventInput {
  const base = toInput(original)
  const startDate = isoOf(start)
  const shift = diffDays(startDate, original.start_date)
  const endDate = original.end_date ? addDays(original.end_date, shift) : null
  if (allDay) {
    return { ...base, start_date: startDate, end_date: endDate, all_day: true, start_time: null, end_time: null }
  }
  const moved = { ...base, start_date: startDate, all_day: false, start_time: timeOf(start) }
  if (original.all_day || !original.end_time || !end) {
    return { ...moved, end_date: endDate, end_time: null }
  }
  // The drop kept the duration exactly; the end may now fall on another day.
  const endIso = isoOf(end)
  return { ...moved, end_date: endIso === startDate ? null : endIso, end_time: timeOf(end) }
}
