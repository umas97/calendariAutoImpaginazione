// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The routes, one per tab (SPEC §9.1). Readable and stable, because they help in
// debugging -- but the window has no address bar, so nothing may be reachable
// *only* by typing one. An unknown path lands on the calendar: in a program
// where nobody types URLs, it can only be a stale link.
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { CalendarPage } from './pages/Calendar'
import { ExportPage } from './pages/Export'
import { TaxonomyPage } from './pages/Taxonomy'

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<CalendarPage />} />
        <Route path="/gruppi" element={<TaxonomyPage />} />
        <Route path="/export" element={<ExportPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}
