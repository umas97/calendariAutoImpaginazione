// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The one place that talks to the server. Errors arrive as
// `{"error": {"code", "message", "field"?, "errors"?}}`: the message is an
// Italian sentence written for a person and the interface shows it as it is,
// because only the server knows *which* field was wrong. `fields` maps each
// wrong field to its message, for the dialogs. (`detail` is what the scaffold's
// own refusals still send.)
import { t } from '../i18n/it'

export type FieldErrors = Record<string, string>

type ErrorBody = {
  error?: {
    code?: string
    message?: string
    field?: string
    errors?: { field: string | null; message: string }[]
    [extra: string]: unknown
  }
  detail?: string
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code: string = '',
    readonly fields: FieldErrors = {},
    readonly extra: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function toApiError(status: number, fallback: string, body: ErrorBody): ApiError {
  const error = body.error
  if (!error) return new ApiError(status, body.detail ?? fallback)
  const fields: FieldErrors = {}
  for (const item of error.errors ?? []) {
    if (item.field && !(item.field in fields)) fields[item.field] = item.message
  }
  if (error.field && !(error.field in fields)) fields[error.field] = error.message ?? fallback
  const { code = '', message = fallback, field: _f, errors: _e, ...extra } = error
  return new ApiError(status, message, code, fields, extra)
}

export type WindowInfo = {
  mode: 'app' | 'tab' | 'webview' | 'none'
  note?: string | null
  can_quit: boolean
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  // A FormData body (the logo) sets its own multipart type.
  if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  let response: Response
  try {
    response = await fetch(path, { ...init, headers })
  } catch {
    throw new ApiError(0, t('error.network'))
  }
  if (!response.ok) {
    let body: ErrorBody = {}
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      // not JSON: keep the status text
    }
    throw toApiError(response.status, response.statusText, body)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Groups and categories share one shape and one set of routes (SPEC §6). */
export type Kind = 'groups' | 'categories'

export type Group = {
  id: number
  name: string
  position: number
  archived: boolean
  event_count: number
}

export type Category = Group & { color: string }

export type TaxonomyItem = Group & { color?: string }

export type ItemPatch = { name?: string; color?: string; archived?: boolean }

export type OrphanChoice = { orphans: 'delete' } | { orphans: 'reassign'; to: number }

/** An event as the server stores it (SPEC §7.1): wall-clock dates and times. */
export type EventInput = {
  title: string
  start_date: string
  end_date: string | null
  all_day: boolean
  start_time: string | null
  end_time: string | null
  place: string
  notes: string
  group_ids: number[]
  /** In the user's order: the first is the main category. */
  category_ids: number[]
}

export type CalendarEvent = EventInput & { id: number; created_at: string; updated_at: string }

export type CalendarView = 'month' | 'week' | 'list'

/** `null` means every group (or category), including the ones created later. */
export type CalendarFilters = { group_ids: number[] | null; category_ids: number[] | null }

export type ExportMode = 'per_group' | 'single_pdf' | 'combined'
export type ExportFormat = 'pdf' | 'png'
export type Dpi = 150 | 200 | 300
export type Period = { from: string; to: string }
export type GroupSelection = { group_id: number; category_ids: number[] }

/** The contract of every export, preview and count (SPEC §8.1). */
export type ExportRequest = {
  period: Period
  mode: ExportMode
  formats: ExportFormat[]
  dpi: Dpi
  selections: GroupSelection[]
  output_dir?: string | null
  /** Groups laid out over several pages instead of one sheet ("Esporta su più pagine"). */
  multipage?: number[]
}

/** The last choices of the Export tab; `category_ids: null` means every category. */
export type ExportLast = {
  period: Period | null
  mode: ExportMode
  formats: ExportFormat[]
  dpi: Dpi
  selections: { group_id: number; category_ids: number[] | null }[]
  /** `null`: the default folder. */
  output_dir: string | null
}

export type ShortcutKey = 'this_month' | 'next_month' | 'next_3_months' | 'pastoral_year'

export type ExportOptions = {
  shortcuts: Record<ShortcutKey, Period>
  default_dir: string
  home: string
  busy: boolean
}

export type ExportCounts = { groups: Record<string, number>; combined: number }

export type SheetLayout = { columns: number; font_pt: number; multipage: boolean }

export type PreviewSheet = {
  group_id: number | null
  title: string
  event_count: number
  layout: SheetLayout | null
  fits: boolean
  /** Image URLs, valid until the next preview request. */
  pages: string[]
}

export type SkippedSheet = {
  group_id: number | null
  group: string
  reason: 'empty' | 'too_big' | 'error'
  message: string
  events: number
}

export type ExportJob = {
  id: string
  status: 'running' | 'done' | 'failed' | 'cancelled'
  total: number
  done: number
  folder: string | null
  files: string[]
  skipped: SkippedSheet[]
  message: string | null
}

export type Parish = {
  name: string
  logo: { mime: string; bytes: number; updated_at: string } | null
}

export type FolderListing = {
  path: string
  parent: string | null
  home: string
  folders: { name: string; path: string }[]
}

export type Settings = {
  'calendar.view': CalendarView
  'calendar.filters': CalendarFilters
  'export.last': ExportLast | null
  'parish.name': string
}

const json = (body: unknown) => JSON.stringify(body)

export const api = {
  health: () => request<{ status: string; app: string; version: string }>('/api/health'),
  window: () => request<WindowInfo>('/api/window'),
  quit: () => request<{ detail: string }>('/api/app/quit', { method: 'POST' }),

  /** Archived items included: the interface filters, so reordering sees them all. */
  items: (kind: Kind) => request<TaxonomyItem[]>(`/api/${kind}?include_archived=true`),
  createItem: (kind: Kind, name: string) =>
    request<TaxonomyItem>(`/api/${kind}`, { method: 'POST', body: json({ name }) }),
  updateItem: (kind: Kind, id: number, patch: ItemPatch) =>
    request<TaxonomyItem>(`/api/${kind}/${id}`, { method: 'PATCH', body: json(patch) }),
  reorderItems: (kind: Kind, ids: number[]) =>
    request<void>(`/api/${kind}/reorder`, { method: 'POST', body: json({ ids }) }),
  itemUsage: (kind: Kind, id: number) =>
    request<{ events: number; orphans: number }>(`/api/${kind}/${id}/usage`),
  deleteItem: (kind: Kind, id: number, choice?: OrphanChoice) => {
    const params = new URLSearchParams()
    if (choice) params.set('orphans', choice.orphans)
    if (choice?.orphans === 'reassign') params.set('to', String(choice.to))
    const query = params.size ? `?${params}` : ''
    return request<void>(`/api/${kind}/${id}${query}`, { method: 'DELETE' })
  },
  palette: () => request<string[]>('/api/categories/palette'),

  events: (from: string, to: string) =>
    request<CalendarEvent[]>(`/api/events?${new URLSearchParams({ from, to })}`),
  createEvent: (body: EventInput) =>
    request<CalendarEvent>('/api/events', { method: 'POST', body: json(body) }),
  updateEvent: (id: number, body: EventInput) =>
    request<CalendarEvent>(`/api/events/${id}`, { method: 'PUT', body: json(body) }),
  deleteEvent: (id: number) => request<void>(`/api/events/${id}`, { method: 'DELETE' }),
  duplicateEvent: (id: number, dates: string[]) =>
    request<{ ids: number[] }>(`/api/events/${id}/duplicate`, {
      method: 'POST',
      body: json({ dates }),
    }),
  places: (q: string) => request<string[]>(`/api/places?${new URLSearchParams({ q })}`),

  settings: () => request<Settings>('/api/settings'),
  putSetting: <K extends keyof Settings>(key: K, value: Settings[K]) =>
    request<{ key: K; value: Settings[K] }>(`/api/settings/${key}`, { method: 'PUT', body: json({ value }) }),

  parish: () => request<Parish>('/api/parish'),
  setParishName: (name: string) => request<Parish>('/api/parish', { method: 'PUT', body: json({ name }) }),
  uploadLogo: (file: File) => {
    const body = new FormData()
    body.append('logo', file)
    return request<Parish>('/api/parish/logo', { method: 'POST', body })
  },
  removeLogo: () => request<void>('/api/parish/logo', { method: 'DELETE' }),

  folders: (path: string, hidden: boolean) =>
    request<FolderListing>(`/api/folders?${new URLSearchParams({ path, hidden: hidden ? '1' : '0' })}`),
  createFolder: (path: string, name: string) =>
    request<{ path: string }>('/api/folders', { method: 'POST', body: json({ path, name }) }),
  openFolder: (path: string) =>
    request<{ path: string }>('/api/folders/open', { method: 'POST', body: json({ path }) }),

  exportOptions: () => request<ExportOptions>('/api/export/options'),
  exportCounts: (body: ExportRequest & { included: number[] }) =>
    request<ExportCounts>('/api/export/counts', { method: 'POST', body: json(body) }),
  preview: (body: ExportRequest) =>
    request<{ generation: number; sheets: PreviewSheet[] }>('/api/export/preview', {
      method: 'POST',
      body: json(body),
    }),
  startExport: (body: ExportRequest) =>
    request<ExportJob>('/api/export', { method: 'POST', body: json(body) }),
  exportJob: (id: string) => request<ExportJob>(`/api/export/jobs/${id}`),
}
