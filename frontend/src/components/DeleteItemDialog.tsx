// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Deleting a group or a category (SPEC §6.3). Events linked to it lose the
// link; those that have *only* this one ("orphans") would be left with no group
// or no category, so the user must say where they go -- another item, or away
// with it -- and "Elimina" stays disabled until they do. The server enforces the
// same rule (409), this dialog just asks first.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Kind, type OrphanChoice, type TaxonomyItem } from '../lib/api'
import { useTaxonomyActions } from '../lib/taxonomy'
import { plural, t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'

type Props = {
  kind: Kind
  item: TaxonomyItem
  /** Every item of the kind: the possible destinations are taken from here. */
  items: TaxonomyItem[]
  onClose: () => void
}

export function DeleteItemDialog({ kind, item, items, onClose }: Props) {
  const usage = useQuery({
    queryKey: ['usage', kind, item.id],
    queryFn: () => api.itemUsage(kind, item.id),
    staleTime: 0,
    gcTime: 0,
  })
  const { remove, update } = useTaxonomyActions(kind)
  const [policy, setPolicy] = useState<'reassign' | 'delete' | null>(null)
  const [target, setTarget] = useState<number | null>(null)
  const targets = items.filter((each) => each.id !== item.id && !each.archived)

  const orphans = usage.data?.orphans ?? 0
  let choice: OrphanChoice | undefined
  if (policy === 'delete') choice = { orphans: 'delete' }
  if (policy === 'reassign' && target !== null) choice = { orphans: 'reassign', to: target }
  const ready = usage.isSuccess && (orphans === 0 || choice !== undefined)
  const busy = remove.isPending || update.isPending
  const error = usage.error ?? remove.error ?? update.error

  const confirm = () =>
    remove.mutate({ id: item.id, choice: orphans ? choice : undefined }, { onSuccess: onClose })
  const archive = () =>
    update.mutate({ id: item.id, patch: { archived: true } }, { onSuccess: onClose })

  return (
    <Dialog
      title={t(`delete.${kind}.title`, { name: item.name })}
      onClose={onClose}
      width="max-w-lg"
      footer={
        <>
          {!item.archived ? (
            <button className={`${buttonClass.secondary} mr-auto`} onClick={archive} disabled={busy}>
              {t('delete.archiveInstead')}
            </button>
          ) : null}
          <button className={buttonClass.secondary} onClick={onClose} disabled={busy}>
            {t('common.cancel')}
          </button>
          <button className={buttonClass.danger} onClick={confirm} disabled={!ready || busy}>
            {remove.isPending ? t('delete.working') : t('delete.confirm')}
          </button>
        </>
      }
    >
      {usage.isPending ? <p className="text-ink-300">{t('delete.loading')}</p> : null}
      {usage.data ? (
        <p>
          {usage.data.events === 0
            ? t('delete.none')
            : plural(`delete.${kind}.linked`, usage.data.events)}
        </p>
      ) : null}

      {orphans > 0 ? (
        <fieldset className="space-y-2 rounded-md border border-ink-600 p-3">
          <legend className="px-1 font-medium text-ink-50">
            {plural(`delete.${kind}.orphans`, orphans)}
          </legend>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="policy"
              checked={policy === 'reassign'}
              disabled={targets.length === 0}
              onChange={() => setPolicy('reassign')}
            />
            <span className={targets.length === 0 ? 'text-ink-400' : ''}>
              {plural('delete.reassign', orphans)}
            </span>
            {targets.length > 0 ? (
              <select
                className="ml-1 min-w-0 flex-1 rounded-md border border-ink-500 bg-ink-800 px-2 py-1"
                value={target ?? ''}
                onChange={(event) => {
                  setTarget(event.target.value ? Number(event.target.value) : null)
                  setPolicy('reassign')
                }}
              >
                <option value="">{t('delete.reassign.choose')}</option>
                {targets.map((each) => (
                  <option key={each.id} value={each.id}>
                    {each.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-ink-400">{t(`delete.${kind}.noTarget`)}</span>
            )}
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="policy"
              checked={policy === 'delete'}
              onChange={() => setPolicy('delete')}
            />
            <span className="text-red-400">{plural('delete.alsoEvents', orphans)}</span>
          </label>
        </fieldset>
      ) : null}

      {!item.archived ? <p className="text-ink-300">{t(`delete.${kind}.archiveHint`)}</p> : null}
      {error ? <p className="text-red-400">{error.message}</p> : null}
    </Dialog>
  )
}
