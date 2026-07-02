export const fmtDate = (d: string) => d.slice(0, 10)
export const fmtHours = (h: number) => h >= 24 ? `${(h / 24).toFixed(1)}일` : `${h}h`
export const fmtPercent = (n: number, total: number) =>
  total > 0 ? `${Math.round((n / total) * 100)}%` : '0%'
