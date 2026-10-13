// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Mode and format of the export (SPEC §8.1, §9.1): three modes; PDF and/or PNG,
// never neither -- the last ticked box cannot be unticked -- and the PNG
// resolution only when PNG is on.
import type { Dpi, ExportFormat, ExportMode } from '../lib/api'
import { t } from '../i18n/it'

const MODES: ExportMode[] = ['per_group', 'single_pdf', 'combined']
const FORMATS: ExportFormat[] = ['pdf', 'png']
const DPIS: Dpi[] = [150, 200, 300]

export function ModeChoice({ mode, onChange }: { mode: ExportMode; onChange: (mode: ExportMode) => void }) {
  return (
    <div role="radiogroup" aria-label={t('export.mode.title')} className="space-y-1">
      {MODES.map((each) => (
        <label key={each} className="flex cursor-pointer items-start gap-2 rounded px-1 py-0.5 hover:bg-ink-800">
          <input
            type="radio"
            name="export-mode"
            checked={mode === each}
            onChange={() => onChange(each)}
            className="mt-1 h-4 w-4 accent-[var(--color-accent)]"
          />
          <span>
            <span className="block text-sm text-ink-50">{t(`export.mode.${each}`)}</span>
            <span className="block text-xs text-ink-300">{t(`export.mode.${each}.hint`)}</span>
          </span>
        </label>
      ))}
    </div>
  )
}

type FormatProps = {
  formats: ExportFormat[]
  dpi: Dpi
  onFormats: (formats: ExportFormat[]) => void
  onDpi: (dpi: Dpi) => void
}

export function FormatChoice({ formats, dpi, onFormats, onDpi }: FormatProps) {
  const toggle = (format: ExportFormat) =>
    onFormats(
      formats.includes(format) ? formats.filter((f) => f !== format) : FORMATS.filter((f) => f === format || formats.includes(f)),
    )
  return (
    <div className="space-y-2">
      <div className="flex gap-4">
        {FORMATS.map((format) => {
          const on = formats.includes(format)
          const last = on && formats.length === 1
          return (
            <label
              key={format}
              title={last ? t('export.format.lastOne') : undefined}
              className={`flex items-center gap-2 text-sm ${last ? 'cursor-default' : 'cursor-pointer'}`}
            >
              <input
                type="checkbox"
                checked={on}
                disabled={last}
                onChange={() => toggle(format)}
                className="h-4 w-4 accent-[var(--color-accent)]"
              />
              {t(`export.format.${format}`)}
            </label>
          )
        })}
      </div>
      {formats.includes('png') ? (
        <div className="flex items-center gap-2 text-sm">
          <span id="export-dpi" className="text-ink-300">
            {t('export.format.dpi')}
          </span>
          <div role="radiogroup" aria-labelledby="export-dpi" className="flex overflow-hidden rounded-md border border-ink-600">
            {DPIS.map((each) => (
              <button
                key={each}
                type="button"
                role="radio"
                aria-checked={dpi === each}
                onClick={() => onDpi(each)}
                className={`px-2.5 py-0.5 text-xs ${
                  dpi === each ? 'bg-accent font-medium text-ink-950' : 'text-ink-200 hover:bg-ink-700'
                }`}
              >
                {t(`export.format.dpi.${each}`)}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
