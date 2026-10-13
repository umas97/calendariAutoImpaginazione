// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A name that becomes a text field on click. Enter or leaving the field saves,
// Esc puts the old name back. A refusal from the server (a duplicate, an empty
// name) keeps the field open with the reason under it: the user fixes it there
// instead of finding the old name silently restored.
import { useRef, useState } from 'react'
import { t } from '../i18n/it'

type Props = {
  value: string
  /** Rejects with an Error whose message is shown to the user. */
  onSave: (name: string) => Promise<unknown>
  className?: string
}

export function InlineName({ value, onSave, className = '' }: Props) {
  const [draft, setDraft] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  // Synchronous twin of `draft !== null && !saving`: the field may report a blur
  // as it is removed after Esc or a save, through a handler with stale state.
  const editing = useRef(false)

  const start = () => {
    editing.current = true
    setDraft(value)
  }

  const stop = () => {
    editing.current = false
    setDraft(null)
    setError(null)
  }

  const save = async () => {
    if (draft === null || !editing.current) return
    if (draft.trim() === value) return stop()
    editing.current = false
    setSaving(true)
    try {
      await onSave(draft)
      stop()
    } catch (err) {
      editing.current = true
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (draft === null) {
    return (
      <button
        type="button"
        title={t('taxonomy.rename')}
        onClick={start}
        className={`min-w-0 flex-1 truncate rounded px-1.5 py-0.5 text-left hover:bg-ink-700 ${className}`}
      >
        {value}
      </button>
    )
  }

  return (
    <div className="min-w-0 flex-1">
      <input
        autoFocus
        value={draft}
        maxLength={80}
        readOnly={saving}
        aria-invalid={error !== null}
        onChange={(event) => {
          setDraft(event.target.value)
          setError(null)
        }}
        onFocus={(event) => event.target.select()}
        onBlur={() => void save()}
        onKeyDown={(event) => {
          if (event.key === 'Enter') void save()
          if (event.key === 'Escape') {
            event.preventDefault()
            stop()
          }
        }}
        className={`w-full rounded border bg-ink-900 px-1.5 py-0.5 outline-none ${
          error ? 'border-red-400' : 'border-accent'
        }`}
      />
      {error ? <p className="mt-1 text-xs text-red-400">{error}</p> : null}
    </div>
  )
}
