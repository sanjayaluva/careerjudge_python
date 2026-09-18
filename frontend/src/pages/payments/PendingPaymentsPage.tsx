/**
 * Pending Payments (E-PLT-2) — CJ Admin manually authorises payments that
 * were made offline or via a manual gateway, marking them paid and unlocking
 * the linked module (assessment / training / counseling) for the payer.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  PageCard,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
  useToast,
} from "@/components/ui";
import { authorisePayment, listPendingPayments } from "@/api/payments";
import { extractApiError } from "@/api/client";

const KEY = ["payments", "pending"];

export default function PendingPaymentsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  const { data: pending, isLoading } = useQuery({
    queryKey: KEY,
    queryFn: () => listPendingPayments(),
  });

  const authoriseMut = useMutation({
    mutationFn: (id: number) => authorisePayment(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Payment authorised — access unlocked.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const list = pending ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="p-6">
          <Link to="/invoicing" className="text-sm text-primary-600 hover:underline">
            ← Back to Invoicing
          </Link>
          <h1 className="mt-2 text-lg font-bold text-slate-900">Pending Payments</h1>
          <p className="text-sm text-slate-500">
            {list.length} payment{list.length !== 1 ? "s" : ""} awaiting manual authorisation.
          </p>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Module</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Raised</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.length === 0 ? (
                <TableEmpty colSpan={6}>No payments awaiting authorisation.</TableEmpty>
              ) : (
                list.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium capitalize">{p.module}</TableCell>
                    <TableCell className="text-slate-500">#{p.item_id}</TableCell>
                    <TableCell>
                      {p.amount} {p.currency}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{p.provider || "manual"}</Badge>
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {new Date(p.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        onClick={() => authoriseMut.mutate(p.id)}
                        loading={authoriseMut.isPending && authoriseMut.variables === p.id}
                      >
                        Authorise
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </PageCard>
    </div>
  );
}
