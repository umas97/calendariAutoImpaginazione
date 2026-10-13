// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The groups of the export (SPEC §9.1): a box to tick each, the number of its
// events in the period (kept up to date while the choices change), and its
// categories as coloured chips, all on by default. A click on the name shows
// that group's sheet in the preview; a group known not to fit one page says so.
import { useState } from 'react'
import type { ExportCounts, ExportMode, TaxonomyItem } from '../lib/api'
import { chosenCategories, withCategories, type ExportForm, type SheetId } from '../lib/exportForm'
import { plural, t } from '../i18n/it'

type Props = {
  form: ExportForm
  onChange: (form: ExportForm) => void
  /** Visible groups and categories, in the user's order. */
  groups: TaxonomyItem[]
  categories: TaxonomyItem[]
  counts: ExportCounts | undefined
  /** The counts are for older choices: shown dimmed until the new ones arrive. */
  countsStale: boolean
  tooBig: (id: number) => boolean
  focus: SheetId | null
  onFocus: (id: number) => void
  mode: ExportMode
}

export function ExportGroups(props: Props) {
  const { form, onChange, groups, categories, counts } = props
  const [open, setOpen] = useState<Set<number>>(new Set())
  const visibleChecked = groups.filter((g) => form.checked.includes(g.id))
  const allChecked = groups.length > 0 && visibleChecked.length === groups.length

  const setChecked = (id: number, on: boolean) =>
    onChange({ ...form, checked: on ? [...form.checked, id] : form.checked.filter((each) => each !== id) })
  const setAll = (on: boolean) => {
    const shown = new Set(groups.map((g) => g.id))
    const others = form.checked.filter((id) => !shown.has(id))
    onChange({ ...form, checked: on ? [...others, ...shown] : others })
  }
  const toggleOpen = (id: number) =>
    setOpen((old) => {
      const next = new Set(old)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setAll(!allChecked)}
        className="rounded px-1 text-sm text-accent hover:bg-ink-700"
      >
        {allChecked ? t('export.groups.selectNone') : t('export.groups.selectAll')}
      </button>
      <ul className="divide-y divide-ink-700 rounded-md border border-ink-700">
        {groups.map((group) => (
          <GroupRow
            key={group.id}
            group={group}
            checked={form.checked.includes(group.id)}
            onChecked={(on) => setChecked(group.id, on)}
            chosen={chosenCategories(form, group.id, categories)}
            onChosen={(ids) => onChange(withCategories(form, group.id, ids, categories))}
            categories={categories}
            count={counts?.groups[String(group.id)]}
            stale={props.countsStale}
            tooBig={props.tooBig(group.id)}
            focused={props.focus === group.id}
            onFocus={() => props.onFocus(group.id)}
            open={open.has(group.id)}
            onToggleOpen={() => toggleOpen(group.id)}
          />
        ))}
      </ul>
      {props.mode === 'combined' && counts ? (
        <p className={`text-sm text-ink-200 ${props.countsStale ? 'opacity-50' : ''}`}>
          {plural('export.groups.combined', counts.combined)}
        </p>
      ) : null}
    </div>
  )
}

type RowProps = {
  group: TaxonomyItem
  checked: boolean
  onChecked: (on: boolean) => void
  chosen: number[]
  onChosen: (ids: number[]) => void
  categories: TaxonomyItem[]
  count: number | undefined
  stale: boolean
  tooBig: boolean
  focused: boolean
  onFocus: () => void
  open: boolean
  onToggleOpen: () => void
}

function GroupRow(props: RowProps) {
  const { group, chosen, categories } = props
  const summary =
    chosen.length === categories.length
      ? t('export.groups.categoriesAll')
      : chosen.length === 0
        ? t('export.groups.categoriesNone')
        : t('export.groups.categoriesSome', { n: chosen.length, total: categories.length })
  const toggle = (id: number) =>
    props.onChosen(chosen.includes(id) ? chosen.filter((each) => each !== id) : [...chosen, id])
  const empty = props.count === 0

  return (
    <li className={props.focused ? 'bg-ink-800' : ''}>
      <div className="flex items-center gap-2 px-2 py-1.5">
        <input
          type="checkbox"
          checked={props.checked}
          aria-label={group.name}
          onChange={(event) => props.onChecked(event.target.checked)}
          className="h-4 w-4 shrink-0 accent-[var(--color-accent)]"
        />
        <button
          type="button"
          title={t('export.groups.showPreview')}
          disabled={!props.checked}
          onClick={props.onFocus}
          className={`min-w-0 flex-1 truncate text-left text-sm ${props.checked ? 'text-ink-50 hover:underline' : 'text-ink-300'}`}
        >
          {group.name}
          {group.archived ? <span className="ml-1 text-xs text-ink-300">({t('export.groups.archived')})</span> : null}
        </button>
        {props.checked && props.tooBig ? (
          <span className="shrink-0 rounded bg-red-500/15 px-1.5 text-xs text-red-400">{t('export.groups.tooBig')}</span>
        ) : null}
        <span
          className={`shrink-0 text-xs tabular-nums ${props.stale ? 'opacity-50' : ''} ${
            empty && props.checked ? 'text-warn' : 'text-ink-300'
          }`}
        >
          {props.count === undefined ? '' : plural('export.groups.count', props.count)}
        </span>
        <button
          type="button"
          aria-expanded={props.open}
          aria-label={t('export.groups.expand', { name: group.name })}
          title={t('export.groups.expand', { name: group.name })}
          onClick={props.onToggleOpen}
          className={`shrink-0 rounded px-1.5 text-xs hover:bg-ink-700 ${
            chosen.length === 0 && props.checked ? 'text-red-400' : 'text-ink-300'
          }`}
        >
          {summary} {props.open ? '▾' : '▸'}
        </button>
      </div>
      {props.open ? (
        <div className="space-y-1.5 px-8 pb-2">
          <div className="flex flex-wrap gap-1.5">
            {categories.map((category) => {
              const on = chosen.includes(category.id)
              return (
                <button
                  key={category.id}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(category.id)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs ${
                    on ? 'border-accent bg-accent/15 text-ink-50' : 'border-ink-600 text-ink-300 hover:bg-ink-700'
                  }`}
                >
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${on ? '' : 'opacity-40'}`}
                    style={{ background: category.color }}
                  />
                  {category.name}
                </button>
              )
            })}
          </div>
          <div className="flex gap-1 text-xs">
            <button
              type="button"
              onClick={() => props.onChosen(categories.map((c) => c.id))}
              className="rounded px-1.5 text-accent hover:bg-ink-700"
            >
              {t('export.groups.all')}
            </button>
            <button type="button" onClick={() => props.onChosen([])} className="rounded px-1.5 text-accent hover:bg-ink-700">
              {t('export.groups.none')}
            </button>
          </div>
        </div>
      ) : null}
    </li>
  )
}
