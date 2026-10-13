// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// One column of "Gruppi e categorie": the items in the user's order, reordered
// by dragging the handle (or with ↑ ↓ on it), and the field that adds a new one.
// The order chosen here is the order of every list and legend in the program.
// Archived items may be hidden; reordering the visible ones leaves the hidden
// ones where they were (`mergeOrder`).
import { useRef, useState, type DragEvent, type KeyboardEvent } from 'react'
import type { Kind, TaxonomyItem } from '../lib/api'
import { mergeOrder, move, useItems, useTaxonomyActions } from '../lib/taxonomy'
import { t } from '../i18n/it'
import { DeleteItemDialog } from './DeleteItemDialog'
import { TaxonomyRow } from './TaxonomyRow'

type Props = { kind: Kind; showArchived: boolean }

/** The row being dragged and the gap (0…n) it would drop into. */
type Drag = { id: number; over: number }

export function TaxonomyList({ kind, showArchived }: Props) {
  const { data: all, isPending, error } = useItems(kind)
  const { reorder } = useTaxonomyActions(kind)
  const [drag, setDrag] = useState<Drag | null>(null)
  const [deleting, setDeleting] = useState<TaxonomyItem | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const handles = useRef(new Map<number, HTMLButtonElement>())

  const visible = (all ?? []).filter((item) => showArchived || !item.archived)
  const ids = visible.map((item) => item.id)

  const commit = (next: number[]) => {
    setNotice(null)
    reorder.mutate(mergeOrder(all ?? [], next), {
      onError: (err) => setNotice(err.message),
    })
  }

  const dragStart = (item: TaxonomyItem) => (event: DragEvent<HTMLButtonElement>) => {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', item.name)
    const row = event.currentTarget.closest('li')
    if (row) event.dataTransfer.setDragImage(row, 16, row.offsetHeight / 2)
    setDrag({ id: item.id, over: ids.indexOf(item.id) })
  }

  const dragOver = (index: number) => (event: DragEvent<HTMLLIElement>) => {
    if (!drag) return // something dragged from elsewhere: not ours to take
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
    const box = event.currentTarget.getBoundingClientRect()
    const over = event.clientY < box.top + box.height / 2 ? index : index + 1
    if (over !== drag.over) setDrag({ ...drag, over })
  }

  const drop = (event: DragEvent<HTMLLIElement>) => {
    if (!drag) return
    event.preventDefault()
    const from = ids.indexOf(drag.id)
    const to = drag.over > from ? drag.over - 1 : drag.over
    setDrag(null)
    if (from !== to) commit(move(ids, from, to))
  }

  const handleKey = (index: number) => (event: KeyboardEvent<HTMLButtonElement>) => {
    const delta = event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0
    const to = index + delta
    if (delta === 0 || to < 0 || to >= ids.length) return
    event.preventDefault()
    const id = ids[index]
    commit(move(ids, index, to))
    // The row moved in the DOM and may have lost focus on the way.
    requestAnimationFrame(() => handles.current.get(id)?.focus())
  }

  /** The line that shows where the dragged row would land; none where it already is. */
  const dropMark = (index: number): 'before' | 'after' | null => {
    if (!drag) return null
    const from = ids.indexOf(drag.id)
    if (drag.over === from || drag.over === from + 1) return null
    if (drag.over === index) return 'before'
    return index === ids.length - 1 && drag.over === ids.length ? 'after' : null
  }

  return (
    <section className="flex min-w-0 flex-col rounded-lg border border-ink-700 bg-ink-850">
      <h2 className="border-b border-ink-700 px-4 py-3 text-sm font-semibold tracking-wide text-ink-50">
        {t(`taxonomy.${kind}.title`)}
      </h2>
      {isPending ? <p className="px-4 py-3 text-sm text-ink-300">{t('taxonomy.loading')}</p> : null}
      {error ? <p className="px-4 py-3 text-sm text-red-400">{error.message}</p> : null}
      {all && all.length === 0 ? (
        <p className="px-4 py-4 text-sm text-ink-300">{t(`taxonomy.${kind}.empty`)}</p>
      ) : null}
      {notice ? <p className="px-4 pt-2 text-sm text-red-400">{notice}</p> : null}

      <ul className="divide-y divide-ink-700/70 px-2">
        {visible.map((item, index) => (
          <TaxonomyRow
            key={item.id}
            kind={kind}
            item={item}
            dropMark={dropMark(index)}
            handleRef={(node) => {
              if (node) handles.current.set(item.id, node)
              else handles.current.delete(item.id)
            }}
            onHandleDragStart={dragStart(item)}
            onHandleKey={handleKey(index)}
            onDragOver={dragOver(index)}
            onDragEnd={() => setDrag(null)}
            onDrop={drop}
            onDelete={() => setDeleting(item)}
            onError={setNotice}
          />
        ))}
      </ul>

      <AddItem kind={kind} />

      {deleting ? (
        <DeleteItemDialog
          kind={kind}
          item={deleting}
          items={all ?? []}
          onClose={() => setDeleting(null)}
        />
      ) : null}
    </section>
  )
}

/** "+ Aggiungi": Enter creates and leaves the field open for the next name. */
function AddItem({ kind }: { kind: Kind }) {
  const { create } = useTaxonomyActions(kind)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const close = () => {
    setOpen(false)
    setName('')
    setError(null)
  }

  const submit = () => {
    if (!name.trim() || create.isPending) return
    create.mutate(name, {
      onSuccess: () => {
        setName('')
        setError(null)
      },
      onError: (err) => setError(err.message),
    })
  }

  return (
    <div className="mt-auto border-t border-ink-700 px-3 py-2">
      {open ? (
        <>
          <input
            autoFocus
            value={name}
            maxLength={80}
            placeholder={t(`taxonomy.${kind}.placeholder`)}
            aria-invalid={error !== null}
            onChange={(event) => {
              setName(event.target.value)
              setError(null)
            }}
            onBlur={() => !name.trim() && close()}
            onKeyDown={(event) => {
              if (event.key === 'Enter') submit()
              if (event.key === 'Escape') close()
            }}
            className={`w-full rounded border bg-ink-900 px-2 py-1 text-sm outline-none ${
              error ? 'border-red-400' : 'border-accent'
            }`}
          />
          {error ? <p className="mt-1 text-xs text-red-400">{error}</p> : null}
        </>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded px-2 py-1 text-sm text-accent hover:bg-ink-700"
        >
          {t(`taxonomy.${kind}.add`)}
        </button>
      )}
    </div>
  )
}
