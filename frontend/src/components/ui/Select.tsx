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
          "cj-select h-10 w-full appearance-none rounded-md border bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-primary-500/25",
          hasError
            ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/25"
            : "border-slate-300 hover:border-slate-400 focus:border-primary-500 focus:hover:border-primary-500",
          disabled && "cursor-not-allowed bg-slate-50 text-slate-500 opacity-70",
          className,
        )}
        aria-invalid={hasError || undefined}
        {...props}
      />
    );
  },
);

Select.displayName = "Select";
