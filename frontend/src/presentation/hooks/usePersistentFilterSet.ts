// frontend/src/presentation/hooks/usePersistentFilterSet.ts
import { useCallback, useMemo, type Dispatch, type SetStateAction } from 'react'
import { usePersistentFilterState } from './usePersistentFilterState'

type FilterSet = Set<string> | null

export function usePersistentFilterSet(
  key: string,
  initial: FilterSet | (() => FilterSet) = null,
): [FilterSet, Dispatch<SetStateAction<FilterSet>>] {
  const [values, setValues] = usePersistentFilterState<string[] | null>(key, () => {
    const selected = typeof initial === 'function' ? initial() : initial
    return selected === null ? null : [...selected]
  })
  const selected = useMemo(() => values === null ? null : new Set(values), [values])
  const setSelected = useCallback<Dispatch<SetStateAction<FilterSet>>>((action) => {
    setValues((previous) => {
      const next = typeof action === 'function'
        ? action(previous === null ? null : new Set(previous))
        : action
      return next === null ? null : [...next]
    })
  }, [setValues])
  return [selected, setSelected]
}
