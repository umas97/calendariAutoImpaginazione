// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The choices of the Export tab (SPEC §9.1) and how they become an
// `ExportRequest` (SPEC §8.1). The form keeps more than one request needs: the
// categories of groups not ticked yet, ticked groups hidden because archived.
// What goes to the server is always the visible part only, so an archived
// group never ends up in an export the user cannot see.
import type {
  Dpi,
  ExportFormat,
  ExportLast,
  ExportMode,
  ExportRequest,
  GroupSelection,
  Period,
  TaxonomyItem,
} from './api'

export type ExportForm = {
  period: Period
  mode: ExportMode
  formats: ExportFormat[]
  dpi: Dpi
  /** The ticked groups. */
  checked: number[]
  /** Chosen categories per group; absent or `null` means all of them. */
  categories: Record<number, number[] | null>
  /** `null`: the default folder. */
  outputDir: string | null
  /** Groups to lay out over several pages ("Esporta su più pagine"); not remembered. */
  multipage: number[]
}

/** What the screen shows: archived items only with "Mostra archiviati". */
export type Visible = { groups: TaxonomyItem[]; categories: TaxonomyItem[] }

/** The remembered choices, or the defaults: every group ticked, the pastoral year. */
export function initialForm(last: ExportLast | null, groups: TaxonomyItem[], pastoralYear: Period): ExportForm {
  if (!last) {
    return {
      period: pastoralYear,
      mode: 'per_group',
      formats: ['pdf'],
      dpi: 200,
      checked: groups.filter((g) => !g.archived).map((g) => g.id),
      categories: {},
      outputDir: null,
      multipage: [],
    }
  }
  return {
    period: last.period ?? pastoralYear,
    mode: last.mode,
    formats: last.formats.length ? last.formats : ['pdf'],
    dpi: last.dpi,
    checked: last.selections.map((s) => s.group_id),
    categories: Object.fromEntries(last.selections.map((s) => [s.group_id, s.category_ids])),
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
    selections: form.checked.map((id) => ({ group_id: id, category_ids: form.categories[id] ?? null })),
    output_dir: form.outputDir,
  }
}

/** The categories chosen for a group, among the visible ones, in the categories' order. */
export function chosenCategories(form: ExportForm, groupId: number, categories: TaxonomyItem[]): number[] {
  const chosen = form.categories[groupId]
  return categories.filter((c) => chosen == null || chosen.includes(c.id)).map((c) => c.id)
}

/** A group's new category choice; all of the visible ones collapses back to `null`. */
export function withCategories(
  form: ExportForm,
  groupId: number,
  ids: number[],
  categories: TaxonomyItem[],
): ExportForm {
  const all = categories.every((c) => ids.includes(c.id))
  return { ...form, categories: { ...form.categories, [groupId]: all ? null : ids } }
}

/** The ticked groups the screen shows, in the groups' order. */
export function checkedVisible(form: ExportForm, visible: Visible): TaxonomyItem[] {
  return visible.groups.filter((g) => form.checked.includes(g.id))
}

function selection(form: ExportForm, group: TaxonomyItem, visible: Visible): GroupSelection {
  return { group_id: group.id, category_ids: chosenCategories(form, group.id, visible.categories) }
}

function base(form: ExportForm, groups: TaxonomyItem[], visible: Visible): ExportRequest {
  return {
    period: form.period,
    mode: form.mode,
    formats: form.formats,
    dpi: form.dpi,
    selections: groups.map((g) => selection(form, g, visible)),
    multipage: form.multipage.filter((id) => groups.some((g) => g.id === id)),
  }
}

/** The export itself. */
export function exportRequest(form: ExportForm, visible: Visible, defaultDir: string): ExportRequest {
  return { ...base(form, checkedVisible(form, visible), visible), output_dir: form.outputDir ?? defaultDir }
}

/** The counts: every visible group, so unticked ones show their number too. */
export function countsRequest(form: ExportForm, visible: Visible): ExportRequest & { included: number[] } {
  return {
    ...base(form, visible.groups, visible),
    multipage: [],
    included: checkedVisible(form, visible).map((g) => g.id),
  }
}

/** Which sheet the preview shows: a group, or the complete calendar. */
export type SheetId = number | 'combined'

/**
 * One preview request per sheet: one per ticked group (`single_pdf` pages are
 * the same sheets as `per_group`), or one for the complete calendar.
 */
export function sheetRequests(form: ExportForm, visible: Visible): { id: SheetId; body: ExportRequest }[] {
  const groups = checkedVisible(form, visible)
  if (!groups.length) return []
  const preview = { ...form, formats: ['pdf'] as ExportFormat[] }
  if (form.mode === 'combined') return [{ id: 'combined', body: base(preview, groups, visible) }]
  return groups.map((g) => ({ id: g.id, body: { ...base(preview, [g], visible), mode: 'per_group' } }))
}

/** What stops the export before the server is even asked; `null` when nothing does. */
export function blocker(form: ExportForm, visible: Visible): 'noGroups' | 'noCategories' | 'period' | null {
  const groups = checkedVisible(form, visible)
  if (!groups.length) return 'noGroups'
  if (form.period.to < form.period.from) return 'period'
  if (groups.some((g) => chosenCategories(form, g.id, visible.categories).length === 0)) return 'noCategories'
  return null
}
