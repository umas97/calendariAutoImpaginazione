// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The place field, with the places already used as suggestions (SPEC §7.5).
// There is no table of places: the server lists the distinct ones, most used
// first. ↑ ↓ choose, Enter takes, Esc closes the list (and only the list).
import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

type Props = {
  id: string
  value: string
  onChange: (value: string) => void
  invalid?: boolean
}

export function PlaceInput({ id, value, onChange, invalid }: Props) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const query = value.trim()
  const { data = [] } = useQuery({
    queryKey: ['places', query],
    queryFn: () => api.places(query),
    enabled: open,
    placeholderData: keepPreviousData,
  })
  const suggestions = data.filter((place) => place !== value)
  const shown = open && suggestions.length > 0

  const take = (place: string) => {
    onChange(place)
    setOpen(false)
    setActive(-1)
  }

  return (
    <div className="relative">
      <input
        id={id}
        value={value}
        maxLength={120}
        autoComplete="off"
        role="combobox"
        aria-expanded={shown}
        aria-controls={`${id}-list`}
        aria-invalid={invalid}
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
          setActive(-1)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (!shown) return
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault()
            const step = event.key === 'ArrowDown' ? 1 : -1
            setActive((index) => (index + step + suggestions.length) % suggestions.length)
          } else if (event.key === 'Enter' && active >= 0 && !event.ctrlKey) {
            event.preventDefault()
            take(suggestions[active])
          } else if (event.key === 'Escape') {
            event.preventDefault() // keep the dialog open
            setOpen(false)
          }
        }}
        className={`w-full rounded border bg-ink-900 px-2 py-1 text-sm outline-none focus:border-accent ${
          invalid ? 'border-red-400' : 'border-ink-600'
        }`}
      />
      {shown ? (
        <ul
          id={`${id}-list`}
          role="listbox"
          className="absolute top-full right-0 left-0 z-10 mt-1 max-h-56 overflow-auto rounded-md border border-ink-600 bg-ink-800 py-1 text-sm shadow-xl"
        >
          {suggestions.map((place, index) => (
            <li
              key={place}
              role="option"
              aria-selected={index === active}
              // mousedown, not click: the input's blur would close the list first.
              onMouseDown={(event) => {
                event.preventDefault()
                take(place)
              }}
              className={`cursor-pointer px-3 py-1 ${index === active ? 'bg-ink-700' : 'hover:bg-ink-700'}`}
            >
              {place}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
