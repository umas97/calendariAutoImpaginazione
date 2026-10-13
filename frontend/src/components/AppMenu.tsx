// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The "⋯" menu at the right of the bar (SPEC §9.1). The backup entries are
// shown but disabled until Phase 6 brings them: the menu already has its final
// shape, and nothing in it pretends to work.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'
import { MenuItem, Popover } from './Popover'

type Props = {
  /** `null` when this server cannot stop itself: then there is no "Esci". */
  onQuit: (() => void) | null
  quitting: boolean
}

export function AppMenu({ onQuit, quitting }: Props) {
  const [about, setAbout] = useState(false)
  return (
    <>
      <Popover
        label={t('menu.label')}
        trigger={<span aria-hidden>⋯</span>}
        triggerClassName="rounded-md px-3 py-0.5 text-lg leading-none text-ink-200 hover:bg-ink-700"
      >
        {(close) => (
          <>
            <MenuItem disabled title={t('menu.soon')} onClick={close}>
              {t('menu.backup')}
            </MenuItem>
            <MenuItem disabled title={t('menu.soon')} onClick={close}>
              {t('menu.restore')}
            </MenuItem>
            <MenuItem disabled title={t('menu.soon')} onClick={close}>
              {t('menu.backupFolder')}
            </MenuItem>
            <div className="my-1 border-t border-ink-600" />
            <MenuItem
              onClick={() => {
                close()
                setAbout(true)
              }}
            >
              {t('menu.about')}
            </MenuItem>
            {onQuit ? (
              <MenuItem
                disabled={quitting}
                onClick={() => {
                  close()
                  onQuit()
                }}
              >
                {quitting ? t('nav.quitting') : t('nav.quit')}
              </MenuItem>
            ) : null}
          </>
        )}
      </Popover>
      {about ? <AboutDialog onClose={() => setAbout(false)} /> : null}
    </>
  )
}

function AboutDialog({ onClose }: { onClose: () => void }) {
  const { data } = useQuery({ queryKey: ['health'], queryFn: api.health })
  return (
    <Dialog
      title={t('about.title')}
      onClose={onClose}
      footer={
        <button className={buttonClass.primary} onClick={onClose} autoFocus>
          {t('common.close')}
        </button>
      }
    >
      <p className="text-base font-semibold text-ink-50">{t('app.name')}</p>
      <p className="text-ink-200">{t('app.description')}</p>
      {data ? <p className="text-ink-300">{t('about.version', { version: data.version })}</p> : null}
      <p className="text-ink-300">{t('about.offline')}</p>
      <p className="text-ink-300">{t('about.license')}</p>
    </Dialog>
  )
}
