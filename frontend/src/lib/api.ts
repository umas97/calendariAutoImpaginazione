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
  if (init.body !== undefined && !headers.has('Content-Type')) {
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

export const api = {
  health: () => request<{ status: string; app: string; version: string }>('/api/health'),
  window: () => request<WindowInfo>('/api/window'),
  quit: () => request<{ detail: string }>('/api/app/quit', { method: 'POST' }),
}
