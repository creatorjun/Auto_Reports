import { create } from 'zustand'
import type { ReportDetail } from '@/domain/Report'

interface ReportStore {
  selectedReportId: number | null
  setSelectedReportId: (id: number | null) => void
  currentReport: ReportDetail | null
  setCurrentReport: (r: ReportDetail | null) => void
}

export const useReportStore = create<ReportStore>((set) => ({
  selectedReportId: null,
  setSelectedReportId: (id) => set({ selectedReportId: id }),
  currentReport: null,
  setCurrentReport: (r) => set({ currentReport: r })
}))
