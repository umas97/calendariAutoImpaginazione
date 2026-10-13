// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dates and times as the program keeps them: wall-clock values without a time
// zone (SPEC §4, decision 11), `YYYY-MM-DD` and `HH:MM`. Where a `Date` is
// unavoidable (FullCalendar) it carries the wall clock in its UTC fields, so no
// daylight-saving change can move anything. Names come from the i18n table.
import { t } from '../i18n/it'

export type IsoDate = string

const DAY_MS = 86_400_000
const WEEKDAYS = t('date.weekdays').split(' ')
const MONTHS = t('date.months').split(' ')
const SEPARATOR = t('date.rangeSeparator')

const pad = (n: number) => String(n).padStart(2, '0')

/** The date in the UTC fields of `date`. */
export const isoOf = (date: Date): IsoDate => date.toISOString().slice(0, 10)

/** The `HH:MM` in the UTC fields of `date`. */
export const timeOf = (date: Date): string => date.toISOString().slice(11, 16)

export const dateOf = (iso: IsoDate): Date => new Date(`${iso}T00:00:00Z`)

export const addDays = (iso: IsoDate, days: number): IsoDate =>
  isoOf(new Date(dateOf(iso).getTime() + days * DAY_MS))

/** Whole days from `b` to `a`. */
export const diffDays = (a: IsoDate, b: IsoDate): number =>
  Math.round((dateOf(a).getTime() - dateOf(b).getTime()) / DAY_MS)

/** The first day of the month `delta` months away from the month of `iso`. */
export function shiftMonth(iso: IsoDate, delta: number): IsoDate {
  const [y, m] = iso.split('-').map(Number)
  const index = y * 12 + (m - 1) + delta
  return `${Math.floor(index / 12)}-${pad((index % 12) + 1)}-01`
}

/** The computer's wall clock now, as `YYYY-MM-DDTHH:MM:SS`. */
export function nowWallClock(): string {
  const d = new Date()
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}

export const today = (): IsoDate => nowWallClock().slice(0, 10)

/** 0 for Monday … 6 for Sunday. */
export const weekday = (iso: IsoDate): number => (dateOf(iso).getUTCDay() + 6) % 7

export const weekdayName = (index: number): string => WEEKDAYS[index]

export const monthName = (month0: number): string => MONTHS[month0]

/** `ottobre 2026`. */
export const monthTitle = (year: number, month0: number): string =>
  `${MONTHS[month0]} ${year}`

const parts = (iso: IsoDate) => {
  const [y, m, d] = iso.split('-').map(Number)
  return { year: y, month0: m - 1, day: d }
}

/** `sab 18 ottobre 2026`. */
export function longDate(iso: IsoDate): string {
  const { year, month0, day } = parts(iso)
  return `${WEEKDAYS[weekday(iso)]} ${day} ${MONTHS[month0]} ${year}`
}

/** `mar 13 ottobre 2026, 09:30`, for a timestamp from the server (`2026-10-13T09:30:00`). */
export const longDateTime = (stamp: string): string => `${longDate(stamp.slice(0, 10))}, ${stamp.slice(11, 16)}`

/** `12 – 18 ottobre 2026`, `28 settembre – 4 ottobre 2026`, `29 dicembre 2025 – 4 gennaio 2026`. */
export function rangeTitle(first: IsoDate, last: IsoDate): string {
  const a = parts(first)
  const b = parts(last)
  const end = `${b.day} ${MONTHS[b.month0]} ${b.year}`
  if (a.year !== b.year) return `${a.day} ${MONTHS[a.month0]} ${a.year}${SEPARATOR}${end}`
  if (a.month0 !== b.month0) return `${a.day} ${MONTHS[a.month0]}${SEPARATOR}${end}`
  return `${a.day}${SEPARATOR}${end}`
}

/** `sab 18 ottobre 2026`, or a range of them for an event on several days. */
export function dateSpan(first: IsoDate, last: IsoDate | null): string {
  if (!last || last === first) return longDate(first)
  return `${longDate(first)}${SEPARATOR}${longDate(last)}`
}

/** `15:00 – 16:30`, or `ore 15:00` when there is no end. */
export function timeSpan(start: string, end: string | null): string {
  return end ? `${start}${SEPARATOR}${end}` : t('time.at', { time: start })
}

/**
 * What the user typed in a time field, as `HH:MM` if it can be read as one:
 * `9` → `09:00`, `930` → `09:30`, `15.30` → `15:30`. Anything else is returned
 * as typed, and the server says what is wrong with it.
 */
export function normalizeTime(text: string): string {
  const raw = text.trim()
  const match = /^(\d{1,2})(?:[:.,\s]?(\d{2}))?$/.exec(raw)
  if (!match) return raw
  const hours = Number(match[1])
  const minutes = Number(match[2] ?? 0)
  if (hours > 23 || minutes > 59) return raw
  return `${pad(hours)}:${pad(minutes)}`
}
