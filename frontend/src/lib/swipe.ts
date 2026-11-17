// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Two-finger horizontal swipes on a touchpad (SPEC §9.1): the browser sees
// them as wheel events with a horizontal delta. Fingers moving left turn to
// the next page, right to the previous one, like turning a page. One gesture
// turns one page however long it is: after a turn the gesture is spent until
// the wheel has been quiet for a moment (the touchpad's inertia included).
import { useEffect, useRef, type RefObject } from 'react'

/** Horizontal travel, in pixels, that turns a page. */
export const SWIPE_THRESHOLD = 60
/** Quiet time, in milliseconds, that ends a gesture. */
export const SWIPE_QUIET_MS = 220
/** One wheel "line" in pixels, for mice that report lines. */
const LINE_PX = 16

export type SwipeState = { travel: number; spent: boolean; last: number }

export const freshSwipe = (): SwipeState => ({ travel: 0, spent: false, last: -Infinity })

/**
 * One wheel event through the gesture: `'next'`, `'prev'`, `null` (nothing to
 * do), or `'ignore'` when the event is not a horizontal swipe and must be left
 * to the browser (vertical scrolling, pinch zoom).
 */
export function swipeStep(
  state: SwipeState,
  event: { deltaX: number; deltaY: number; deltaMode: number; ctrlKey: boolean },
  now: number,
): 'next' | 'prev' | null | 'ignore' {
  if (event.ctrlKey || Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return 'ignore'
  if (now - state.last > SWIPE_QUIET_MS) {
    state.travel = 0
    state.spent = false
  }
  state.last = now
  if (state.spent) return null
  state.travel += event.deltaX * (event.deltaMode === 1 ? LINE_PX : 1)
  if (Math.abs(state.travel) < SWIPE_THRESHOLD) return null
  state.spent = true
  return state.travel > 0 ? 'next' : 'prev'
}

/** Turn pages with horizontal swipes over `target`. */
export function useHorizontalSwipe(
  target: RefObject<HTMLElement | null>,
  onPrev: () => void,
  onNext: () => void,
) {
  const handlers = useRef({ onPrev, onNext })
  handlers.current = { onPrev, onNext }

  useEffect(() => {
    const node = target.current
    if (!node) return
    const state = freshSwipe()
    const onWheel = (event: WheelEvent) => {
      const step = swipeStep(state, event, event.timeStamp)
      if (step === 'ignore') return
      // Also keeps Chromium from going back or forward in its history.
      event.preventDefault()
      if (step === 'next') handlers.current.onNext()
      else if (step === 'prev') handlers.current.onPrev()
    }
    node.addEventListener('wheel', onWheel, { passive: false })
    return () => node.removeEventListener('wheel', onWheel)
  }, [target])
}
