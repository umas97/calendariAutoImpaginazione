// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The folder picker inside the program (SPEC §10.3): only folders, only inside
// the home -- the server refuses anything else. A click opens a folder; the
// button at the bottom chooses the one open. A folder that does not exist yet
// (the default one before the first export) opens on its nearest parent.
//
// With `pickFile` it chooses a backup instead (SPEC §10.4): the `.db` files are
// listed under the folders, newest first; a click selects one, a double click
// chooses it.
import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, ApiError, type FileEntry } from '../lib/api'
import { longDateTime } from '../lib/dates'
import { t } from '../i18n/it'
import { buttonClass, Dialog } from './Dialog'

type Props = {
  initial: string
  home: string
  onChoose: (path: string) => void
  onClose: () => void
  /** Choose a `.db` file, not a folder. */
  pickFile?: boolean
  title?: string
  chooseLabel?: string
}

/** `~/Documenti/…` for a path in the home. */
export function tildePath(path: string, home: string): string {
  if (path === home) return '~'
  return path.startsWith(`${home}/`) ? `~${path.slice(home.length)}` : path
}

const parentOf = (path: string) => path.replace(/\/[^/]+\/?$/, '') || '/'

/** `850 KB`, `1,2 MB`. */
function fileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return t('folders.size.kb', { n: Math.max(1, Math.round(bytes / 1024)) })
  return t('folders.size.mb', { n: (bytes / (1024 * 1024)).toFixed(1).replace('.', ',') })
}

export function FolderBrowser({ initial, home, onChoose, onClose, pickFile, title, chooseLabel }: Props) {
  const [path, setPath] = useState(initial)
  const [hidden, setHidden] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [newName, setNewName] = useState<string | null>(null)
  const [newError, setNewError] = useState<string | null>(null)
  const listing = useQuery({
    queryKey: ['folders', path, hidden, pickFile ?? false],
    queryFn: () => api.folders(path, hidden, pickFile ? 'db' : undefined),
    retry: false,
    staleTime: 0,
  })
  useEffect(() => setSelected(null), [path])

  // Not there (yet): one level up, until something exists -- the home always does.
  const error = listing.error as ApiError | null
  useEffect(() => {
    if (error?.status === 404 && path !== home && path.startsWith(home)) setPath(parentOf(path))
  }, [error, path, home])

  const create = async () => {
    const name = (newName ?? '').trim()
    if (!name || !listing.data) return
    try {
      const made = await api.createFolder(listing.data.path, name)
      setNewName(null)
      setNewError(null)
      setPath(made.path)
    } catch (err) {
      setNewError((err as Error).message)
    }
  }

  const current = listing.data
  const files = current?.files ?? []
  const chosen = pickFile ? selected : (current?.path ?? null)
  return (
    <Dialog
      title={title ?? t('folders.title')}
      onClose={onClose}
      width="max-w-xl"
      footer={
        <>
          <button className={buttonClass.secondary} onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button className={buttonClass.primary} disabled={!chosen} onClick={() => chosen && onChoose(chosen)}>
            {chooseLabel ?? t('folders.choose')}
          </button>
        </>
      }
    >
      <div className="flex items-center gap-1">
        <IconButton label={t('folders.up')} disabled={!current?.parent} onClick={() => current?.parent && setPath(current.parent)}>
          ↑
        </IconButton>
        <IconButton label={t('folders.home')} onClick={() => setPath(home)}>
          ⌂
        </IconButton>
        <p className="min-w-0 flex-1 truncate rounded bg-ink-900 px-2 py-1 font-mono text-xs text-ink-100" title={current?.path}>
          {current ? tildePath(current.path, home) : '…'}
        </p>
      </div>
      <div className="h-72 overflow-y-auto rounded border border-ink-700">
        {listing.isLoading ? (
          <p className="p-3 text-ink-300">{t('folders.loading')}</p>
        ) : error && error.status !== 404 ? (
          <p className="p-3 text-red-400">{error.message}</p>
        ) : current && current.folders.length === 0 && files.length === 0 ? (
          <p className="p-3 text-ink-300">{pickFile ? t('folders.emptyFiles') : t('folders.empty')}</p>
        ) : (
          <ul>
            {current?.folders.map((folder) => (
              <li key={folder.path}>
                <button
                  type="button"
                  onClick={() => setPath(folder.path)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-ink-700"
                >
                  <span aria-hidden className="text-ink-300">
                    ▸
                  </span>
                  <span className="truncate">{folder.name}</span>
                </button>
              </li>
            ))}
            {files.map((file) => (
              <FileRow
                key={file.path}
                file={file}
                selected={file.path === selected}
                onSelect={() => setSelected(file.path)}
                onChoose={() => onChoose(file.path)}
              />
            ))}
          </ul>
        )}
      </div>
      <div className="flex items-center gap-3">
        {pickFile ? null : newName === null ? (
          <button type="button" className="rounded px-1 text-accent hover:bg-ink-700" onClick={() => setNewName('')}>
            + {t('folders.new')}
          </button>
        ) : (
          <NewFolderInput
            value={newName}
            onChange={setNewName}
            onSubmit={() => void create()}
            onCancel={() => {
              setNewName(null)
              setNewError(null)
            }}
          />
        )}
        <label className="ml-auto flex cursor-pointer items-center gap-2 text-ink-200">
          <input
            type="checkbox"
            checked={hidden}
            onChange={(event) => setHidden(event.target.checked)}
            className="h-4 w-4 accent-[var(--color-accent)]"
          />
          {t('folders.hidden')}
        </label>
      </div>
      {newError ? <p className="text-red-400">{newError}</p> : null}
    </Dialog>
  )
}

type FileProps = { file: FileEntry; selected: boolean; onSelect: () => void; onChoose: () => void }

function FileRow({ file, selected, onSelect, onChoose }: FileProps) {
  return (
    <li>
      <button
        type="button"
        aria-pressed={selected}
        onClick={onSelect}
        onDoubleClick={onChoose}
        className={`flex w-full items-center gap-2 px-3 py-1.5 text-left ${
          selected ? 'bg-accent/20 text-ink-50' : 'hover:bg-ink-700'
        }`}
      >
        <span aria-hidden className="text-ink-300">
          ◆
        </span>
        <span className="min-w-0 flex-1 truncate">{file.name}</span>
        <span className="shrink-0 text-xs text-ink-300">
          {longDateTime(file.modified)} · {fileSize(file.size)}
        </span>
      </button>
    </li>
  )
}

type InputProps = { value: string; onChange: (v: string) => void; onSubmit: () => void; onCancel: () => void }

function NewFolderInput({ value, onChange, onSubmit, onCancel }: InputProps) {
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => ref.current?.focus(), [])
  return (
    <input
      ref={ref}
      value={value}
      aria-label={t('folders.new')}
      placeholder={t('folders.newPlaceholder')}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === 'Enter') onSubmit()
        if (event.key === 'Escape') {
          // Close the field, not the dialog.
          event.preventDefault()
          event.stopPropagation()
          onCancel()
        }
      }}
      className="w-64 rounded border border-ink-600 bg-ink-900 px-2 py-1 text-sm"
    />
  )
}

type IconProps = { label: string; onClick: () => void; disabled?: boolean; children: string }

function IconButton({ label, onClick, disabled, children }: IconProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded px-2 py-0.5 text-base text-ink-200 hover:bg-ink-700 disabled:opacity-40"
    >
      {children}
    </button>
  )
}
