import { useDialogAccessibility } from '@/hooks/useDialogAccessibility';
import * as React from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { useModalAnimation } from "@/hooks/useModalAnimation"

interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  ariaLabel?: string
  description?: string
  children: React.ReactNode
  className?: string
  maxWidth?: string
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  ariaLabel,
  description,
  children,
  className,
  maxWidth = "max-w-lg",
}) => {
  const { shouldRender, isClosing } = useModalAnimation(isOpen, 220)
  const dialogRef = useDialogAccessibility(isOpen && shouldRender, onClose, ariaLabel || title || 'Confirm action');



  if (!shouldRender || typeof document === "undefined") return null

  return createPortal(
    <div ref={dialogRef} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-slate-900/65  transition-opacity",
          isClosing ? "animate-modal-backdrop-exit" : "animate-modal-backdrop"
        )}
        onClick={onClose}
      />

      {/* Dialog content */}
      <div
        className={cn(
          "relative w-full max-h-[calc(100dvh-1.5rem)] sm:max-h-[90vh] overflow-y-auto rounded-xl bg-card p-4 sm:p-6 text-foreground shadow-2xl transition-colors z-10 custom-scrollbar my-auto",
          isClosing ? "animate-modal-content-exit" : "animate-modal-content",
          maxWidth,
          className
        )}
      >
        <button
          onClick={onClose}
          className="absolute right-2 top-2 h-11 w-11 flex items-center justify-center rounded-lg text-slate-500 hover:text-foreground hover:bg-slate-100 transition-colors cursor-pointer z-20 print:hidden"
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </button>

        {(title || description) && (
          <div className="flex flex-col space-y-1.5 text-left mb-4 pr-12">
            {title && (
              <h2 className="text-base sm:text-lg font-bold leading-snug tracking-tight text-slate-900">
                {title}
              </h2>
            )}
            {description && (
              <p className="text-xs sm:text-sm text-slate-500">{description}</p>
            )}
          </div>
        )}

        {children}
      </div>
    </div>,
    document.body
  )
}
