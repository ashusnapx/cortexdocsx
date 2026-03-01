import * as React from "react";
import { cn } from "@/shared/utils/tw";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "error";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const baseStyles =
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2";

  const variants = {
    default: "border-transparent bg-primary text-white hover:bg-primaryHover",
    secondary:
      "border-transparent bg-surface text-foreground hover:bg-surfaceHover",
    success: "border-transparent bg-success text-emerald-800",
    error: "border-transparent bg-error text-errorForeground",
    outline: "text-foreground border-border",
  };

  return (
    <div className={cn(baseStyles, variants[variant], className)} {...props} />
  );
}

export { Badge };
