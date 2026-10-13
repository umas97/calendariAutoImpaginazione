// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Groups and categories as the interface sees them. The query always holds the
// whole list, archived included: the screen hides what it must, but a reorder
// has to send every id (SPEC §6.3), and the hidden ones keep their places.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type ItemPatch, type Kind, type OrphanChoice, type TaxonomyItem } from './api'

export function useItems(kind: Kind) {
  return useQuery({ queryKey: [kind], queryFn: () => api.items(kind) })
}

export function usePalette() {
  return useQuery({ queryKey: ['palette'], queryFn: api.palette, staleTime: Infinity })
}

/** `ids` moved so that the item at `from` ends up at `to`. */
export function move(ids: number[], from: number, to: number): number[] {
  const next = ids.slice()
  const [id] = next.splice(from, 1)
  next.splice(to, 0, id)
  return next
}

/**
 * The full order after the visible items were rearranged: the visible ones fill
 * the slots visible items occupied, in their new order; hidden ones stay put.
 */
export function mergeOrder(all: TaxonomyItem[], visible: number[]): number[] {
  const shown = new Set(visible)
  let next = 0
  return all.map((item) => (shown.has(item.id) ? visible[next++] : item.id))
}

export function useTaxonomyActions(kind: Kind) {
  const client = useQueryClient()
  const refresh = () => client.invalidateQueries({ queryKey: [kind] })

  const create = useMutation({
    mutationFn: (name: string) => api.createItem(kind, name),
    onSuccess: refresh,
  })

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: ItemPatch }) =>
      api.updateItem(kind, id, patch),
    onSuccess: (item) => {
      client.setQueryData<TaxonomyItem[]>([kind], (old) =>
        old?.map((each) => (each.id === item.id ? item : each)),
      )
      // Events show names and colours: whatever displays them must see the change.
      void client.invalidateQueries({ queryKey: ['events'] })
    },
  })

  // Optimistic: a dragged row must not jump back while the server answers.
  const reorder = useMutation({
    mutationFn: (ids: number[]) => api.reorderItems(kind, ids),
    onMutate: async (ids) => {
      await client.cancelQueries({ queryKey: [kind] })
      const before = client.getQueryData<TaxonomyItem[]>([kind])
      if (before) {
        const byId = new Map(before.map((item) => [item.id, item]))
        client.setQueryData<TaxonomyItem[]>(
          [kind],
          ids.map((id, index) => ({ ...byId.get(id)!, position: index + 1 })),
        )
      }
      return { before }
    },
    onError: (_error, _ids, context) => {
      if (context?.before) client.setQueryData([kind], context.before)
    },
    onSettled: refresh,
  })

  const remove = useMutation({
    mutationFn: ({ id, choice }: { id: number; choice?: OrphanChoice }) =>
      api.deleteItem(kind, id, choice),
    // Orphans may have moved to another item, or gone with their events.
    onSuccess: () =>
      Promise.all(
        (['groups', 'categories', 'events'] as const).map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      ),
  })

  return { create, update, reorder, remove }
}
