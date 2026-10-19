// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The choices of the Export tab (SPEC §9.1) and how they become an
// `ExportRequest` (SPEC §8.1). Sheets are per group (each filtered by
// category) or per category (each filtered by group): the form keeps both
// choices, so switching back finds the other one as it was. It also keeps more
// than one request needs: the chips of rows not ticked yet, ticked rows hidden
// because archived. What goes to the server is always the visible part only,
// so an archived item never ends up in an export the user cannot see.
import type {
  Dpi,
  ExportBy,
  ExportFormat,
  ExportLast,
  ExportMode,
  ExportRequest,
  Period,
  TaxonomyItem,
} from './api'

export type ExportForm = {
  period: Period
  mode: ExportMode
  formats: ExportFormat[]
  dpi: Dpi
  by: ExportBy
  /** The ticked groups (sheets per group). */
  checked: number[]
  /** Chosen categories per group; absent or `null` means all of them. */
  categories: Record<number, number[] | null>
  /** The ticked categories (sheets per category). */
  checkedCategories: number[]
  /** Chosen groups per category; absent or `null` means all of them. */
  groups: Record<number, number[] | null>
  /** `null`: the default folder. */
  outputDir: string | null
  /** Sheets to lay out over several pages ("Esporta su più pagine"); not remembered. */
  multipage: number[]
}

/** What the screen shows: archived items only with "Mostra archiviati". */
export type Visible = { groups: TaxonomyItem[]; categories: TaxonomyItem[] }

/** One side of the form: the ticked rows (the sheets) and the chips chosen in each. */
export type Side = { checked: number[]; chosen: Record<number, number[] | null> }

const active = (items: TaxonomyItem[]) => items.filter((i) => !i.archived).map((i) => i.id)

/**
 * The remembered choices, or the defaults: every group ticked, the pastoral
 * year. Categories never used for sheets of their own start all ticked.
 */
export function initialForm(
  last: ExportLast | null,
  groups: TaxonomyItem[],
  categories: TaxonomyItem[],
  pastoralYear: Period,
): ExportForm {
  const perCategory = last?.category_selections ?? []
  const byCategory = perCategory.length
    ? {
        checkedCategories: perCategory.map((s) => s.category_id),
        groups: Object.fromEntries(perCategory.map((s) => [s.category_id, s.group_ids])),
      }
    : { checkedCategories: active(categories), groups: {} }
  if (!last) {
    return {
      period: pastoralYear,
      mode: 'per_group',
      formats: ['pdf'],
      dpi: 200,
      by: 'group',
      checked: active(groups),
      categories: {},
      ...byCategory,
      outputDir: null,
      multipage: [],
    }
  }
  return {
    period: last.period ?? pastoralYear,
    mode: last.mode,
    formats: last.formats.length ? last.formats : ['pdf'],
    dpi: last.dpi,
    // Choices saved before sheets per category existed have no `by`.
    by: last.by ?? 'group',
    checked: last.selections.map((s) => s.group_id),
    categories: Object.fromEntries(last.selections.map((s) => [s.group_id, s.category_ids])),
    ...byCategory,
    outputDir: last.output_dir,
    multipage: [],
  }
}

export function toLast(form: ExportForm): ExportLast {
  return {
    period: form.period,
    mode: form.mode,
    formats: form.formats,
    dpi: form.dpi,
    by: form.by,
    selections: form.checked.map((id) => ({ group_id: id, category_ids: form.categories[id] ?? null })),
    category_selections: form.checkedCategories.map((id) => ({
      category_id: id,
      group_ids: form.groups[id] ?? null,
    })),
    output_dir: form.outputDir,
  }
}

/** The side `by` picks. */
export function side(form: ExportForm): Side {
  return form.by === 'group'
    ? { checked: form.checked, chosen: form.categories }
    : { checked: form.checkedCategories, chosen: form.groups }
}

/** The form with its current side replaced. */
export function withSide(form: ExportForm, next: Side): ExportForm {
  return form.by === 'group'
    ? { ...form, checked: next.checked, categories: next.chosen }
    : { ...form, checkedCategories: next.checked, groups: next.chosen }
}

/** The rows (one sheet each) and the chips (the filter of each sheet) of the current side. */
export function lists(form: ExportForm, visible: Visible): { rows: TaxonomyItem[]; chips: TaxonomyItem[] } {
  return form.by === 'group'
    ? { rows: visible.groups, chips: visible.categories }
    : { rows: visible.categories, chips: visible.groups }
}

/** The chips chosen for a row, among the visible ones, in the user's order. */
export function chosenChips(form: ExportForm, rowId: number, chips: TaxonomyItem[]): number[] {
  const chosen = side(form).chosen[rowId]
  return chips.filter((c) => chosen == null || chosen.includes(c.id)).map((c) => c.id)
}

/** A row's new chip choice; all of the visible ones collapses back to `null`. */
export function withChips(form: ExportForm, rowId: number, ids: number[], chips: TaxonomyItem[]): ExportForm {
  const current = side(form)
  const all = chips.every((c) => ids.includes(c.id))
  return withSide(form, { ...current, chosen: { ...current.chosen, [rowId]: all ? null : ids } })
}

/** The ticked rows the screen shows, in the user's order. */
export function checkedVisible(form: ExportForm, visible: Visible): TaxonomyItem[] {
  const { checked } = side(form)
  return lists(form, visible).rows.filter((r) => checked.includes(r.id))
}

function base(form: ExportForm, rows: TaxonomyItem[], visible: Visible): ExportRequest {
  const { chips } = lists(form, visible)
  const pick = (row: TaxonomyItem) => chosenChips(form, row.id, chips)
  return {
    period: form.period,
    mode: form.mode,
    formats: form.formats,
    dpi: form.dpi,
    by: form.by,
    selections: form.by === 'group' ? rows.map((r) => ({ group_id: r.id, category_ids: pick(r) })) : [],
    category_selections:
      form.by === 'category' ? rows.map((r) => ({ category_id: r.id, group_ids: pick(r) })) : [],
    multipage: form.multipage.filter((id) => rows.some((r) => r.id === id)),
  }
}

/** The export itself. */
export function exportRequest(form: ExportForm, visible: Visible, defaultDir: string): ExportRequest {
  return { ...base(form, checkedVisible(form, visible), visible), output_dir: form.outputDir ?? defaultDir }
}

/** The same export limited to some sheets, each over several pages. */
export function multipageRequest(body: ExportRequest, ids: number[]): ExportRequest {
  return {
    ...body,
    mode: 'per_group',
    selections: body.selections.filter((s) => ids.includes(s.group_id)),
    category_selections: body.category_selections.filter((s) => ids.includes(s.category_id)),
    multipage: ids,
  }
}

/** The counts: every visible row, so unticked ones show their number too. */
export function countsRequest(form: ExportForm, visible: Visible): ExportRequest & { included: number[] } {
  return {
    ...base(form, lists(form, visible).rows, visible),
    multipage: [],
    included: checkedVisible(form, visible).map((r) => r.id),
  }
}

/** Which sheet the preview shows: a group or category (per `by`), or the complete calendar. */
export type SheetId = number | 'combined'

/**
 * One preview request per sheet: one per ticked row (`single_pdf` pages are
 * the same sheets as `per_group`), or one for the complete calendar.
 */
export function sheetRequests(form: ExportForm, visible: Visible): { id: SheetId; body: ExportRequest }[] {
  const rows = checkedVisible(form, visible)
  if (!rows.length) return []
  const preview = { ...form, formats: ['pdf'] as ExportFormat[] }
  if (form.mode === 'combined') return [{ id: 'combined', body: base(preview, rows, visible) }]
  return rows.map((r) => ({ id: r.id, body: { ...base(preview, [r], visible), mode: 'per_group' } }))
}

/** What stops the export before the server is even asked; `null` when nothing does. */
export function blocker(form: ExportForm, visible: Visible): 'noRows' | 'noChips' | 'period' | null {
  const rows = checkedVisible(form, visible)
  if (!rows.length) return 'noRows'
  if (form.period.to < form.period.from) return 'period'
  const { chips } = lists(form, visible)
  if (rows.some((r) => chosenChips(form, r.id, chips).length === 0)) return 'noChips'
  return null
}
