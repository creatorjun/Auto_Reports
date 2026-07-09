// frontend/src/app/store/uiStore.ts
import { create } from 'zustand'

interface UiStore {
  isTriggerLoading: boolean
  setTriggerLoading: (v: boolean) => void
  triggerMessage: string | null
  setTriggerMessage: (msg: string | null) => void
}

export const useUiStore = create<UiStore>((set) => ({
  isTriggerLoading: false,
  setTriggerLoading: (v) => set({ isTriggerLoading: v }),
  triggerMessage: null,
  setTriggerMessage: (msg) => set({ triggerMessage: msg }),
}))
