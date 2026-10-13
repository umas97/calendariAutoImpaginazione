// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// How an event looks inside FullCalendar, and the panel that appears over it
// (SPEC §9.1): coloured by the main category, with a small dot for each other
// category; on hover the time, place, groups, categories and the notes, which
// are seen only here and in the dialog (SPEC §7.1). Text comes from our data,
// not from FullCalendar's formatting.
import type { EventContentArg } from '@fullcalendar/core'
import type { CalendarEvent, TaxonomyItem } from '../lib/api'
import { dateSpan, timeSpan } from '../lib/dates'
import { t } from '../i18n/it'

export type Lookup = Map<number, TaxonomyItem>

export const sourceOf = (arg: { event: { extendedProps: Record<string, unknown> } }) =>
  arg.event.extendedProps.source as CalendarEvent

/** An element with classes and children (text is set with textContent: no markup). */
function el(tag: string, className: string, ...children: (Node | string | null)[]): HTMLElement {
  const node = document.createElement(tag)
  node.className = className
  for (const child of children) if (child !== null) node.append(child)
  return node
}

function dots(event: CalendarEvent, categories: Lookup): HTMLElement | null {
  const others = event.category_ids.slice(1)
  if (others.length === 0) return null
  const box = el('span', 'ml-auto flex shrink-0 gap-0.5 pl-1')
  for (const id of others) {
    const dot = el('span', 'h-2 w-2 rounded-full ring-1 ring-white/80')
    dot.style.background = categories.get(id)?.color ?? ''
    box.append(dot)
  }
  return box
}

/**
 * The inside of an event, as DOM nodes. Not JSX on purpose: FullCalendar mounts
 * React content through one portal per event, which costs a fifth of the time
 * of drawing a month with 200 events (measured); plain nodes keep the month
 * change within SPEC §9.3.
 */
export function eventContent(arg: EventContentArg, categories: Lookup): { domNodes: Node[] } {
  const event = sourceOf(arg)
  const type = arg.view.type
  let node: HTMLElement
  if (type === 'listMonth') {
    node = el(
      'span',
      'flex items-center gap-2',
      el('span', 'font-medium', event.title),
      event.place ? el('span', 'text-ink-300', event.place) : null,
      dots(event, categories),
    )
  } else if (type === 'timeGridWeek' && !event.all_day) {
    node = el(
      'div',
      'h-full overflow-hidden px-1 text-xs leading-tight',
      el('div', 'flex', el('span', 'font-semibold', event.title), dots(event, categories)),
      el('div', 'opacity-85', timeSpan(event.start_time!, event.end_time)),
      event.place ? el('div', 'truncate opacity-85', event.place) : null,
    )
  } else {
    const time = !event.all_day && arg.isStart ? event.start_time : null
    node = el(
      'div',
      'flex items-center gap-1 overflow-hidden px-1 text-xs',
      time ? el('span', 'shrink-0 tabular-nums opacity-85', time) : null,
      el('span', 'truncate font-medium', event.title),
      dots(event, categories),
    )
  }
  return { domNodes: [node] }
}

type TooltipProps = {
  event: CalendarEvent
  anchor: DOMRect
  groups: Lookup
  categories: Lookup
}

const WIDTH = 288

export function EventTooltip({ event, anchor, groups, categories }: TooltipProps) {
  const below = anchor.bottom + 220 < window.innerHeight
  const left = Math.min(Math.max(8, anchor.left), window.innerWidth - WIDTH - 8)
  const style = below
    ? { top: anchor.bottom + 6, left }
    : { bottom: window.innerHeight - anchor.top + 6, left }
  const names = (ids: number[], lookup: Lookup) => ids.map((id) => lookup.get(id)?.name ?? '?').join(', ')

  return (
    <div
      role="tooltip"
      style={{ ...style, width: WIDTH }}
      className="pointer-events-none fixed z-50 space-y-1 rounded-md border border-ink-600 bg-ink-800 px-3 py-2 text-sm text-ink-100 shadow-xl"
    >
      <p className="font-semibold text-ink-50">{event.title}</p>
      <p className="text-ink-200">{dateSpan(event.start_date, event.end_date)}</p>
      <p className="text-ink-200">
        {event.all_day ? t('calendar.allDay') : timeSpan(event.start_time!, event.end_time)}
      </p>
      {event.place ? <p className="text-ink-200">{event.place}</p> : null}
      <p>
        <span className="text-ink-300">{t('tooltip.groups')}: </span>
        {names(event.group_ids, groups)}
      </p>
      <p className="flex flex-wrap items-center gap-x-2">
        <span className="text-ink-300">{t('tooltip.categories')}:</span>
        {event.category_ids.map((id) => (
          <span key={id} className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ background: categories.get(id)?.color }} />
            {categories.get(id)?.name ?? '?'}
          </span>
        ))}
      </p>
      {event.notes ? (
        <p className="line-clamp-6 border-t border-ink-600 pt-1 whitespace-pre-line text-ink-200">
          <span className="text-ink-300">{t('tooltip.notes')}: </span>
          {event.notes}
        </p>
      ) : null}
    </div>
  )
}
