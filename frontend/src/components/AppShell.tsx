// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The frame every screen sits in (SPEC §9.1): the name, the three tabs -- always
// visible, so every screen has its way back -- and the "⋯" menu with "Esci",
// which is how a desktop program ends without hunting for its terminal.
// In a browser window it also shows the notice that explains a tab.
import { useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'
import { api } from '../lib/api'
import { t, type MessageKey } from '../i18n/it'
import { AppMenu } from './AppMenu'
import { WindowBanner } from './WindowBanner'

const TABS: { to: string; label: MessageKey }[] = [
  { to: '/', label: 'nav.calendar' },
  { to: '/gruppi', label: 'nav.taxonomy' },
  { to: '/export', label: 'nav.export' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { data: window_ } = useQuery({ queryKey: ['window'], queryFn: api.window })
  const [quitting, setQuitting] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const quit = async () => {
    setQuitting(true)
    try {
      await api.quit()
      setDone(true)
    } catch (err) {
      setError((err as Error).message)
      setQuitting(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <WindowBanner info={window_} />
      <header className="flex items-center gap-6 border-b border-ink-700 bg-ink-850 px-4">
        <h1 className="text-xs font-medium tracking-wide text-ink-300">{t('app.name')}</h1>
        <nav className="flex flex-1 gap-1">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end
              className={({ isActive }) =>
                `border-b-2 px-3 py-2.5 text-sm ${
                  isActive
                    ? 'border-accent font-medium text-ink-50'
                    : 'border-transparent text-ink-300 hover:text-ink-100'
                }`
              }
            >
              {t(tab.label)}
            </NavLink>
          ))}
        </nav>
        <AppMenu onQuit={window_?.can_quit ? () => void quit() : null} quitting={quitting} />
      </header>
      {error ? <p className="border-b border-ink-700 px-4 py-2 text-warn">{error}</p> : null}
      <main className="min-h-0 flex-1 overflow-auto">
        {done ? <p className="p-6">{t('quit.done')}</p> : children}
      </main>
    </div>
  )
}
