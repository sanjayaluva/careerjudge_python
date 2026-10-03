import { forwardRef, type LabelHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export const Label = forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, children, required, ...props }, ref) => {
    return (
      <label
        ref={ref}
        className={cn("block text-sm font-medium leading-5 text-slate-700", "mb-1.5", className)}
        {...props}
      >
        {children}
        {required && <span className="ml-0.5 text-danger-500">*</span>}
      </label>
    );
  },
);
Label.displayName = "Label";
