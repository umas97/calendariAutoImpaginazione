// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// What the sheets are for (SPEC §9.1): "Un foglio per" gruppo or categoria,
// then one row per group (or category) with a box to tick it, the number of
// its events in the period (kept up to date while the choices change), and the
// categories (or groups) it takes as coloured chips -- the colours of its bars --, all on by default. A click
// on the name shows that sheet in the preview; a sheet known not to fit one
// page says so.
import { useState } from 'react'
import type { ExportBy, ExportCounts, ExportMode, TaxonomyItem } from '../lib/api'
import { chosenChips, side, withChips, withSide, type ExportForm, type SheetId } from '../lib/exportForm'
import { plural, t } from '../i18n/it'

type Props = {
  form: ExportForm
  onChange: (form: ExportForm) => void
  /** The rows (one sheet each) and the chips (each sheet's filter), visible, in the user's order. */
  rows: TaxonomyItem[]
  chips: TaxonomyItem[]
  counts: ExportCounts | undefined
  /** The counts are for older choices: shown dimmed until the new ones arrive. */
  countsStale: boolean
  tooBig: (id: number) => boolean
  focus: SheetId | null
  onFocus: (id: number) => void
  mode: ExportMode
}

const SIDES: ExportBy[] = ['group', 'category']

export function ExportSheets(props: Props) {
  const { form, onChange, rows, chips, counts } = props
  const by = form.by
  const [open, setOpen] = useState<Set<string>>(new Set())
  const current = side(form)
  const allChecked = rows.length > 0 && rows.every((r) => current.checked.includes(r.id))

  const setBy = (next: ExportBy) => onChange({ ...form, by: next, multipage: [] })
  const setChecked = (id: number, on: boolean) =>
    onChange(
      withSide(form, {
        ...current,
        checked: on ? [...current.checked, id] : current.checked.filter((each) => each !== id),
      }),
    )
  const setAll = (on: boolean) => {
    const shown = new Set(rows.map((r) => r.id))
    const others = current.checked.filter((id) => !shown.has(id))
    onChange(withSide(form, { ...current, checked: on ? [...others, ...shown] : others }))
  }
  // Rows of both sides share the state: the key keeps a group and a category apart.
  const toggleOpen = (id: number) =>
    setOpen((old) => {
      const next = new Set(old)
      const key = `${by}:${id}`
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm">
        <span id="export-by" className="text-ink-200">
          {props.mode === 'combined' ? t('export.by.combinedLabel') : t('export.by.label')}
        </span>
        <div role="radiogroup" aria-labelledby="export-by" className="inline-flex rounded-md border border-ink-600 p-0.5">
          {SIDES.map((each) => (
            <button
              key={each}
              type="button"
              role="radio"
              aria-checked={by === each}
              onClick={() => setBy(each)}
              className={`rounded px-2.5 py-0.5 ${by === each ? 'bg-accent/20 text-ink-50' : 'text-ink-300 hover:bg-ink-700'}`}
            >
              {t(`export.by.${each}`)}
            </button>
          ))}
        </div>
      </div>
      <button
        type="button"
        onClick={() => setAll(!allChecked)}
        className="rounded px-1 text-sm text-accent hover:bg-ink-700"
      >
        {allChecked ? t(`export.${by}.selectNone`) : t(`export.${by}.selectAll`)}
      </button>
      <ul className="divide-y divide-ink-700 rounded-md border border-ink-700">
        {rows.map((row) => (
          <SheetRow
            key={`${by}:${row.id}`}
            by={by}
            row={row}
            checked={current.checked.includes(row.id)}
            onChecked={(on) => setChecked(row.id, on)}
            chosen={chosenChips(form, row.id, chips)}
            onChosen={(ids) => onChange(withChips(form, row.id, ids, chips))}
            chips={chips}
            count={counts?.sheets[String(row.id)]}
            stale={props.countsStale}
            tooBig={props.tooBig(row.id)}
            focused={props.focus === row.id}
            onFocus={() => props.onFocus(row.id)}
            open={open.has(`${by}:${row.id}`)}
            onToggleOpen={() => toggleOpen(row.id)}
          />
        ))}
      </ul>
      {props.mode === 'combined' && counts ? (
        <p className={`text-sm text-ink-200 ${props.countsStale ? 'opacity-50' : ''}`}>
          {plural('export.rows.combined', counts.combined)}
        </p>
      ) : null}
    </div>
  )
}

type RowProps = {
  by: ExportBy
  row: TaxonomyItem
  checked: boolean
  onChecked: (on: boolean) => void
  chosen: number[]
  onChosen: (ids: number[]) => void
  chips: TaxonomyItem[]
  count: number | undefined
  stale: boolean
  tooBig: boolean
  focused: boolean
  onFocus: () => void
  open: boolean
  onToggleOpen: () => void
}

function SheetRow(props: RowProps) {
  const { by, row, chosen, chips } = props
  const summary =
    chosen.length === chips.length
      ? t(`export.${by}.chipsAll`)
      : chosen.length === 0
        ? t(`export.${by}.chipsNone`)
        : t(`export.${by}.chipsSome`, { n: chosen.length, total: chips.length })
  const toggle = (id: number) =>
    props.onChosen(chosen.includes(id) ? chosen.filter((each) => each !== id) : [...chosen, id])
  const empty = props.count === 0

  return (
    <li className={props.focused ? 'bg-ink-800' : ''}>
      <div className="flex items-center gap-2 px-2 py-1.5">
        <input
          type="checkbox"
          checked={props.checked}
          aria-label={row.name}
          onChange={(event) => props.onChecked(event.target.checked)}
          className="h-4 w-4 shrink-0 accent-[var(--color-accent)]"
        />
        <button
          type="button"
          title={t(`export.${by}.showPreview`)}
          disabled={!props.checked}
          onClick={props.onFocus}
          className={`min-w-0 flex-1 truncate text-left text-sm ${props.checked ? 'text-ink-50 hover:underline' : 'text-ink-300'}`}
        >
          {row.name}
          {row.archived ? <span className="ml-1 text-xs text-ink-300">({t(`export.${by}.archived`)})</span> : null}
        </button>
        {props.checked && props.tooBig ? (
          <span className="shrink-0 rounded bg-red-500/15 px-1.5 text-xs text-red-400">{t('export.rows.tooBig')}</span>
        ) : null}
        <span
          className={`shrink-0 text-xs tabular-nums ${props.stale ? 'opacity-50' : ''} ${
            empty && props.checked ? 'text-warn' : 'text-ink-300'
          }`}
        >
          {props.count === undefined ? '' : plural('export.rows.count', props.count)}
        </span>
        <button
          type="button"
          aria-expanded={props.open}
          aria-label={t(`export.${by}.expand`, { name: row.name })}
          title={t(`export.${by}.expand`, { name: row.name })}
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
            {chips.map((chip) => {
              const on = chosen.includes(chip.id)
              return (
                <button
                  key={chip.id}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(chip.id)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs ${
                    on ? 'border-accent bg-accent/15 text-ink-50' : 'border-ink-600 text-ink-300 hover:bg-ink-700'
                  }`}
                >
                  <span className={`h-2.5 w-2.5 rounded-full ${on ? '' : 'opacity-40'}`} style={{ background: chip.color }} />
                  {chip.name}
                </button>
              )
            })}
          </div>
          <div className="flex gap-1 text-xs">
            <button
              type="button"
              onClick={() => props.onChosen(chips.map((c) => c.id))}
              className="rounded px-1.5 text-accent hover:bg-ink-700"
            >
              {t(`export.${by}.all`)}
            </button>
            <button type="button" onClick={() => props.onChosen([])} className="rounded px-1.5 text-accent hover:bg-ink-700">
              {t(`export.${by}.none`)}
            </button>
          </div>
        </div>
      ) : null}
    </li>
  )
}
