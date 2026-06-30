import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export type InputSize = "sm" | "md" | "lg";

const inputSizeClasses: Record<InputSize, string> = {
  sm: "h-8 text-xs",
  md: "h-10 text-sm",
  lg: "h-12 text-base",
};

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  /** Optional id — if omitted, the label's htmlFor will be derived from name. */
  id?: string;
  /** Show an error state — typically passed `errors.field`. */
  hasError?: boolean;
  inputSize?: InputSize;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, hasError, inputSize = "md", type = "text", id, disabled, ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        id={id}
        className={cn(
          "w-full rounded-md border bg-white px-3 py-2 text-slate-900 placeholder:text-slate-400 shadow-sm transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-1",
          inputSizeClasses[inputSize],
          hasError
            ? "border-danger focus:ring-danger"
            : "border-slate-200 hover:border-slate-300",
          disabled && "cursor-not-allowed bg-slate-50 opacity-60",
          className,
        )}
        aria-invalid={hasError || undefined}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";
