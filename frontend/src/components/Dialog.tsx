// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A modal on the native <dialog>: the browser traps focus, dims the rest and
// turns Esc into `cancel`, which we route to `onClose` so the owner decides
// (an unsaved form may want to ask first). Mount it to open it.
import { useEffect, useRef, type ReactNode } from 'react'

type Props = {
  title: string
  onClose: () => void
  children: ReactNode
  /** The buttons, right-aligned under the body. */
  footer: ReactNode
  width?: string
}

export function Dialog({ title, onClose, children, footer, width = 'max-w-md' }: Props) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
    return () => dialog?.close()
  }, [])

  return (
    <dialog
      ref={ref}
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      className={`m-auto w-full ${width} rounded-lg border border-ink-600 bg-ink-850 p-0 text-ink-100 shadow-2xl backdrop:bg-black/60`}
    >
      <div className="space-y-4 p-5">
        <h2 className="text-base font-semibold text-ink-50">{title}</h2>
        <div className="space-y-3 text-sm">{children}</div>
      </div>
      <div className="flex justify-end gap-2 border-t border-ink-700 px-5 py-3">{footer}</div>
    </dialog>
  )
}

export const buttonClass = {
  primary:
    'rounded-md bg-accent px-4 py-1.5 text-sm font-medium text-ink-950 hover:brightness-110 disabled:opacity-50',
  danger:
    'rounded-md bg-red-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-400 disabled:opacity-50',
  secondary:
    'rounded-md border border-ink-500 px-4 py-1.5 text-sm hover:bg-ink-700 disabled:opacity-50',
} as const
