// frontend/src/presentation/hooks/useTablePreferences.ts
import { useCallback, useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'

interface TableSort<K extends string> {
  key: K
  direction: 'asc' | 'desc'
}

interface TablePreferences<K extends string> {
  sort: TableSort<K> | null
  widths: Record<K, number>
}

function readPreferences<K extends string>(storageKey: string | undefined, defaults: Record<K, number>, minimums: number | Record<K, number>): TablePreferences<K> {
  const fallback: TablePreferences<K> = { sort: null, widths: { ...defaults } }
  if (!storageKey) return fallback
  try {
    const saved = JSON.parse(window.localStorage.getItem(`auto-reports-table:${storageKey}`) ?? 'null')
    if (!saved || saved.version !== 1) return fallback
    const columns = Object.keys(defaults) as K[]
    const validWidths = saved.widths && columns.every((key) => {
      const width = saved.widths[key]
      const minimum = typeof minimums === 'number' ? minimums : minimums[key]
      return typeof width === 'number' && Number.isFinite(width) && width >= minimum - 1e-9 && width <= 1
    }) && Math.abs(columns.reduce((sum, key) => sum + saved.widths[key], 0) - 1) < 1e-6
    const sort = saved.sort && columns.includes(saved.sort.key) && ['asc', 'desc'].includes(saved.sort.direction)
      ? { key: saved.sort.key as K, direction: saved.sort.direction as 'asc' | 'desc' }
      : null
    return { sort, widths: validWidths ? Object.fromEntries(columns.map((key) => [key, saved.widths[key]])) as Record<K, number> : fallback.widths }
  } catch {
    return fallback
  }
}

export function useTablePreferences<K extends string>(storageKey: string | undefined, defaultWidths: Record<K, number>, minWidths: number | Record<K, number>) {
  const [state, setState] = useState(() => ({ storageKey, preferences: readPreferences(storageKey, defaultWidths, minWidths) }))
  let current = state
  if (state.storageKey !== storageKey) {
    current = { storageKey, preferences: readPreferences(storageKey, defaultWidths, minWidths) }
    setState(current)
  }
  const { preferences } = current
  useEffect(() => {
    if (!storageKey) return
    try {
      window.localStorage.setItem(`auto-reports-table:${storageKey}`, JSON.stringify({ version: 1, ...preferences }))
    } catch {
      return
    }
  }, [storageKey, preferences])

  const setSort: Dispatch<SetStateAction<TableSort<K> | null>> = useCallback((value) => setState((previous) => {
    const sort = typeof value === 'function' ? value(previous.preferences.sort) : value
    return sort === previous.preferences.sort ? previous : { ...previous, preferences: { ...previous.preferences, sort } }
  }), [])
  const setWidths: Dispatch<SetStateAction<Record<K, number>>> = useCallback((value) => setState((previous) => {
    const widths = typeof value === 'function' ? value(previous.preferences.widths) : value
    return widths === previous.preferences.widths ? previous : { ...previous, preferences: { ...previous.preferences, widths } }
  }), [])
  return { ...preferences, setSort, setWidths }
}
