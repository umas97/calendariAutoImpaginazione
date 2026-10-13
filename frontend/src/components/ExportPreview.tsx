// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The right column of the Export tab (SPEC §9.1): the pages of each sheet,
// group by group, with the layout the program chose ("1 colonna, 10 pt") or,
// in red, "non entra in un A4" and the way out: "Esporta su più pagine". While
// a new preview is prepared the old pages stay, dimmed.
import type { SheetLayout } from '../lib/api'
import type { SheetId } from '../lib/exportForm'
import type { SheetPreview, SheetResult } from '../lib/preview'
import { plural, t } from '../i18n/it'
import { buttonClass } from './Dialog'

type Props = {
  sheets: { id: SheetId; title: string }[]
  focus: SheetId | null
  onFocus: (id: SheetId) => void
  sheet: (id: SheetId) => SheetPreview
  /** Settings changed and the preview has not been asked again yet. */
  waiting: boolean
  multipage: number[]
  onMultipage: (id: number, on: boolean) => void
}

const pt = (value: number) => String(value).replace('.', ',')

export function layoutLabel(layout: SheetLayout, pages: number): string {
  if (layout.multipage) {
    return t(`preview.layout.multipage.${pages === 1 ? 'one' : 'many'}`, { n: pages, pt: pt(layout.font_pt) })
  }
  return t(layout.columns === 1 ? 'preview.layout.one' : 'preview.layout.two', { pt: pt(layout.font_pt) })
}

export function ExportPreview({ sheets, focus, onFocus, sheet, waiting, multipage, onMultipage }: Props) {
  if (!sheets.length) {
    return <p className="m-auto max-w-sm text-center text-sm text-ink-300">{t('preview.none')}</p>
  }
  const index = Math.max(0, sheets.findIndex((s) => s.id === focus))
  const current = sheets[index]
  const state = sheet(current.id)
  const result = state.current ?? state.shown
  const stale = !state.current
  const busy = stale && (waiting || state.loading)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-ink-700 px-4 py-2">
        <h2 className="text-sm font-semibold text-ink-50">{t('preview.title')}</h2>
        {sheets.length > 1 ? (
          <div className="flex items-center gap-1">
            <NavButton label={t('preview.prev')} disabled={index === 0} onClick={() => onFocus(sheets[index - 1].id)}>
              ‹
            </NavButton>
            <select
              aria-label={t('preview.choose')}
              value={String(current.id)}
              onChange={(event) => onFocus(sheets.find((s) => String(s.id) === event.target.value)!.id)}
              className="max-w-56 rounded border border-ink-600 bg-ink-900 px-2 py-0.5 text-sm"
            >
              {sheets.map((s) => (
                <option key={s.id} value={String(s.id)}>
                  {s.title}
                </option>
              ))}
            </select>
            <NavButton
              label={t('preview.next')}
              disabled={index === sheets.length - 1}
              onClick={() => onFocus(sheets[index + 1].id)}
            >
              ›
            </NavButton>
            <span className="text-xs text-ink-300">{t('preview.position', { n: index + 1, total: sheets.length })}</span>
          </div>
        ) : (
          <span className="text-sm text-ink-200">{current.title}</span>
        )}
        <span className="ml-auto flex items-center gap-3 text-xs">
          {busy ? <span className="text-ink-300">{result ? t('preview.updating') : ''}</span> : null}
          {result?.status === 'done' && !stale ? <SheetLabel result={result} /> : null}
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto bg-ink-950/40 p-4">
        {!result ? (
          <p className="mt-10 text-center text-sm text-ink-300">{t('preview.loading')}</p>
        ) : result.status === 'error' ? (
          <p className="mt-10 text-center text-sm text-red-400">{result.message}</p>
        ) : (
          <div className={`mx-auto space-y-4 transition-opacity ${stale ? 'opacity-50' : ''}`} style={{ width: PAGE_WIDTH }}>
            {result.eventCount === 0 ? (
              <p className="mt-6 text-center text-sm text-ink-300">{t('preview.empty')}</p>
            ) : !result.fits ? (
              <TooBig
                title={current.title}
                count={result.eventCount}
                onMultipage={typeof current.id === 'number' ? () => onMultipage(current.id as number, true) : undefined}
              />
            ) : null}
            {typeof current.id === 'number' && multipage.includes(current.id) ? (
              <button
                type="button"
                className="rounded px-1 text-xs text-accent hover:bg-ink-700"
                onClick={() => onMultipage(current.id as number, false)}
              >
                {t('preview.backToOne')}
              </button>
            ) : null}
            {result.pages.map((url, page) => (
              <img
                key={url}
                src={url}
                alt={t('preview.page', { n: page + 1 })}
                className="block w-full bg-white shadow-lg shadow-black/50"
                draggable={false}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/** A whole A4 page in sight: as wide as the column allows, as tall as the screen allows. */
const PAGE_WIDTH = 'min(100%, calc((100vh - 9rem) * 0.7071))'

function SheetLabel({ result }: { result: Extract<SheetResult, { status: 'done' }> }) {
  if (result.eventCount === 0) return <span className="text-warn">{plural('preview.events', 0)}</span>
  return (
    <>
      <span className="text-ink-300">{plural('preview.events', result.eventCount)}</span>
      {result.fits && result.layout ? (
        <span className="rounded bg-ink-700 px-1.5 py-0.5 text-ink-100">
          {layoutLabel(result.layout, result.pages.length)}
        </span>
      ) : (
        <span className="rounded bg-red-500/15 px-1.5 py-0.5 font-medium text-red-400">{t('preview.tooBig')}</span>
      )}
    </>
  )
}

function TooBig({ title, count, onMultipage }: { title: string; count: number; onMultipage?: () => void }) {
  return (
    <div className="space-y-3 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm">
      <p className="font-medium text-red-300">{t('preview.tooBig')}</p>
      <p className="text-ink-100">{t('preview.tooBigText', { group: title, n: count })}</p>
      {onMultipage ? (
        <button type="button" className={buttonClass.secondary} onClick={onMultipage}>
          {t('preview.multipage')}
        </button>
      ) : null}
    </div>
  )
}

type NavProps = { label: string; disabled: boolean; onClick: () => void; children: string }

function NavButton({ label, disabled, onClick, children }: NavProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded px-2 py-0.5 text-lg leading-none text-ink-200 hover:bg-ink-700 disabled:opacity-30"
    >
      {children}
    </button>
  )
}
