// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Export" (SPEC §9.1): the settings on the left, the preview on the right.
// Counts, preview and files all come from the same request and the same
// server code (SPEC §5.1), so what the preview shows is what gets saved. The
// choices are remembered (SPEC §10.2, `export.last`), except "Esporta su più
// pagine", which belongs to the period and the events of the moment.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, type ApiError, type ExportOptions, type Parish, type Settings, type TaxonomyItem } from '../lib/api'
import {
  blocker,
  checkedVisible,
  countsRequest,
  exportRequest,
  initialForm,
  sheetRequests,
  toLast,
  type ExportForm,
  type SheetId,
} from '../lib/exportForm'
import { useExportJob } from '../lib/exportJob'
import { usePreview } from '../lib/preview'
import { useSaveSetting, useSettings } from '../lib/settings'
import { useItems } from '../lib/taxonomy'
import { plural, t } from '../i18n/it'
import { buttonClass } from '../components/Dialog'
import { FormatChoice, ModeChoice } from '../components/ExportFormatOptions'
import { ExportGroups } from '../components/ExportGroups'
import { ExportJobDialog } from '../components/ExportJobDialog'
import { ExportPeriod } from '../components/ExportPeriod'
import { ExportPreview } from '../components/ExportPreview'
import { FolderField } from '../components/FolderField'
import { ParishHeader } from '../components/ParishHeader'

export function ExportPage() {
  const settings = useSettings()
  const groups = useItems('groups')
  const categories = useItems('categories')
  const options = useQuery({ queryKey: ['exportOptions'], queryFn: api.exportOptions, staleTime: 0 })
  const parish = useQuery({ queryKey: ['parish'], queryFn: api.parish })
  const error = settings.error ?? groups.error ?? categories.error ?? options.error ?? parish.error
  if (error) return <p className="p-6 text-red-400">{error.message}</p>
  if (!settings.data || !groups.data || !categories.data || !options.data || !parish.data) {
    return <p className="p-6 text-ink-300">{t('export.loading')}</p>
  }
  if (!groups.data.some((g) => !g.archived) || !categories.data.some((c) => !c.archived)) {
    return (
      <div className="mx-auto mt-[10vh] max-w-md space-y-4 px-6 text-center">
        <p className="text-ink-200">{t('export.empty.text')}</p>
        <Link to="/gruppi" className={`inline-block ${buttonClass.primary}`}>
          {t('export.empty.action')}
        </Link>
      </div>
    )
  }
  return (
    <ExportScreen
      settings={settings.data}
      groups={groups.data}
      categories={categories.data}
      options={options.data}
      parish={parish.data}
    />
  )
}

type ScreenProps = {
  settings: Settings
  groups: TaxonomyItem[]
  categories: TaxonomyItem[]
  options: ExportOptions
  parish: Parish
}

function ExportScreen({ settings, groups, categories, options, parish }: ScreenProps) {
  const [form, setForm] = useState<ExportForm>(() =>
    initialForm(settings['export.last'], groups, options.shortcuts.pastoral_year),
  )
  const [showArchived, setShowArchived] = useState(false)
  const visible = useMemo(
    () => ({
      groups: groups.filter((g) => showArchived || !g.archived),
      categories: categories.filter((c) => showArchived || !c.archived),
    }),
    [groups, categories, showArchived],
  )
  const update = (patch: Partial<ExportForm>) => setForm((old) => ({ ...old, ...patch }))

  useRemember(form)

  const countsBody = useMemo(() => countsRequest(form, visible), [form, visible])
  const counts = useQuery({
    queryKey: ['exportCounts', countsBody],
    queryFn: () => api.exportCounts(countsBody),
    placeholderData: keepPreviousData,
    enabled: visible.groups.length > 0 && form.period.from <= form.period.to,
    retry: false,
    staleTime: 0,
  })

  const job = useExportJob()
  const requests = useMemo(() => sheetRequests(form, visible), [form, visible])
  const sheets = useMemo(
    () =>
      form.mode === 'combined'
        ? requests.map(() => ({ id: 'combined' as SheetId, title: t('preview.combined') }))
        : checkedVisible(form, visible).map((g) => ({ id: g.id as SheetId, title: g.name })),
    [form, visible, requests],
  )
  const [focus, setFocus] = useState<SheetId | null>(null)
  const shownFocus = sheets.some((s) => s.id === focus) ? focus : (sheets[0]?.id ?? null)
  const letterhead = `${parish.name}|${parish.logo?.updated_at ?? ''}`
  const preview = usePreview(requests, letterhead, shownFocus, job.running || job.starting)
  const tooBig = (id: number) => {
    const result = preview.sheet(id).current
    return result?.status === 'done' && result.eventCount > 0 && !result.fits
  }

  const setMultipage = (id: number, on: boolean) =>
    update({ multipage: on ? [...form.multipage, id] : form.multipage.filter((each) => each !== id) })

  const stop = blocker(form, visible)
  const serverFields = { ...(counts.error as ApiError | null)?.fields, ...job.error?.fields }
  const periodError = serverFields['period.to'] ?? serverFields['period.from']
  const withEvents = checkedVisible(form, visible).filter((g) => (counts.data?.groups[String(g.id)] ?? 1) > 0)
  const misfits = form.mode === 'combined' ? 0 : withEvents.filter((g) => tooBig(g.id)).length
  const sheetCount = form.mode === 'combined' ? Number((counts.data?.combined ?? 0) > 0) : withEvents.length - misfits

  const start = () => void job.start(exportRequest(form, visible, options.default_dir))
  const redoOnSeveralPages = (ids: number[]) => {
    const body = exportRequest(form, visible, options.default_dir)
    void job.start({
      ...body,
      mode: 'per_group',
      selections: body.selections.filter((s) => ids.includes(s.group_id)),
      multipage: ids,
    })
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-[27rem] shrink-0 flex-col border-r border-ink-700">
        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-4">
          <Section title={t('export.period.title')}>
            <ExportPeriod
              period={form.period}
              shortcuts={options.shortcuts}
              onChange={(period) => update({ period, multipage: [] })}
              error={periodError}
            />
          </Section>
          <Section title={t('export.mode.title')}>
            <ModeChoice mode={form.mode} onChange={(mode) => update({ mode })} />
          </Section>
          <Section title={t('export.format.title')}>
            <FormatChoice
              formats={form.formats}
              dpi={form.dpi}
              onFormats={(formats) => update({ formats })}
              onDpi={(dpi) => update({ dpi })}
            />
          </Section>
          <Section
            title={t('export.groups.title')}
            aside={
              <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-200">
                <input
                  type="checkbox"
                  checked={showArchived}
                  onChange={(event) => setShowArchived(event.target.checked)}
                  className="h-3.5 w-3.5 accent-[var(--color-accent)]"
                />
                {t('export.groups.showArchived')}
              </label>
            }
          >
            <ExportGroups
              form={form}
              onChange={setForm}
              groups={visible.groups}
              categories={visible.categories}
              counts={counts.data}
              countsStale={counts.isPlaceholderData || counts.isFetching}
              tooBig={tooBig}
              focus={shownFocus}
              onFocus={setFocus}
              mode={form.mode}
            />
          </Section>
          <Section title={t('export.parish.title')}>
            <ParishHeader parish={parish} />
          </Section>
          <Section title={t('export.folder.title')}>
            <FolderField
              value={form.outputDir}
              defaultDir={options.default_dir}
              home={options.home}
              onChange={(outputDir) => update({ outputDir })}
              error={serverFields['output_dir'] ?? serverFields['path']}
            />
          </Section>
        </div>
        <div className="space-y-2 border-t border-ink-700 bg-ink-850 p-4">
          <div className="flex items-center gap-3">
            <button className={buttonClass.primary} disabled={stop !== null || job.starting} onClick={start}>
              {job.starting ? t('export.starting') : t('export.go')}
            </button>
            <span className="text-sm text-ink-300">
              {stop ? t(`export.blocked.${stop}`) : counts.data ? plural('export.sheets', sheetCount) : ''}
              {!stop && misfits ? <span className="block text-red-400">{plural('export.sheets.tooBig', misfits)}</span> : null}
            </span>
          </div>
          {job.error && !job.job ? <p className="text-sm text-red-400">{job.error.message}</p> : null}
        </div>
      </aside>
      <section className="flex min-w-0 flex-1 flex-col">
        <ExportPreview
          sheets={sheets}
          focus={shownFocus}
          onFocus={setFocus}
          sheet={preview.sheet}
          waiting={preview.waiting}
          multipage={form.multipage}
          onMultipage={setMultipage}
        />
      </section>
      {job.job ? (
        <ExportJobDialog
          job={job.job}
          home={options.home}
          onClose={job.close}
          onMultipage={form.mode === 'combined' ? undefined : redoOnSeveralPages}
        />
      ) : null}
    </div>
  )
}

/** The choices, saved half a second after the last change (not on opening). */
function useRemember(form: ExportForm) {
  const save = useSaveSetting('export.last')
  const value = JSON.stringify(toLast(form))
  const opened = useRef<string | null>(value)
  useEffect(() => {
    if (value === opened.current) return
    opened.current = null
    const timer = window.setTimeout(() => save.mutate(JSON.parse(value)), 500)
    return () => window.clearTimeout(timer)
    // `save` changes identity on every render; `value` is what matters.
  }, [value])
}

function Section({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-wider text-ink-300 uppercase">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}
