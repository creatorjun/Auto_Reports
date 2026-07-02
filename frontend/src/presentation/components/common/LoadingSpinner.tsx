// frontend/src/presentation/components/common/LoadingSpinner.tsx
export default function LoadingSpinner({ text = '로딩 중...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-8 h-8 border-[2.5px] border-apple-divider border-t-brand-600 rounded-full animate-spin" />
      <p className="text-[13px] text-apple-light">{text}</p>
    </div>
  )
}
