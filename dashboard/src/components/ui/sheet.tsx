import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in-0"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div
          className={cn(
            "relative w-screen max-w-md md:max-w-lg border-l bg-background p-6 shadow-xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200",
            className
          )}
        >
          <div>
            <div className="flex items-center justify-between pb-4 border-b">
              <div>
                {title && (
                  <h3 className="text-base font-semibold leading-none tracking-tight">
                    {title}
                  </h3>
                )}
                {description && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {description}
                  </p>
                )}
              </div>
              <button
                onClick={onClose}
                className="rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 p-1 cursor-pointer"
              >
                <X className="h-4 w-4" />
                <span className="sr-only">Close</span>
              </button>
            </div>

            <div className="py-4">{children}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
