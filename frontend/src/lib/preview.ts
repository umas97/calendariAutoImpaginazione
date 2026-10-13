// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The preview (SPEC §8.7, §9.1): the very PDF of the export, as small images.
// One request per sheet, one at a time: the sheet on screen first, then the
// others in the background, so that every group gets its label ("non entra in
// un A4") before the export. The server keeps only the latest preview's images
// and a newer request makes an older one give up: the sheet on screen may
// overtake a background one, which simply comes back later. Images are copied
// into blob URLs at once, so a sheet seen once shows again instantly.
// Settings changes are applied 400 ms after the last one; background work
// waits for a quiet moment, so that a quick series of clicks rarely finds the
// server busy with a sheet nobody is looking at.
import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { api, ApiError, type ExportRequest, type SheetLayout } from './api'
import type { SheetId } from './exportForm'

export type SheetResult =
  | { status: 'done'; eventCount: number; layout: SheetLayout | null; fits: boolean; pages: string[] }
  | { status: 'error'; message: string }

export type SheetPreview = {
  /** The result for the current settings, if ready. */
  current: SheetResult | null
  /** The last result shown for this sheet, to keep on screen while the new one comes. */
  shown: SheetResult | null
  loading: boolean
}

type Wanted = { id: SheetId; key: string; body: ExportRequest }

const DEBOUNCE_MS = 400
/** Quiet time after the last change or sheet shown before the background work starts. */
const BACKGROUND_DELAY_MS = 1500
/** Results kept beyond the wanted ones, for going back to an earlier choice. */
const SPARE = 40

async function blobUrl(url: string): Promise<string> {
  const response = await fetch(url, { cache: 'no-store' })
  if (!response.ok) throw new ApiError(response.status, response.statusText)
  return URL.createObjectURL(await response.blob())
}

function release(result: SheetResult | undefined) {
  if (result?.status === 'done') result.pages.forEach((url) => URL.revokeObjectURL(url))
}

class PreviewQueue {
  private results = new Map<string, SheetResult>()
  private lastKey = new Map<SheetId, string>()
  private wanted: Wanted[] = []
  private focus: SheetId | null = null
  private running = new Set<string>()
  private paused = false
  private alive = true
  private quietUntil = 0
  private wake: number | undefined
  private version = 0
  private listeners = new Set<() => void>()
  applied = ''

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  getVersion = () => this.version

  private emit() {
    this.version++
    this.listeners.forEach((listener) => listener())
  }

  private touch() {
    this.quietUntil = Date.now() + BACKGROUND_DELAY_MS
  }

  update(wanted: Wanted[], signature: string) {
    this.touch()
    this.wanted = wanted
    this.applied = signature
    this.evict()
    this.pump()
    this.emit()
  }

  setFocus(focus: SheetId | null) {
    if (focus !== this.focus) this.touch()
    this.focus = focus
    this.pump()
  }

  setPaused(paused: boolean) {
    this.paused = paused
    this.pump()
  }

  start() {
    this.alive = true
    this.pump()
  }

  stop() {
    this.alive = false
    window.clearTimeout(this.wake)
    this.results.forEach(release)
    this.results.clear()
    this.lastKey.clear()
  }

  sheet(id: SheetId, key: string | undefined): SheetPreview {
    const last = this.lastKey.get(id)
    return {
      current: (key && this.results.get(key)) || null,
      shown: (last && this.results.get(last)) || null,
      loading: key !== undefined && this.running.has(key),
    }
  }

  private missing = (w: Wanted) => !this.results.has(w.key) && !this.running.has(w.key)

  private pump() {
    if (this.paused || !this.alive) return
    const focused = this.wanted.find((w) => w.id === this.focus)
    // The sheet on screen goes even past one being prepared: the server drops the older.
    if (focused && this.missing(focused)) return void this.run(focused)
    if (this.running.size) return
    const next = this.wanted.find(this.missing)
    if (!next) return
    const wait = this.quietUntil - Date.now()
    window.clearTimeout(this.wake)
    if (wait > 0) this.wake = window.setTimeout(() => this.pump(), wait)
    else void this.run(next)
  }

  private async run(wanted: Wanted) {
    this.running.add(wanted.key)
    this.emit()
    let result: SheetResult | null = null
    try {
      const sheet = (await api.preview(wanted.body)).sheets[0]
      const pages = await Promise.all(sheet.pages.map(blobUrl))
      result = {
        status: 'done',
        eventCount: sheet.event_count,
        layout: sheet.layout,
        fits: sheet.fits,
        pages,
      }
    } catch (error) {
      // Overtaken by a newer preview (or its images already gone): it will be asked again.
      const overtaken = error instanceof ApiError && (error.code === 'superseded' || error.status === 404)
      if (!overtaken) result = { status: 'error', message: (error as Error).message }
    }
    this.running.delete(wanted.key)
    if (wanted.id === this.focus) this.touch()
    if (result && this.alive) {
      release(this.results.get(wanted.key))
      this.results.set(wanted.key, result)
      this.lastKey.set(wanted.id, wanted.key)
    } else {
      release(result ?? undefined)
    }
    this.emit()
    this.pump()
  }

  /** Forget the oldest results nobody wants or shows any more. */
  private evict() {
    const keep = new Set([...this.wanted.map((w) => w.key), ...this.lastKey.values()])
    const spare = [...this.results.keys()].filter((key) => !keep.has(key))
    for (const key of spare.slice(0, Math.max(0, spare.length - SPARE))) {
      release(this.results.get(key))
      this.results.delete(key)
    }
  }
}

/**
 * Previews for `requests`, one per sheet. `extra` is part of every key: what
 * changes the sheets without being in the request (the parish name and logo).
 */
export function usePreview(
  requests: { id: SheetId; body: ExportRequest }[],
  extra: string,
  focus: SheetId | null,
  paused: boolean,
) {
  const [queue] = useState(() => new PreviewQueue())
  useSyncExternalStore(queue.subscribe, queue.getVersion)

  const wanted = useMemo(
    () => requests.map((r) => ({ ...r, key: `${JSON.stringify(r.body)}|${extra}` })),
    [requests, extra],
  )
  const signature = wanted.map((w) => w.key).join('\n')

  useEffect(() => {
    queue.start()
    return () => queue.stop()
  }, [queue])
  useEffect(() => {
    const timer = window.setTimeout(() => queue.update(wanted, signature), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
    // `signature` says everything `wanted` does.
  }, [queue, signature])
  useEffect(() => queue.setFocus(focus), [queue, focus])
  useEffect(() => queue.setPaused(paused), [queue, paused])

  const keys = new Map(wanted.map((w) => [w.id, w.key]))
  return {
    sheet: (id: SheetId) => queue.sheet(id, keys.get(id)),
    /** Settings changed and the 400 ms have not passed yet. */
    waiting: signature !== queue.applied,
  }
}
