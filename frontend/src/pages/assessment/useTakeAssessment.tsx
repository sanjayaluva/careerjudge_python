/**
 * useTakeAssessment — the candidate's "Take Assessment" flow.
 *
 * Report 9 #73: a PAID assessment first shows a pop-up with its price
 * ("This assessment costs ₹X. Pay to start?") and only then goes into the
 * existing payment flow (Razorpay widget / Stripe redirect). With no online
 * gateway active the payment waits for CJ Admin's approval (Admin › Payments)
 * and the pop-up says so. Report 9 #75: once the assessment is free or paid,
 * the candidate goes to the assessment description page, whose Start button
 * begins the session.
 *
 * Usage: `const take = useTakeAssessment();` → `take.begin(assessment)` on
 * click, and render `{take.prompt}` once in the page.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button, Modal, useToast } from "@/components/ui";
import { extractApiError } from "@/api/client";
import {
  createCheckout,
  getPaymentConfig,
  getPaymentStatus,
  openRazorpayCheckout,
  type PaymentConfig,
} from "@/api/payments";

import {
  formatPrice,
  hasOnlineGateway,
  isPaidAssessment,
  type TakeableAssessment,
} from "./takeAssessment";

type Stage = "confirm" | "awaiting";

export interface TakeAssessmentFlow {
  /** Start the flow for an assessment (price check → pay prompt → description page). */
  begin: (a: TakeableAssessment) => void;
  /** Open the pay prompt directly (e.g. after the server answered 402 payment_required). */
  promptPayment: (a: TakeableAssessment) => void;
  /** Id of the assessment whose payment status is being checked (for button spinners). */
  checkingId: number | null;
  /** The pop-up; render once in the page. */
  prompt: ReactNode;
}

export function useTakeAssessment(opts?: {
  /** Called when the candidate may start (free or paid). Defaults to opening the description page. */
  onReady?: (a: TakeableAssessment) => void;
}): TakeAssessmentFlow {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<TakeableAssessment | null>(null);
  const [stage, setStage] = useState<Stage>("confirm");
  const [config, setConfig] = useState<PaymentConfig | null>(null);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [paying, setPaying] = useState(false);

  const ready = (a: TakeableAssessment) => {
    setTarget(null);
    if (opts?.onReady) opts.onReady(a);
    else navigate(`/assessments/${a.id}/start`);
  };

  const loadConfig = () =>
    queryClient
      .fetchQuery({
        queryKey: ["payments", "config"],
        queryFn: getPaymentConfig,
        staleTime: 60_000,
      })
      .catch(() => null);

  const openPrompt = async (a: TakeableAssessment, paymentStatus?: string) => {
    const cfg = await loadConfig();
    setConfig(cfg);
    // A request already waiting for CJ Admin (no gateway to pay it online):
    // tell the candidate where it stands instead of asking again.
    setStage(paymentStatus === "pending" && !hasOnlineGateway(cfg) ? "awaiting" : "confirm");
    setTarget(a);
  };

  const begin = async (a: TakeableAssessment) => {
    if (!isPaidAssessment(a)) {
      ready(a);
      return;
    }
    setCheckingId(a.id);
    try {
      const st = await getPaymentStatus("assessment", a.id);
      if (st.is_paid) {
        ready(a);
        return;
      }
      await openPrompt(a, st.status);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setCheckingId(null);
    }
  };

  const pay = async () => {
    if (!target) return;
    setPaying(true);
    try {
      const res = await createCheckout({
        module: "assessment",
        item_id: target.id,
        amount: target.price,
        description: `Assessment: ${target.title}`,
      });
      if (res.order) {
        // E-PLT-4: Razorpay is the active gateway — open its widget.
        const paid = await openRazorpayCheckout(res.order);
        if (paid) ready(target);
        else toast.error("Payment not completed. Click Take Assessment to try again.");
        return;
      }
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
        return;
      }
      if (res.status === "paid" || res.status === "free") {
        ready(target);
        return;
      }
      // No online gateway: the payment is recorded as pending for CJ Admin.
      setStage("awaiting");
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setPaying(false);
    }
  };

  const currency = config?.currency || "INR";
  const price = target ? formatPrice(target.price, currency) : "";
  const online = hasOnlineGateway(config);
  const close = () => setTarget(null);

  const prompt = (
    <Modal
      open={target !== null}
      onClose={close}
      closeOnBackdrop={!paying}
      closeOnEsc={!paying}
      title={stage === "confirm" ? "Payment required" : "Payment awaiting admin approval"}
      footer={
        stage === "confirm" ? (
          <>
            <Button variant="outline" onClick={close} disabled={paying}>
              Cancel
            </Button>
            <Button loading={paying} onClick={() => void pay()}>
              {online ? `Pay ${price}` : `Confirm payment of ${price}`}
            </Button>
          </>
        ) : (
          <Button onClick={close}>OK</Button>
        )
      }
    >
      {target && stage === "confirm" && (
        <div className="space-y-3 text-sm text-slate-700">
          <p>
            <span className="font-semibold text-slate-900">{target.title}</span> costs{" "}
            <span className="font-semibold text-slate-900">{price}</span>. Pay to start?
          </p>
          {online ? (
            <p className="text-slate-500">
              You will be taken to the secure payment page. After payment the assessment description
              opens and you can start.
            </p>
          ) : (
            <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-800">
              Online payment is not available at the moment. When you confirm, your payment is sent
              to the Career Judge admin for approval. You can start the assessment once it is
              approved.
            </p>
          )}
        </div>
      )}
      {target && stage === "awaiting" && (
        <div className="space-y-3 text-sm text-slate-700">
          <p>
            Your payment of <span className="font-semibold text-slate-900">{price}</span> for{" "}
            <span className="font-semibold text-slate-900">{target.title}</span> is recorded and is
            awaiting approval by the Career Judge admin.
          </p>
          <p>
            Once it is approved, open Assessments and click{" "}
            <span className="font-medium">Take Assessment</span> again — the assessment description
            will open and you can start. You will not be charged twice.
          </p>
          <p className="text-slate-500">
            Questions about your payment?{" "}
            <Link to="/concerns" className="text-primary-600 hover:underline" onClick={close}>
              Contact Admin
            </Link>
            .
          </p>
        </div>
      )}
    </Modal>
  );

  return {
    begin: (a) => void begin(a),
    promptPayment: (a) => void openPrompt(a),
    checkingId,
    prompt,
  };
}
