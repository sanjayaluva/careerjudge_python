import {
  createContext,
  forwardRef,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/utils";

interface DropdownContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  triggerRef: React.RefObject<HTMLButtonElement>;
  contentRef: React.RefObject<HTMLDivElement>;
}

const DropdownContext = createContext<DropdownContextValue | null>(null);

function useDropdown(): DropdownContextValue {
  const ctx = useContext(DropdownContext);
  if (!ctx) throw new Error("Dropdown components must be used inside <DropdownMenu>");
  return ctx;
}

export interface DropdownMenuProps {
  children: ReactNode;
  /** Controlled open state — leave undefined for uncontrolled. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function DropdownMenu({ children, open: controlled, onOpenChange }: DropdownMenuProps) {
  const [uncontrolled, setUncontrolled] = useState(false);
  const open = controlled ?? uncontrolled;
  const setOpen = (next: boolean) => {
    if (controlled === undefined) setUncontrolled(next);
    onOpenChange?.(next);
  };
  const triggerRef = useRef<HTMLButtonElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  return (
    <DropdownContext.Provider value={{ open, setOpen, triggerRef, contentRef }}>
      <div className="relative inline-block">{children}</div>
    </DropdownContext.Provider>
  );
}

export interface DropdownMenuTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
}

export const DropdownMenuTrigger = forwardRef<HTMLButtonElement, DropdownMenuTriggerProps>(
  ({ onClick, ...props }, _ref) => {
    const { open, setOpen, triggerRef } = useDropdown();
    return (
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(e) => {
          setOpen(!open);
          onClick?.(e);
        }}
        {...props}
      />
    );
  },
);
DropdownMenuTrigger.displayName = "DropdownMenuTrigger";

export interface DropdownMenuContentProps extends React.HTMLAttributes<HTMLDivElement> {
  align?: "start" | "end";
  sideOffset?: number;
}

export function DropdownMenuContent({
  className,
  align = "end",
  sideOffset = 6,
  children,
  ...props
}: DropdownMenuContentProps) {
  const { open, setOpen, contentRef, triggerRef } = useDropdown();

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (contentRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open, setOpen, contentRef, triggerRef]);

  if (!open) return null;

  return (
    <div
      ref={contentRef}
      role="menu"
      className={cn(
        "absolute z-50 mt-0 min-w-[12rem] overflow-hidden rounded-md border border-slate-200 bg-white p-1 shadow-md",
        "animate-fade-in",
        align === "end" ? "right-0" : "left-0",
        className,
      )}
      style={{ top: `calc(100% + ${sideOffset}px)` }}
      {...props}
    >
      {children}
    </div>
  );
}

export interface DropdownMenuItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  destructive?: boolean;
}

export const DropdownMenuItem = forwardRef<HTMLButtonElement, DropdownMenuItemProps>(
  ({ className, destructive, onClick, ...props }, ref) => {
    const { setOpen } = useDropdown();
    return (
      <button
        ref={ref}
        type="button"
        role="menuitem"
        className={cn(
          "flex w-full items-center gap-2 rounded-sm px-2.5 py-1.5 text-left text-sm transition-colors",
          "hover:bg-slate-100 focus:bg-slate-100 focus:outline-none",
          destructive ? "text-danger hover:bg-danger-50" : "text-slate-700",
          className,
        )}
        onClick={(e) => {
          onClick?.(e);
          setOpen(false);
        }}
        {...props}
      />
    );
  },
);
DropdownMenuItem.displayName = "DropdownMenuItem";

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return <div className={cn("my-1 h-px bg-slate-200", className)} />;
}

export function DropdownMenuLabel({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500",
        className,
      )}
    >
      {children}
    </div>
  );
}
