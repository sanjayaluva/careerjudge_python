/**
 * Payment success/cancel pages — shown after Stripe redirect.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Button, Card, Spinner } from "@/components/ui";
import { verifyPayment } from "@/api/payments";
import { clearPaymentReturn, readPaymentReturn } from "@/lib/paymentReturn";

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id");
  // Set by the page that sent the user to Stripe (Report 9: the candidate
  // goes straight on to his assessment).
  const [returnTo] = useState(() => readPaymentReturn());

  const verifyMut = useMutation({
    mutationFn: () => verifyPayment(sessionId!),
  });

  // Auto-verify on page load
  useQuery({
    queryKey: ["payment-verify", sessionId],
    queryFn: async () => {
      if (sessionId) {
        await verifyMut.mutateAsync();
      }
      return null;
    },
    enabled: !!sessionId,
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 sm:p-6">
      <Card className="w-full max-w-md">
        <div className="p-8 text-center sm:p-10">
          {verifyMut.isPending ? (
            <>
              <Spinner size="lg" className="mx-auto" />
              <p className="mt-4 text-sm text-slate-500">Verifying your payment...</p>
            </>
          ) : verifyMut.data?.status === "paid" ? (
            <>
              <div className="text-4xl">✅</div>
              <h1 className="mt-4 text-xl font-semibold tracking-tight text-slate-900">
                Payment Successful!
              </h1>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                Your payment has been confirmed. You now have access.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {/* Back to where the payment started (e.g. the assessment). */}
                {returnTo && (
                  <Link to={returnTo.path} onClick={clearPaymentReturn}>
                    <Button>{returnTo.label}</Button>
                  </Link>
                )}
                <Link to="/dashboard">
                  <Button variant={returnTo ? "outline" : "primary"}>Go to Dashboard</Button>
                </Link>
              </div>
            </>
          ) : (
            <>
              <div className="text-4xl">⏳</div>
              <h1 className="mt-4 text-xl font-semibold tracking-tight text-slate-900">
                Payment Processing
              </h1>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                Your payment is being processed. Access will be granted once confirmed.
              </p>
              <Link to="/dashboard" className="mt-6 inline-block">
                <Button variant="outline">Go to Dashboard</Button>
              </Link>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

export function PaymentCancelPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 sm:p-6">
      <Card className="w-full max-w-md">
        <div className="p-8 text-center sm:p-10">
          <div className="text-4xl">❌</div>
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-slate-900">
            Payment Cancelled
          </h1>
          <p className="mt-2 text-sm leading-snug text-slate-500">
            Your payment was cancelled. You can try again anytime.
          </p>
          <Link to="/dashboard" className="mt-6 inline-block">
            <Button variant="outline">Go to Dashboard</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
