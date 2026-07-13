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
  success: "border-green-200 bg-green-50 text-green-800",
  error: "border-red-200 bg-red-50 text-red-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
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
      className={`flex items-start gap-3 rounded-lg border p-4 shadow-lg transition-all duration-200 ${
        VARIANT_STYLES[toast.variant]
      } ${isLeaving ? "translate-x-full opacity-0" : "translate-x-0 opacity-100"}`}
      role="alert"
    >
      <span className="mt-0.5 text-lg font-bold">{VARIANT_ICONS[toast.variant]}</span>
      <div className="flex-1">
        <p className="text-sm font-medium">{toast.message}</p>
        {toast.onConfirm && (
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleConfirm}
              className="rounded-md bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700"
            >
              {toast.confirmLabel}
            </button>
            <button
              onClick={handleClose}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
      {!toast.onConfirm && (
        <button
          onClick={handleClose}
          className="text-lg leading-none text-slate-400 hover:text-slate-600"
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
