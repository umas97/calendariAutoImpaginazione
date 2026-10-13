// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A category's colour (SPEC §6.2): the twelve palette colours first, then any
// colour through the system picker. The palette comes from the server, which
// also assigns it, so there is one list. The free picker reports every move of
// the cursor; only the final `change` is saved.
import { useEffect, useRef } from 'react'
import { usePalette } from '../lib/taxonomy'
import { t } from '../i18n/it'
import { Popover } from './Popover'

type Props = {
  value: string
  onChange: (color: string) => void
}

export function ColorPicker({ value, onChange }: Props) {
  const { data: palette = [] } = usePalette()
  return (
    <Popover
      label={t('taxonomy.color')}
      align="start"
      triggerClassName="grid h-7 w-7 shrink-0 place-items-center rounded-md hover:bg-ink-700"
      trigger={<Swatch color={value} />}
    >
      {(close) => (
        <div className="w-52 space-y-2 px-3 py-2">
          <p className="text-xs text-ink-300">{t('taxonomy.color.palette')}</p>
          <div className="grid grid-cols-6 gap-1.5">
            {palette.map((color) => (
              <button
                key={color}
                type="button"
                title={color}
                aria-label={color}
                aria-pressed={color === value}
                onClick={() => {
                  close()
                  if (color !== value) onChange(color)
                }}
                className={`h-6 w-6 rounded-full ring-offset-2 ring-offset-ink-800 ${
                  color === value ? 'ring-2 ring-ink-50' : 'hover:ring-2 hover:ring-ink-400'
                }`}
                style={{ background: color }}
              />
            ))}
          </div>
          <FreeColor value={value} onChange={(color) => color !== value && onChange(color)} />
        </div>
      )}
    </Popover>
  )
}

function FreeColor({ value, onChange }: Props) {
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const input = ref.current
    if (!input) return
    const commit = () => onChange(input.value.toUpperCase())
    input.addEventListener('change', commit)
    return () => input.removeEventListener('change', commit)
  }, [onChange])
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-md py-1 text-ink-200 hover:text-ink-50">
      <input
        ref={ref}
        type="color"
        defaultValue={value.toLowerCase()}
        className="h-6 w-8 cursor-pointer rounded border-0 bg-transparent p-0"
      />
      {t('taxonomy.color.custom')}
    </label>
  )
}

export function Swatch({ color }: { color: string }) {
  return (
    <span
      aria-hidden
      className="block h-4 w-4 rounded-full border border-black/20"
      style={{ background: color }}
    />
  )
}
