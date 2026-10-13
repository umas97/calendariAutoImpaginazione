// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// One group or category: handle, name, colour, number of events, menu. The row
// knows nothing about order -- the list owns dragging and passes the handlers.
import type { DragEvent, KeyboardEvent, Ref } from 'react'
import type { ItemPatch, Kind, TaxonomyItem } from '../lib/api'
import { useTaxonomyActions } from '../lib/taxonomy'
import { t } from '../i18n/it'
import { ColorPicker } from './ColorPicker'
import { InlineName } from './InlineName'
import { MenuItem, Popover } from './Popover'

type Props = {
  kind: Kind
  item: TaxonomyItem
  /** Where a dragged row would land relative to this one, if over it. */
  dropMark: 'before' | 'after' | null
  handleRef: Ref<HTMLButtonElement>
  onHandleDragStart: (event: DragEvent<HTMLButtonElement>) => void
  onHandleKey: (event: KeyboardEvent<HTMLButtonElement>) => void
  onDragOver: (event: DragEvent<HTMLLIElement>) => void
  onDragEnd: () => void
  onDrop: (event: DragEvent<HTMLLIElement>) => void
  onDelete: () => void
  onError: (message: string) => void
}

export function countLabel(n: number): string {
  if (n === 0) return t('taxonomy.count.zero')
  return n === 1 ? t('taxonomy.count.one') : t('taxonomy.count.many', { n })
}

const DROP_MARK = {
  before: 'shadow-[inset_0_2px_0_0_var(--color-accent)]',
  after: 'shadow-[inset_0_-2px_0_0_var(--color-accent)]',
}

export function TaxonomyRow(props: Props) {
  const { kind, item, dropMark } = props
  const { update } = useTaxonomyActions(kind)
  const patch = (changes: ItemPatch) =>
    update.mutateAsync({ id: item.id, patch: changes })

  return (
    <li
      onDragOver={props.onDragOver}
      onDrop={props.onDrop}
      className={`flex items-center gap-1.5 py-1.5 pr-1 ${dropMark ? DROP_MARK[dropMark] : ''}`}
    >
      <button
        ref={props.handleRef}
        type="button"
        draggable
        onDragStart={props.onHandleDragStart}
        onDragEnd={props.onDragEnd}
        onKeyDown={props.onHandleKey}
        title={t('taxonomy.dragHandle')}
        aria-label={t('taxonomy.dragHandle')}
        className="cursor-grab rounded px-1 py-0.5 text-ink-400 hover:bg-ink-700 hover:text-ink-100 active:cursor-grabbing"
      >
        <span aria-hidden>⠿</span>
      </button>

      {item.color !== undefined ? (
        <ColorPicker
          value={item.color}
          onChange={(color) => patch({ color }).catch((err: Error) => props.onError(err.message))}
        />
      ) : null}

      <InlineName
        value={item.name}
        onSave={(name) => patch({ name })}
        className={item.archived ? 'text-ink-300' : 'text-ink-50'}
      />

      {item.archived ? (
        <span className="rounded bg-ink-700 px-1.5 py-0.5 text-xs text-ink-300">
          {t(`taxonomy.${kind}.archived`)}
        </span>
      ) : null}
      <span className="w-24 shrink-0 text-right text-xs text-ink-300 tabular-nums">
        {countLabel(item.event_count)}
      </span>

      <Popover
        label={t('taxonomy.actions')}
        trigger={<span aria-hidden>⋯</span>}
        triggerClassName="rounded px-2 py-0.5 text-ink-300 hover:bg-ink-700 hover:text-ink-50"
      >
        {(close) => (
          <>
            <MenuItem
              onClick={() => {
                close()
                patch({ archived: !item.archived }).catch((err: Error) =>
                  props.onError(err.message),
                )
              }}
            >
              {item.archived ? t('taxonomy.restore') : t('taxonomy.archive')}
            </MenuItem>
            <MenuItem
              danger
              onClick={() => {
                close()
                props.onDelete()
              }}
            >
              {t('taxonomy.delete')}
            </MenuItem>
          </>
        )}
      </Popover>
    </li>
  )
}
