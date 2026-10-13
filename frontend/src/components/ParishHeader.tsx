// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The letterhead of every sheet (SPEC §8.8): the parish name, saved when the
// field is left, and the optional logo with its thumbnail. The server checks
// type and size and says what is wrong in Italian.
import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Parish } from '../lib/api'
import { t } from '../i18n/it'
import { buttonClass } from './Dialog'

export function ParishHeader({ parish }: { parish: Parish }) {
  const client = useQueryClient()
  const store = (answer: Parish) => client.setQueryData(['parish'], answer)
  const [name, setName] = useState(parish.name)
  const file = useRef<HTMLInputElement>(null)

  const saveName = useMutation({
    mutationFn: api.setParishName,
    onSuccess: (answer) => {
      store(answer)
      setName(answer.name)
    },
  })
  const upload = useMutation({ mutationFn: api.uploadLogo, onSuccess: store })
  const remove = useMutation({
    mutationFn: api.removeLogo,
    onSuccess: () => store({ ...parish, logo: null }),
  })

  const commit = () => {
    if (name.trim() !== parish.name) saveName.mutate(name)
  }
  const logoError = upload.error ?? remove.error

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label htmlFor="parish-name" className="block text-sm text-ink-300">
          {t('export.parish.name')}
        </label>
        <input
          id="parish-name"
          value={name}
          maxLength={80}
          placeholder={t('export.parish.namePlaceholder')}
          onChange={(event) => setName(event.target.value)}
          onBlur={commit}
          onKeyDown={(event) => {
            if (event.key === 'Enter') commit()
          }}
          className={`w-full rounded border bg-ink-900 px-2 py-1 text-sm ${
            saveName.error ? 'border-red-400' : 'border-ink-600'
          }`}
        />
        {saveName.error ? (
          <p className="text-sm text-red-400">{saveName.error.message}</p>
        ) : (
          <p className="text-xs text-ink-300">{t('export.parish.nameHint')}</p>
        )}
      </div>
      <div className="space-y-1">
        <span className="block text-sm text-ink-300">{t('export.parish.logo')}</span>
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-20 shrink-0 items-center justify-center overflow-hidden rounded border border-ink-600 bg-white">
            {parish.logo ? (
              <img
                src={`/api/parish/logo?v=${encodeURIComponent(parish.logo.updated_at)}`}
                alt={t('export.parish.logo')}
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <span className="px-1 text-center text-[10px] text-ink-400">{t('export.parish.noLogo')}</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={buttonClass.secondary}
              disabled={upload.isPending}
              onClick={() => file.current?.click()}
            >
              {upload.isPending
                ? t('export.parish.uploading')
                : parish.logo
                  ? t('export.parish.replace')
                  : t('export.parish.upload')}
            </button>
            {parish.logo ? (
              <button
                type="button"
                className={buttonClass.secondary}
                disabled={remove.isPending}
                onClick={() => {
                  upload.reset()
                  remove.mutate()
                }}
              >
                {t('export.parish.remove')}
              </button>
            ) : null}
          </div>
          <input
            ref={file}
            type="file"
            accept="image/png,image/jpeg,image/svg+xml"
            className="hidden"
            onChange={(event) => {
              const chosen = event.target.files?.[0]
              event.target.value = ''
              remove.reset()
              if (chosen) upload.mutate(chosen)
            }}
          />
        </div>
        {logoError ? (
          <p className="text-sm text-red-400">{logoError.message}</p>
        ) : (
          <p className="text-xs text-ink-300">{t('export.parish.logoHint')}</p>
        )}
      </div>
    </div>
  )
}
