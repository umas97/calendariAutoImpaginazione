// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The choices the program remembers (SPEC §10.2). A save updates the cache at
// once, so the screen never waits for it; the server's answer (which drops ids
// that are gone) replaces it.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Settings } from './api'

export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: api.settings, staleTime: Infinity })
}

export function useSaveSetting<K extends keyof Settings>(key: K) {
  const client = useQueryClient()
  const store = (value: Settings[K]) =>
    client.setQueryData<Settings>(['settings'], (old) => (old ? { ...old, [key]: value } : old))
  return useMutation({
    mutationFn: (value: Settings[K]) => api.putSetting(key, value),
    onMutate: store,
    onSuccess: (answer) => store(answer.value),
  })
}
