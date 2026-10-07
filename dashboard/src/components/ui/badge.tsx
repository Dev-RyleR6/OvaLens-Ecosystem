import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "maroon"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "status-brand",
    secondary: "status-neutral",
    destructive: "status-danger",
    outline: "text-foreground border-border",
    success: "status-success",
    warning: "status-warning",
    maroon: "status-brand",
  }

  return (
    <div
      className={cn(
        "status-badge",
        variants[variant],
        className
      )}
      {...props}
    />
  )
}

export { Badge }
