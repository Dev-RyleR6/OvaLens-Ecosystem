import * as React from "react"
import { cn } from "@/lib/utils"

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <select
        className={cn(
          "flex min-h-11 w-full min-w-0 max-w-full rounded-lg border border-input bg-card px-3 py-2.5 text-base sm:text-sm transition-colors hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </select>
    )
  }
)
Select.displayName = "Select"

export { Select }
