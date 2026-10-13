// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// A button that opens a small panel under itself: row menus, the colour picker,
// the "⋯" menu. The panel is `fixed`, measured from the button, so a scrolling
// list cannot clip it; it closes on a click elsewhere, Esc, scroll or resize.
import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'

type Props = {
  /** Read by screen readers and shown as the tooltip. */
  label: string
  trigger: ReactNode
  triggerClassName?: string
  /** So that a `<label htmlFor>` can point at the button. */
  triggerId?: string
  /** Which edge of the button the panel lines up with. */
  align?: 'start' | 'end'
  children: (close: () => void) => ReactNode
}

/** Room the panel needs below the button before it opens upwards instead. */
const ROOM_BELOW = 330

export function Popover({ label, trigger, triggerClassName, triggerId, align = 'end', children }: Props) {
  const [anchor, setAnchor] = useState<DOMRect | null>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setAnchor(null), [])

  useEffect(() => {
    if (!anchor) return
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node
      if (!panelRef.current?.contains(target) && !buttonRef.current?.contains(target)) close()
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      // Inside a <dialog>, Esc must close the panel, not the dialog too.
      event.preventDefault()
      event.stopPropagation()
      close()
      buttonRef.current?.focus()
    }
    const onScroll = (event: Event) => {
      if (!panelRef.current?.contains(event.target as Node)) close()
    }
    window.addEventListener('mousedown', onPointer)
    window.addEventListener('keydown', onKey, true)
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', close)
    return () => {
      window.removeEventListener('mousedown', onPointer)
      window.removeEventListener('keydown', onKey, true)
      window.removeEventListener('scroll', onScroll, true)
      window.removeEventListener('resize', close)
    }
  }, [anchor, close])

  let style: CSSProperties | undefined
  if (anchor) {
    const vertical =
      anchor.bottom + ROOM_BELOW > window.innerHeight
        ? { bottom: window.innerHeight - anchor.top + 4 }
        : { top: anchor.bottom + 4 }
    const horizontal =
      align === 'end' ? { right: window.innerWidth - anchor.right } : { left: anchor.left }
    style = { ...vertical, ...horizontal }
  }

  return (
    <>
      <button
        ref={buttonRef}
        id={triggerId}
        type="button"
        aria-label={label}
        title={label}
        aria-expanded={anchor !== null}
        className={triggerClassName}
        onClick={() => setAnchor((open) => (open ? null : buttonRef.current!.getBoundingClientRect()))}
      >
        {trigger}
      </button>
      {anchor ? (
        <div
          ref={panelRef}
          style={style}
          className="fixed z-50 min-w-44 rounded-md border border-ink-600 bg-ink-800 py-1 text-sm shadow-xl"
        >
          {children(close)}
        </div>
      ) : null}
    </>
  )
}

type ItemProps = {
  onClick: () => void
  children: ReactNode
  disabled?: boolean
  danger?: boolean
  title?: string
}

export function MenuItem({ onClick, children, disabled, danger, title }: ItemProps) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`block w-full px-3 py-1.5 text-left hover:bg-ink-700 disabled:cursor-default disabled:text-ink-400 disabled:hover:bg-transparent ${danger ? 'text-red-400' : ''}`}
    >
      {children}
    </button>
  )
}
