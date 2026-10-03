/**
 * Toast notification system — modern top-right auto-dismissing toasts.
 *
 * Usage:
 *   const toast = useToast();
 *   toast.success("Saved!");
 *   toast.error("Something went wrong");
 *   toast.info("Info message");
 *   toast.confirm("Delete this?", () => { /* onConfirm *\/ });
 */
import { createPortal } from "react-dom";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

export type ToastVariant = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  variant: ToastVariant;
  message: string;
  /** Optional confirm callback — if set, shows Confirm/Cancel buttons. */
  onConfirm?: () => void;
  confirmLabel?: string;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
  /** Show a confirm toast with Confirm/Cancel buttons. */
  confirm: (message: string, onConfirm: () => void, confirmLabel?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: "border-success-200 bg-success-50 text-success-800",
  error: "border-danger-200 bg-danger-50 text-danger-800",
  info: "border-info-200 bg-info-50 text-info-800",
  warning: "border-warning-200 bg-warning-50 text-warning-800",
};

const VARIANT_ICONS: Record<ToastVariant, string> = {
  success: "✓",
  error: "✕",
  info: "ℹ",
  warning: "⚠",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idCounter = useRef(0);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const add = useCallback(
    (variant: ToastVariant, message: string) => {
      const id = ++idCounter.current;
      setToasts((prev) => [...prev, { id, variant, message }]);
      // Auto-dismiss after 4 seconds (non-confirmation toasts only)
      setTimeout(() => remove(id), 4000);
    },
    [remove],
  );

  const confirm = useCallback(
    (message: string, onConfirm: () => void, confirmLabel = "Confirm") => {
      const id = ++idCounter.current;
      setToasts((prev) => [...prev, { id, variant: "warning", message, onConfirm, confirmLabel }]);
      // Confirmation toasts don't auto-dismiss — they stay until the user
      // clicks Confirm or Cancel.
    },
    [],
  );

  const contextValue: ToastContextValue = {
    success: (msg: string) => add("success", msg),
    error: (msg: string) => add("error", msg),
    info: (msg: string) => add("info", msg),
    warning: (msg: string) => add("warning", msg),
    confirm,
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer toasts={toasts} onRemove={remove} />
    </ToastContext.Provider>
  );
}

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: number) => void }) {
  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed right-4 top-4 z-[9999] flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body,
  );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: number) => void }) {
  const [isLeaving, setIsLeaving] = useState(false);

  const handleClose = useCallback(() => {
    setIsLeaving(true);
    setTimeout(() => onRemove(toast.id), 200);
  }, [onRemove, toast.id]);

  const handleConfirm = useCallback(() => {
    toast.onConfirm?.();
    handleClose();
  }, [toast, handleClose]);

  return (
    <div
      className={`flex animate-fade-in items-start gap-3 rounded-lg border p-4 shadow-popover transition-all duration-200 ${
        VARIANT_STYLES[toast.variant]
      } ${isLeaving ? "translate-x-full opacity-0" : "translate-x-0 opacity-100"}`}
      role="alert"
    >
      <span className="mt-0.5 text-base font-bold leading-5">{VARIANT_ICONS[toast.variant]}</span>
      <div className="flex-1">
        <p className="text-sm font-medium leading-5">{toast.message}</p>
        {toast.onConfirm && (
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleConfirm}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            >
              {toast.confirmLabel}
            </button>
            <button
              onClick={handleClose}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
      {!toast.onConfirm && (
        <button
          onClick={handleClose}
          className="-mr-1 -mt-1 rounded-md p-1 text-lg leading-none text-slate-400 transition-colors hover:bg-slate-900/5 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Dismiss"
        >
          ×
        </button>
      )}
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Fallback: if used outside ToastProvider, return no-op functions
    // so components don't crash. This shouldn't happen in practice.
    return {
      success: () => {},
      error: () => {},
      info: () => {},
      warning: () => {},
      confirm: () => {},
    };
  }
  return ctx;
}
