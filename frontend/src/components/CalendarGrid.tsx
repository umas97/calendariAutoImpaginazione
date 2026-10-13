// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// FullCalendar, configured once (SPEC §9.1). Two choices matter:
//
// * `timeZone: 'UTC'` with `now` taken from the wall clock: the program has no
//   time zones (SPEC §4, decision 11), and in UTC no daylight-saving change can
//   shift an event by an hour.
// * `eventOrder: 'order'`, the position in the server's answer, which is
//   already in chronological order (SPEC §7.3).
//
// Every visible text is ours: names from the i18n table, times from the data.
// `handlers` must be a stable object (see `useStableHandlers`): with `memo`, a
// re-render of the page then does not hand FullCalendar new options and
// redraw every event.
import { forwardRef, memo, useMemo, useRef } from 'react'
import FullCalendar from '@fullcalendar/react'
import type {
  DatesSetArg,
  DateSelectArg,
  EventDropArg,
  EventSourceFunc,
  FormatterInput,
} from '@fullcalendar/core'
import itLocale from '@fullcalendar/core/locales/it'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import listPlugin from '@fullcalendar/list'
import timeGridPlugin from '@fullcalendar/timegrid'
import type { CalendarEvent, CalendarView } from '../lib/api'
import { isoOf, longDate, nowWallClock, timeOf, weekdayName } from '../lib/dates'
import { t } from '../i18n/it'
import { eventContent, sourceOf, type Lookup } from './EventContent'

export const FC_VIEW: Record<CalendarView, string> = {
  month: 'dayGridMonth',
  week: 'timeGridWeek',
  list: 'listMonth',
}

export type GridHandlers = {
  onDatesSet: (info: DatesSetArg) => void
  onSelect: (info: DateSelectArg) => void
  onEventClick: (event: CalendarEvent) => void
  onEventDrop: (info: EventDropArg) => void
  onHover: (event: CalendarEvent | null, anchor?: DOMRect) => void
}

type Props = {
  initialView: CalendarView
  initialDate?: string
  /** Stable: see `useEventSource`. */
  events: EventSourceFunc
  categories: Lookup
  canCreate: boolean
  slotMinTime: string
  slotMaxTime: string
  handlers: GridHandlers
}

type Arg = Parameters<Extract<FormatterInput, (arg: never) => string>>[0]

const weekdayOf = (arg: Arg) => weekdayName((arg.date.marker.getUTCDay() + 6) % 7)
const hm = (date: Date) => timeOf(date)
const formats = {
  monthHeader: ((arg: Arg) => weekdayOf(arg)) as FormatterInput,
  weekHeader: ((arg: Arg) => `${weekdayOf(arg)} ${arg.date.day}`) as FormatterInput,
  longDay: ((arg: Arg) => longDate(isoOf(arg.date.marker))) as FormatterInput,
  hour: ((arg: Arg) => hm(arg.date.marker)) as FormatterInput,
  time: ((arg: Arg) =>
    arg.end ? `${hm(arg.start.marker)}${t('date.rangeSeparator')}${hm(arg.end.marker)}` : hm(arg.date.marker)) as FormatterInput,
}

/** The first hour shown in the week, in sight of the user (SPEC §9.1). */
function scrollTime(): string {
  const hour = Number(nowWallClock().slice(11, 13))
  return hour >= 7 && hour < 23 ? `${String(hour).padStart(2, '0')}:00:00` : '08:00:00'
}

/** A stable `GridHandlers` that always calls the latest `handlers`. */
export function useStableHandlers(handlers: GridHandlers): GridHandlers {
  const latest = useRef(handlers)
  latest.current = handlers
  return useMemo(
    () => ({
      onDatesSet: (info) => latest.current.onDatesSet(info),
      onSelect: (info) => latest.current.onSelect(info),
      onEventClick: (event) => latest.current.onEventClick(event),
      onEventDrop: (info) => latest.current.onEventDrop(info),
      onHover: (event, anchor) => latest.current.onHover(event, anchor),
    }),
    [],
  )
}

export const CalendarGrid = memo(
  forwardRef<FullCalendar, Props>(function CalendarGrid(props, ref) {
    const { categories, handlers } = props

    const views = useMemo(
      () => ({
        dayGridMonth: { dayHeaderFormat: formats.monthHeader },
        timeGridWeek: { dayHeaderFormat: formats.weekHeader },
        listMonth: { listDayFormat: formats.longDay, listDaySideFormat: false as const },
      }),
      [],
    )
    const initialScroll = useMemo(scrollTime, [])

    return (
      <FullCalendar
        ref={ref}
        plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
        locale={itLocale}
        timeZone="UTC"
        now={nowWallClock}
        initialView={FC_VIEW[props.initialView]}
        initialDate={props.initialDate}
        headerToolbar={false}
        height="100%"
        firstDay={1}
        views={views}
        events={props.events}
        eventOrder="order"
        eventDisplay="block"
        dayMaxEvents
        nowIndicator
        editable
        eventDurationEditable={false}
        selectable={props.canCreate}
        unselectAuto
        slotMinTime={props.slotMinTime}
        slotMaxTime={props.slotMaxTime}
        scrollTime={initialScroll}
        slotLabelFormat={formats.hour}
        eventTimeFormat={formats.time}
        dayPopoverFormat={formats.longDay}
        allDayContent={() => t('calendar.allDay')}
        moreLinkContent={(arg) => t('calendar.more', { n: arg.num })}
        noEventsContent={() => t('calendar.noEvents')}
        eventContent={(arg) => eventContent(arg, categories)}
        datesSet={(info) => handlers.onDatesSet(info)}
        select={(info) => handlers.onSelect(info)}
        eventClick={(info) => {
          info.jsEvent.preventDefault()
          handlers.onEventClick(sourceOf(info))
        }}
        eventDrop={(info) => handlers.onEventDrop(info)}
        eventDragStart={() => handlers.onHover(null)}
        eventMouseEnter={(info) =>
          handlers.onHover(sourceOf(info), info.el.getBoundingClientRect())
        }
        eventMouseLeave={() => handlers.onHover(null)}
      />
    )
  }),
)
