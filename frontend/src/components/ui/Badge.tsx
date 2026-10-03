import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium leading-5 ring-1 ring-inset transition-colors",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-700 ring-slate-500/20",
        success: "bg-success-50 text-success-700 ring-success-600/20",
        warning: "bg-warning-50 text-warning-800 ring-warning-600/25",
        danger: "bg-danger-50 text-danger-700 ring-danger-600/20",
        info: "bg-info-50 text-info-700 ring-info-600/20",
        outline: "bg-white text-slate-600 ring-slate-300",
        primary: "bg-primary-50 text-primary-700 ring-primary-600/20",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant }), className)} {...props} />
  ),
);
Badge.displayName = "Badge";

export { badgeVariants };
