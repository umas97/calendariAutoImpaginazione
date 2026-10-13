// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The "⋯" menu at the right of the bar (SPEC §9.1): the backups (§10.4),
// "Informazioni" and "Esci".
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { t } from '../i18n/it'
import { BackupDialog } from './BackupDialog'
import { buttonClass, Dialog } from './Dialog'
import { MenuItem, Popover } from './Popover'
import { Message, RestoreDialog } from './RestoreDialog'

type Props = {
  /** `null` when this server cannot stop itself: then there is no "Esci". */
  onQuit: (() => void) | null
  quitting: boolean
}

type Open = 'about' | 'backup' | 'restore' | { error: string } | null

export function AppMenu({ onQuit, quitting }: Props) {
  const [open, setOpen] = useState<Open>(null)
  const closeDialog = () => setOpen(null)
  const openBackups = async () => {
    try {
      await api.openBackups()
    } catch (err) {
      setOpen({ error: (err as Error).message })
    }
  }
  return (
    <>
      <Popover
        label={t('menu.label')}
        trigger={<span aria-hidden>⋯</span>}
        triggerClassName="rounded-md px-3 py-0.5 text-lg leading-none text-ink-200 hover:bg-ink-700"
      >
        {(close) => (
          <>
            <MenuItem
              onClick={() => {
                close()
                setOpen('backup')
              }}
            >
              {t('menu.backup')}
            </MenuItem>
            <MenuItem
              onClick={() => {
                close()
                setOpen('restore')
              }}
            >
              {t('menu.restore')}
            </MenuItem>
            <MenuItem
              onClick={() => {
                close()
                void openBackups()
              }}
            >
              {t('menu.backupFolder')}
            </MenuItem>
            <div className="my-1 border-t border-ink-600" />
            <MenuItem
              onClick={() => {
                close()
                setOpen('about')
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
      {open === 'about' ? <AboutDialog onClose={closeDialog} /> : null}
      {open === 'backup' ? <BackupDialog onClose={closeDialog} /> : null}
      {open === 'restore' ? <RestoreDialog onClose={closeDialog} /> : null}
      {open !== null && typeof open === 'object' ? (
        <Message title={t('backupFolder.errorTitle')} text={open.error} onClose={closeDialog} />
      ) : null}
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
