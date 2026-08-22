import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { useModalAnimation } from "@/hooks/useModalAnimation"

interface SheetProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
  children: React.ReactNode
  className?: string
  side?: "right" | "left"
}

export const Sheet: React.FC<SheetProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  className,
  side = "right",
}) => {
  const { shouldRender, isClosing } = useModalAnimation(isOpen, 220)

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    if (isOpen) {
      document.body.style.overflow = "hidden"
      window.addEventListener("keydown", handleKeyDown)
    }
    return () => {
      document.body.style.overflow = "unset"
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!shouldRender) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity",
          isClosing ? "animate-modal-backdrop-exit" : "animate-modal-backdrop"
        )}
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-0 sm:pl-10">
        <div
          className={cn(
            "relative w-screen max-w-[100vw] sm:max-w-md md:max-w-lg border-l border-slate-200 bg-white p-4 sm:p-6 shadow-2xl flex flex-col justify-between overflow-y-auto z-10 custom-scrollbar h-full max-h-[100dvh]",
            isClosing ? "animate-drawer-right-exit" : "animate-drawer-right",
            className
          )}
        >
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 flex-shrink-0">
              <div className="pr-4">
                {title && (
                  <h3 className="text-sm sm:text-base font-bold text-slate-900 leading-tight">
                    {title}
                  </h3>
                )}
                {description && (
                  <p className="text-[11px] sm:text-xs text-slate-500 mt-0.5 sm:mt-1">
                    {description}
                  </p>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer flex-shrink-0"
              >
                <X className="h-4 w-4" />
                <span className="sr-only">Close</span>
              </button>
            </div>

            <div className="py-4 flex-1 overflow-y-auto custom-scrollbar">{children}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
