import { forwardRef, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
}

/**
 * Shared native <select> primitive (E-X9 polish). Matches the Input component's
 * border, focus-ring and hover treatment so the many inline selects across the
 * app can share one consistent look.
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, hasError, disabled, ...props }, ref) => {
    return (
      <select
        ref={ref}
        disabled={disabled}
        className={cn(
          "h-10 w-full rounded-md border bg-white px-3 text-sm text-slate-900 shadow-sm transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-1",
          hasError ? "border-danger focus:ring-danger" : "border-slate-200 hover:border-slate-300",
          disabled && "cursor-not-allowed bg-slate-50 opacity-60",
          className,
        )}
        aria-invalid={hasError || undefined}
        {...props}
      />
    );
  },
);

Select.displayName = "Select";
