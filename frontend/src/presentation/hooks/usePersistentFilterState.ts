// frontend/src/presentation/hooks/usePersistentFilterState.ts
import { createContext, useContext, useMemo, useSyncExternalStore } from 'react'
import type { Dispatch, SetStateAction } from 'react'

export const FilterOwnerContext = createContext<string | null>(null)

function createFilter<T>(storageKey: string | null, initial: T | (() => T)) {
  function restore(): T {
    if (storageKey) {
      try {
        const saved = window.localStorage.getItem(storageKey)
        if (saved !== null) return JSON.parse(saved)
      } catch {}
    }
    return typeof initial === 'function' ? (initial as () => T)() : initial
  }

  let value = restore()
  const listeners = new Set<() => void>()
  return {
    snapshot: () => value,
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => { listeners.delete(listener) }
    },
    update(action: SetStateAction<T>) {
      const next = typeof action === 'function' ? (action as (previous: T) => T)(value) : action
      if (storageKey) {
        try {
          window.localStorage.setItem(storageKey, JSON.stringify(next))
        } catch {}
      }
      if (Object.is(next, value)) return
      value = next
      listeners.forEach((listener) => listener())
    },
  }
}

export function usePersistentFilterState<T>(key: string, initial: T | (() => T)): [T, Dispatch<SetStateAction<T>>] {
  const owner = useContext(FilterOwnerContext)
  const filter = useMemo(() => createFilter(
    owner === null ? null : `auto-reports-filters:v1:${JSON.stringify([owner, key])}`,
    initial,
  ), [owner, key])
  return [useSyncExternalStore(filter.subscribe, filter.snapshot, filter.snapshot), filter.update]
}
