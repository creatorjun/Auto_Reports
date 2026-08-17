// frontend/src/presentation/components/storage/StorageNavigation.tsx
import { useState } from 'react'
import { ArrowLeft, ArrowRight, ArrowUp, ChevronRight, FolderPlus } from 'lucide-react'
import { STORAGE_ENTRY_DRAG_TYPE } from './StorageDrag'

type Props = {
  folder: string
  canGoBack: boolean
  canGoForward: boolean
  onBack: () => void
  onForward: () => void
  onUp: () => void
  onNavigateTo: (index: number) => void
  onCreateFolder: () => void
  isCreateDisabled: boolean
  dragSourceFolder: string | null
  isMoving: boolean
  onMoveToFolder: (destinationFolder: string) => void
}

type NavigationButtonProps = {
  label: string
  disabled: boolean
  onClick: () => void
  children: React.ReactNode
}

function NavigationButton({ label, disabled, onClick, children }: NavigationButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-apple-divider bg-white text-apple-dark transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-600 disabled:cursor-not-allowed disabled:bg-apple-gray/50 disabled:text-apple-light disabled:opacity-45"
    >
      {children}
    </button>
  )
}

export default function StorageNavigation({
  folder,
  canGoBack,
  canGoForward,
  onBack,
  onForward,
  onUp,
  onNavigateTo,
  onCreateFolder,
  isCreateDisabled,
  dragSourceFolder,
  isMoving,
  onMoveToFolder,
}: Props) {
  const breadcrumbs = folder ? folder.split('/') : []
  const [dropTargetFolder, setDropTargetFolder] = useState<string | null>(null)

  const getDropTargetProps = (destinationFolder: string) => {
    const canDrop = dragSourceFolder !== null && destinationFolder !== dragSourceFolder && !isMoving
    return {
      canDrop,
      isDropTarget: canDrop && dropTargetFolder === destinationFolder,
      onDragOver: (event: React.DragEvent) => {
        if (!canDrop || !Array.from(event.dataTransfer.types).includes(STORAGE_ENTRY_DRAG_TYPE)) return
        event.preventDefault()
        event.stopPropagation()
        event.dataTransfer.dropEffect = 'move'
        setDropTargetFolder(destinationFolder)
      },
      onDragLeave: (event: React.DragEvent) => {
        if (event.relatedTarget instanceof Node && event.currentTarget.contains(event.relatedTarget)) return
        setDropTargetFolder(null)
      },
      onDrop: (event: React.DragEvent) => {
        if (!canDrop) return
        event.preventDefault()
        event.stopPropagation()
        setDropTargetFolder(null)
        onMoveToFolder(destinationFolder)
      },
    }
  }

  const rootDropTarget = getDropTargetProps('')

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-x-2 gap-y-2 md:grid-cols-[auto_minmax(0,1fr)_auto]">
      <div className="flex items-center gap-1">
        <NavigationButton label="뒤로 가기" disabled={!canGoBack} onClick={onBack}>
          <ArrowLeft size={15} strokeWidth={1.8} />
        </NavigationButton>
        <NavigationButton label="앞으로 가기" disabled={!canGoForward} onClick={onForward}>
          <ArrowRight size={15} strokeWidth={1.8} />
        </NavigationButton>
        <NavigationButton label="상위 폴더로 이동" disabled={!folder} onClick={onUp}>
          <ArrowUp size={15} strokeWidth={1.8} />
        </NavigationButton>
      </div>

      <nav
        aria-label="현재 폴더 위치"
        className="col-span-2 row-start-2 flex min-w-0 items-center gap-1 overflow-x-auto py-0.5 md:col-span-1 md:col-start-2 md:row-start-1"
      >
        <button
          type="button"
          onClick={() => onNavigateTo(-1)}
          disabled={!folder}
          onDragOver={rootDropTarget.onDragOver}
          onDragLeave={rootDropTarget.onDragLeave}
          onDrop={rootDropTarget.onDrop}
          title={rootDropTarget.canDrop ? '여기에 놓아 보관함으로 이동' : undefined}
          className={`shrink-0 rounded-md px-1.5 py-1 text-[13px] font-medium transition-all disabled:cursor-default ${
            rootDropTarget.isDropTarget
              ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-300'
              : 'text-brand-600 hover:text-brand-700 disabled:text-apple-dark'
          }`}
        >
          보관함
        </button>
        {breadcrumbs.map((segment, index) => {
          const isCurrent = index === breadcrumbs.length - 1
          const destinationFolder = breadcrumbs.slice(0, index + 1).join('/')
          const dropTarget = getDropTargetProps(destinationFolder)
          return (
            <div
              key={`${segment}-${index}`}
              onDragOver={dropTarget.onDragOver}
              onDragLeave={dropTarget.onDragLeave}
              onDrop={dropTarget.onDrop}
              title={dropTarget.canDrop ? `여기에 놓아 ${segment}(으)로 이동` : undefined}
              className={`flex shrink-0 items-center gap-1 rounded-md px-1 py-0.5 transition-all ${
                dropTarget.isDropTarget ? 'bg-brand-100 ring-2 ring-brand-300' : ''
              }`}
            >
              <ChevronRight size={12} className="text-apple-divider" strokeWidth={1.6} />
              <button
                type="button"
                onClick={() => onNavigateTo(index)}
                disabled={isCurrent}
                className="text-[13px] font-medium text-brand-600 transition-colors hover:text-brand-700 disabled:cursor-default disabled:text-apple-dark"
              >
                {segment}
              </button>
            </div>
          )
        })}
      </nav>

      <button
        type="button"
        onClick={onCreateFolder}
        disabled={isCreateDisabled}
        className="col-start-2 row-start-1 flex shrink-0 items-center justify-center gap-1.5 rounded-xl bg-apple-gray px-3 py-1.5 text-[12px] font-medium text-apple-dark transition-colors hover:bg-apple-divider/40 disabled:cursor-not-allowed disabled:opacity-40 md:col-start-3"
      >
        <FolderPlus size={13} strokeWidth={1.7} />
        새 폴더
      </button>
    </div>
  )
}
