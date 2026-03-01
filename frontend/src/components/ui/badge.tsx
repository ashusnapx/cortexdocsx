import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "subtle" | "outline";

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-teal-600 text-white border-transparent",
  subtle: "bg-teal-50 text-teal-800 border-teal-100",
  outline: "bg-white/70 text-slate-700 border-slate-200",
};

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
