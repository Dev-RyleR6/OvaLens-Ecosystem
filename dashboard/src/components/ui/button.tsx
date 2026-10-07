import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "maroon"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseClasses = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer [&>svg]:h-4 [&>svg]:w-4 [&>svg]:shrink-0"

    const variants = {
      default: "bg-primary text-primary-foreground hover:bg-primary-hover",
      maroon: "bg-primary text-primary-foreground hover:bg-primary-hover",
      destructive: "bg-destructive text-destructive-foreground hover:bg-destructive-hover",
      outline: "border border-input bg-card text-foreground hover:bg-slate-50",
      secondary: "bg-secondary text-secondary-foreground hover:bg-slate-200",
      ghost: "text-slate-700 hover:bg-slate-100 hover:text-foreground",
      link: "text-brand underline underline-offset-4 hover:decoration-2",
    }

    const sizes = {
      default: "px-4 py-2.5",
      sm: "px-3 py-2 text-sm",
      lg: "min-h-12 px-6 py-3",
      icon: "h-11 w-11 p-0",
    }

    return (
      <button
        className={cn(baseClasses, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
