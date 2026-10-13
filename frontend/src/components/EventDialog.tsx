// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The event dialog (SPEC §9.1): the fields in the order of the SPEC, Salva and
// Annulla, and for an existing event Duplica… and Elimina. The rules live on
// the server (SPEC §7.2): the dialog sends what was typed and puts each
// message next to its field. Ctrl+Enter saves; Esc closes, asking first if
// something was changed.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ApiError, type CalendarEvent, type EventInput, type TaxonomyItem } from '../lib/api'
import { addDays, diffDays, normalizeTime } from '../lib/dates'
import { useEventActions } from '../lib/events'
import { t } from '../i18n/it'
import { ChipSelect } from './ChipSelect'
import { ConfirmDialog } from './ConfirmDialog'
import { DateField } from './DateField'
import { buttonClass, Dialog } from './Dialog'
import { PlaceInput } from './PlaceInput'
import { TimeInput } from './TimeInput'

type Props = {
  /** `null` for a new event. */
  event: CalendarEvent | null
  draft: EventInput
  groups: TaxonomyItem[]
  categories: TaxonomyItem[]
  onClose: () => void
  onDuplicate: (event: CalendarEvent) => void
  onDeleted: () => void
}

type Form = Omit<EventInput, 'end_date' | 'start_time' | 'end_time'> & {
  multi_day: boolean
  end_date: string
  start_time: string
  end_time: string
}

/** The fields that show their own message; any other goes on top. */
const FIELDS = [
  'title', 'start_date', 'end_date', 'start_time', 'end_time',
  'place', 'notes', 'group_ids', 'category_ids',
] as const
type Field = (typeof FIELDS)[number]

const toForm = (draft: EventInput): Form => ({
  ...draft,
  multi_day: draft.end_date !== null,
  end_date: draft.end_date ?? addDays(draft.start_date, 1),
  start_time: draft.start_time ?? '',
  end_time: draft.end_time ?? '',
})

const toBody = (form: Form): EventInput => {
  const { multi_day, ...rest } = form
  return {
    ...rest,
    end_date: multi_day ? form.end_date : null,
    start_time: form.all_day ? null : normalizeTime(form.start_time) || null,
    end_time: form.all_day ? null : normalizeTime(form.end_time) || null,
  }
}

/** The non-archived choices, plus the archived ones the event already has. */
const choices = (items: TaxonomyItem[], had: number[]) =>
  items.filter((item) => !item.archived || had.includes(item.id))

export function EventDialog({ event, draft, groups, categories, ...props }: Props) {
  const { create, update, remove } = useEventActions()
  const [initial] = useState(() => toForm(draft))
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({})
  const [general, setGeneral] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<'delete' | 'discard' | null>(null)
  const busy = create.isPending || update.isPending
  const dirty = JSON.stringify(toBody(form)) !== JSON.stringify(toBody(initial))

  const set = <K extends keyof Form>(key: K, value: Form[K]) => {
    setForm((old) => ({ ...old, [key]: value }))
    const field = key === 'multi_day' ? 'end_date' : key
    setErrors((old) => ({ ...old, [field]: undefined }))
  }

  const changeStart = (iso: string) => {
    // On several days the length stays: the end moves with the start.
    const length = diffDays(form.end_date, form.start_date)
    setForm((old) => ({ ...old, start_date: iso, end_date: addDays(iso, Math.max(length, 1)) }))
    setErrors((old) => ({ ...old, start_date: undefined, end_date: undefined }))
  }

  const save = () => {
    if (busy) return
    const fail = (err: Error) => {
      const fields = err instanceof ApiError ? err.fields : {}
      const shown = Object.fromEntries(FIELDS.filter((f) => f in fields).map((f) => [f, fields[f]]))
      setErrors(shown)
      setGeneral(Object.keys(shown).length ? null : err.message)
    }
    const body = toBody(form)
    if (event) update.mutate({ id: event.id, body }, { onSuccess: props.onClose, onError: fail })
    else create.mutate(body, { onSuccess: props.onClose, onError: fail })
  }

  const close = () => (dirty ? setConfirm('discard') : props.onClose())

  // Ctrl+Enter from any field; not while a confirmation is on top.
  const saveRef = useRef(save)
  saveRef.current = save
  useEffect(() => {
    if (confirm) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        saveRef.current()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirm])

  return (
    <Dialog
      title={event ? t('event.edit') : t('event.new')}
      onClose={close}
      width="max-w-2xl"
      footer={
        <>
          {event ? (
            <div className="mr-auto flex gap-2">
              <button
                className={buttonClass.secondary}
                disabled={dirty}
                title={dirty ? t('event.duplicateDirty') : undefined}
                onClick={() => props.onDuplicate(event)}
              >
                {t('event.duplicate')}
              </button>
              <button
                className={`${buttonClass.secondary} text-red-400`}
                onClick={() => setConfirm('delete')}
              >
                {t('event.delete')}
              </button>
            </div>
          ) : null}
          <span className="self-center text-xs text-ink-400">{t('event.shortcuts')}</span>
          <button className={buttonClass.secondary} onClick={close}>
            {t('common.cancel')}
          </button>
          <button className={buttonClass.primary} disabled={busy} onClick={save}>
            {busy ? t('event.saving') : t('event.save')}
          </button>
        </>
      }
    >
      {general ? <p className="text-red-400">{general}</p> : null}

      <Row label={t('event.title')} htmlFor="ev-title" error={errors.title}>
        <input
          id="ev-title"
          autoFocus
          value={form.title}
          maxLength={120}
          aria-invalid={!!errors.title}
          onChange={(e) => set('title', e.target.value)}
          className={`w-full rounded border bg-ink-900 px-2 py-1 text-sm outline-none focus:border-accent ${
            errors.title ? 'border-red-400' : 'border-ink-600'
          }`}
        />
      </Row>

      <Row label={t('event.date')} htmlFor="ev-date" error={errors.start_date ?? errors.end_date}>
        <div className="flex flex-wrap items-center gap-3">
          <DateField id="ev-date" value={form.start_date} onChange={changeStart} invalid={!!errors.start_date} />
          {form.multi_day ? (
            <>
              <span className="text-ink-300">{t('event.until')}</span>
              <DateField value={form.end_date} onChange={(iso) => set('end_date', iso)} invalid={!!errors.end_date} />
            </>
          ) : null}
          <Toggle checked={form.multi_day} onChange={(on) => set('multi_day', on)}>
            {t('event.multiDay')}
          </Toggle>
        </div>
      </Row>

      <Row label="" error={undefined}>
        <Toggle checked={form.all_day} onChange={(on) => set('all_day', on)}>
          {t('event.allDay')}
        </Toggle>
      </Row>

      {form.all_day ? null : (
        <Row label={t('event.startTime')} htmlFor="ev-start" error={errors.start_time ?? errors.end_time}>
          <div className="flex items-center gap-3">
            <TimeInput id="ev-start" value={form.start_time} onChange={(v) => set('start_time', v)} invalid={!!errors.start_time} />
            <label htmlFor="ev-end" className="text-ink-300">
              {t('event.endTime')}
            </label>
            <TimeInput id="ev-end" value={form.end_time} onChange={(v) => set('end_time', v)} invalid={!!errors.end_time} />
            <span className="text-xs text-ink-400">{t('event.endTimeHint')}</span>
          </div>
        </Row>
      )}

      <Row label={t('event.place')} htmlFor="ev-place" error={errors.place}>
        <PlaceInput id="ev-place" value={form.place} onChange={(v) => set('place', v)} invalid={!!errors.place} />
      </Row>

      <Row label={t('event.groups')} labelId="ev-groups" error={errors.group_ids}>
        <ChipSelect
          labelledBy="ev-groups"
          items={choices(groups, draft.group_ids)}
          selected={form.group_ids}
          onChange={(ids) => set('group_ids', ids)}
          invalid={!!errors.group_ids}
        />
      </Row>

      <Row label={t('event.categories')} labelId="ev-categories" error={errors.category_ids}>
        <ChipSelect
          labelledBy="ev-categories"
          withMain
          items={choices(categories, draft.category_ids)}
          selected={form.category_ids}
          onChange={(ids) => set('category_ids', ids)}
          invalid={!!errors.category_ids}
        />
      </Row>

      <Row label={t('event.notes')} htmlFor="ev-notes" error={errors.notes}>
        <textarea
          id="ev-notes"
          rows={3}
          maxLength={2000}
          value={form.notes}
          onChange={(e) => set('notes', e.target.value)}
          className={`w-full resize-y rounded border bg-ink-900 px-2 py-1 text-sm outline-none focus:border-accent ${
            errors.notes ? 'border-red-400' : 'border-ink-600'
          }`}
        />
        <p className="mt-1 text-xs text-ink-300">{t('event.notesHint')}</p>
      </Row>

      {confirm === 'discard' ? (
        <ConfirmDialog
          title={t('event.discard.title')}
          text={t('event.discard.text')}
          confirmLabel={t('event.discard.confirm')}
          cancelLabel={t('event.discard.keep')}
          danger
          onConfirm={props.onClose}
          onCancel={() => setConfirm(null)}
        />
      ) : null}
      {confirm === 'delete' && event ? (
        <ConfirmDialog
          title={t('event.delete.title', { title: event.title })}
          text={t('event.delete.text')}
          confirmLabel={t('event.delete')}
          cancelLabel={t('common.cancel')}
          danger
          busy={remove.isPending}
          error={remove.error?.message}
          onConfirm={() => remove.mutate(event.id, { onSuccess: props.onDeleted })}
          onCancel={() => setConfirm(null)}
        />
      ) : null}
    </Dialog>
  )
}

type RowProps = {
  label: string
  htmlFor?: string
  labelId?: string
  error: string | undefined
  children: ReactNode
}

function Row({ label, htmlFor, labelId, error, children }: RowProps) {
  return (
    <div className="grid grid-cols-[7rem_1fr] items-start gap-3">
      <label id={labelId} htmlFor={htmlFor} className="pt-1 text-ink-300">
        {label}
      </label>
      <div className="min-w-0">
        {children}
        {error ? <p className="mt-1 text-xs text-red-400">{error}</p> : null}
      </div>
    </div>
  )
}

function Toggle({ checked, onChange, children }: { checked: boolean; onChange: (on: boolean) => void; children: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-ink-100">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-[var(--color-accent)]"
      />
      {children}
    </label>
  )
}
