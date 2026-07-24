/**
 * Payment success/cancel pages — shown after Stripe redirect.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { Button, PageCard, Spinner } from "@/components/ui";
import { verifyPayment } from "@/api/payments";

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id");

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
    <div className="flex min-h-screen items-center justify-center p-6">
      <PageCard className="max-w-md">
        <div className="p-8 text-center">
          {verifyMut.isPending ? (
            <>
              <Spinner size="lg" />
              <p className="mt-4 text-sm text-slate-500">Verifying your payment...</p>
            </>
          ) : verifyMut.data?.status === "paid" ? (
            <>
              <div className="text-4xl">✅</div>
              <h1 className="mt-4 text-xl font-bold text-slate-900">Payment Successful!</h1>
              <p className="mt-2 text-sm text-slate-500">
                Your payment has been confirmed. You now have access.
              </p>
              <Link to="/dashboard" className="mt-4 inline-block">
                <Button>Go to Dashboard</Button>
              </Link>
            </>
          ) : (
            <>
              <div className="text-4xl">⏳</div>
              <h1 className="mt-4 text-xl font-bold text-slate-900">Payment Processing</h1>
              <p className="mt-2 text-sm text-slate-500">
                Your payment is being processed. Access will be granted once confirmed.
              </p>
              <Link to="/dashboard" className="mt-4 inline-block">
                <Button variant="outline">Go to Dashboard</Button>
              </Link>
            </>
          )}
        </div>
      </PageCard>
    </div>
  );
}

export function PaymentCancelPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <PageCard className="max-w-md">
        <div className="p-8 text-center">
          <div className="text-4xl">❌</div>
          <h1 className="mt-4 text-xl font-bold text-slate-900">Payment Cancelled</h1>
          <p className="mt-2 text-sm text-slate-500">
            Your payment was cancelled. You can try again anytime.
          </p>
          <Link to="/dashboard" className="mt-4 inline-block">
            <Button variant="outline">Go to Dashboard</Button>
          </Link>
        </div>
      </PageCard>
    </div>
  );
}
