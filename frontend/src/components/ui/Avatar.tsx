import { forwardRef, type HTMLAttributes } from "react";

import { cn, getInitials } from "@/lib/utils";

export interface AvatarProps extends HTMLAttributes<HTMLSpanElement> {
  /** Optional avatar URL. When omitted, shows initials derived from name/email. */
  src?: string | null;
  /** Full name or email used to derive initials. */
  name?: string | null;
  email?: string | null;
  size?: "sm" | "md" | "lg";
}

const sizeClasses: Record<NonNullable<AvatarProps["size"]>, string> = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-14 w-14 text-lg",
};

export const Avatar = forwardRef<HTMLSpanElement, AvatarProps>(
  ({ className, src, name, email, size = "md", ...props }, ref) => {
    const initials = getInitials(name, email);
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary-100 text-primary-700 font-semibold",
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        {src ? (
          <img
            src={src}
            alt={name || "User avatar"}
            className="h-full w-full object-cover"
          />
        ) : (
          <span aria-hidden="true">{initials}</span>
        )}
      </span>
    );
  },
);
Avatar.displayName = "Avatar";
