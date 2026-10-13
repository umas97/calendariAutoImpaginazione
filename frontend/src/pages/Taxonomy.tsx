// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Gruppi e categorie" (SPEC §9.1): the two lists side by side, and the switch
// that brings back the archived ones -- the groups of past years.
import { useState } from 'react'
import { TaxonomyList } from '../components/TaxonomyList'
import { t } from '../i18n/it'

export function TaxonomyPage() {
  const [showArchived, setShowArchived] = useState(false)
  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <div className="flex items-start gap-3">
        <label className="flex shrink-0 cursor-pointer items-center gap-2 text-sm text-ink-100">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => setShowArchived(event.target.checked)}
            className="h-4 w-4 accent-[var(--color-accent)]"
          />
          {t('taxonomy.showArchived')}
        </label>
        <p className="text-sm text-ink-300">{t('taxonomy.archivedHint')}</p>
      </div>
      <div className="grid grid-cols-2 items-start gap-6">
        <TaxonomyList kind="groups" showArchived={showArchived} />
        <TaxonomyList kind="categories" showArchived={showArchived} />
      </div>
    </div>
  )
}
