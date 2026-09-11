/**
 * Invoicing page (H14) — Doc 4: empanelled roles (SME, Reviewer, Trainer,
 * Counsellor, Channel Partner, Psychometrician) raise invoices against CJ
 * Admin, who reviews (approve/reject) and marks them paid.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  Badge,
  Button,
  Input,
  Label,
  Modal,
  PageCard,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "@/components/ui";
import {
  INVOICE_TYPES,
  INVOICING_EMPANELLED_ROLES,
  approveInvoice,
  cancelInvoice,
  createInvoice,
  listInvoices,
  listMyInvoices,
  listPendingInvoices,
  payInvoice,
  rejectInvoice,
  submitInvoice,
  type Invoice,
  type InvoiceStatus,
  type InvoiceType,
} from "@/api/invoicing";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { usePermissions } from "@/hooks/usePermissions";

const STATUS_VARIANT: Record<InvoiceStatus, "default" | "success" | "warning" | "danger" | "primary" | "outline"> = {
  draft: "outline",
  submitted: "warning",
  approved: "primary",
  rejected: "danger",
  paid: "success",
  cancelled: "default",
};

export default function InvoicingPage() {
  const { user } = useAuth();
  const { isSuperAdmin } = usePermissions();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  const canCreate = isSuperAdmin || INVOICING_EMPANELLED_ROLES.includes(user?.role ?? "");

  const myQuery = useQuery({ queryKey: ["invoicing", "mine"], queryFn: listMyInvoices });
  const pendingQuery = useQuery({
    queryKey: ["invoicing", "pending"],
    queryFn: listPendingInvoices,
    enabled: isSuperAdmin,
  });
  const allQuery = useQuery({
    queryKey: ["invoicing", "all"],
    queryFn: listInvoices,
    enabled: isSuperAdmin,
  });

  const invalidateAll = () => {
    void queryClient.invalidateQueries({ queryKey: ["invoicing"] });
  };

  const submitMut = useMutation({
    mutationFn: (id: number) => submitInvoice(id),
    onSuccess: () => {
      invalidateAll();
      toast.success("Invoice submitted to CJ Admin.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const cancelMut = useMutation({
    mutationFn: (id: number) => cancelInvoice(id),
    onSuccess: () => {
      invalidateAll();
      toast.success("Invoice cancelled.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const myInvoices = myQuery.data?.results ?? [];
  const pendingInvoices = pendingQuery.data?.results ?? [];
  const allInvoices = allQuery.data?.results ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6 pb-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Invoicing</h1>
            <p className="text-sm text-slate-500">
              {canCreate
                ? "Raise invoices for your work and track their approval."
                : "Track invoice status across the platform."}
            </p>
          </div>
          {canCreate && <Button onClick={() => setCreateOpen(true)}>New invoice</Button>}
        </div>

        <Tabs defaultValue="mine">
          <div className="px-6">
            <TabsList>
              <TabsTrigger value="mine">My Invoices ({myInvoices.length})</TabsTrigger>
              {isSuperAdmin && (
                <TabsTrigger value="pending">Review Queue ({pendingInvoices.length})</TabsTrigger>
              )}
              {isSuperAdmin && <TabsTrigger value="all">All Invoices</TabsTrigger>}
            </TabsList>
          </div>

          <TabsContent value="mine" className="px-6 py-4">
            {myQuery.isLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : (
              <InvoiceTable
                invoices={myInvoices}
                renderActions={(inv) =>
                  inv.creator === user?.id ? (
                    <div className="flex gap-1">
                      {inv.status === "draft" && (
                        <Button
                          size="sm"
                          onClick={() => submitMut.mutate(inv.id)}
                          loading={submitMut.isPending}
                        >
                          Submit
                        </Button>
                      )}
                      {(inv.status === "draft" || inv.status === "submitted") && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-danger-600"
                          onClick={() => cancelMut.mutate(inv.id)}
                          loading={cancelMut.isPending}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  ) : null
                }
              />
            )}
          </TabsContent>

          {isSuperAdmin && (
            <TabsContent value="pending" className="px-6 py-4">
              {pendingQuery.isLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner size="lg" />
                </div>
              ) : (
                <InvoiceTable
                  invoices={pendingInvoices}
                  renderActions={(inv) => <AdminReviewActions invoice={inv} onDone={invalidateAll} />}
                />
              )}
            </TabsContent>
          )}

          {isSuperAdmin && (
            <TabsContent value="all" className="px-6 py-4">
              {allQuery.isLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner size="lg" />
                </div>
              ) : (
                <InvoiceTable
                  invoices={allInvoices}
                  renderActions={(inv) => <AdminReviewActions invoice={inv} onDone={invalidateAll} />}
                />
              )}
            </TabsContent>
          )}
        </Tabs>
      </PageCard>

      {createOpen && (
        <CreateInvoiceModal onClose={() => setCreateOpen(false)} onCreated={invalidateAll} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared invoice table
// ---------------------------------------------------------------------------

function InvoiceTable({
  invoices,
  renderActions,
}: {
  invoices: Invoice[];
  renderActions: (invoice: Invoice) => React.ReactNode;
}) {
  if (invoices.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">No invoices yet.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Invoice #</TableHead>
          <TableHead>Creator</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Amount</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {invoices.map((inv) => (
          <TableRow key={inv.id}>
            <TableCell className="font-medium text-slate-900">{inv.invoice_number}</TableCell>
            <TableCell className="text-slate-500">{inv.creator_name || inv.creator_role}</TableCell>
            <TableCell className="text-slate-500">
              {INVOICE_TYPES.find((t) => t.value === inv.invoice_type)?.label ?? inv.invoice_type}
            </TableCell>
            <TableCell className="max-w-xs truncate text-slate-700">{inv.description}</TableCell>
            <TableCell className="text-slate-500">
              {inv.amount} {inv.currency}
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANT[inv.status]}>{inv.status}</Badge>
            </TableCell>
            <TableCell>{renderActions(inv)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
      {invoices.length === 0 && <TableEmpty colSpan={7}>No invoices.</TableEmpty>}
    </Table>
  );
}

// ---------------------------------------------------------------------------
// Create invoice modal (empanelled roles + admin)
// ---------------------------------------------------------------------------

function CreateInvoiceModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const toast = useToast();
  const [invoiceType, setInvoiceType] = useState<InvoiceType>("other");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      createInvoice({ invoice_type: invoiceType, description, amount: amount || "0" }),
    onSuccess: () => {
      onCreated();
      toast.success("Invoice created as a draft. Submit it when you're ready.");
      onClose();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Modal open onClose={onClose} title="New invoice" size="sm">
      <div className="space-y-4">
        <div>
          <Label htmlFor="inv-type" required>
            Invoice type
          </Label>
          <select
            id="inv-type"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={invoiceType}
            onChange={(e) => setInvoiceType(e.target.value as InvoiceType)}
          >
            {INVOICE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="inv-desc" required>
            Description
          </Label>
          <textarea
            id="inv-desc"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What this invoice is for…"
          />
        </div>
        <div>
          <Label htmlFor="inv-amount" required>
            Amount
          </Label>
          <Input
            id="inv-amount"
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => createMut.mutate()}
            loading={createMut.isPending}
            disabled={!description.trim() || !amount}
          >
            Create draft
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Admin review actions — approve/reject a submitted invoice, or mark an
// approved one paid.
// ---------------------------------------------------------------------------

function AdminReviewActions({ invoice, onDone }: { invoice: Invoice; onDone: () => void }) {
  const toast = useToast();
  const [reviewOpen, setReviewOpen] = useState<"approve" | "reject" | null>(null);
  const [payOpen, setPayOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [paymentReference, setPaymentReference] = useState("");

  const reviewMut = useMutation({
    mutationFn: () =>
      reviewOpen === "reject" ? rejectInvoice(invoice.id, comment) : approveInvoice(invoice.id, comment),
    onSuccess: () => {
      onDone();
      toast.success(reviewOpen === "reject" ? "Invoice rejected." : "Invoice approved.");
      setReviewOpen(null);
      setComment("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const payMut = useMutation({
    mutationFn: () => payInvoice(invoice.id, paymentReference),
    onSuccess: () => {
      onDone();
      toast.success("Invoice marked as paid.");
      setPayOpen(false);
      setPaymentReference("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="flex gap-1">
      {invoice.status === "submitted" && (
        <>
          <Button size="sm" onClick={() => setReviewOpen("approve")}>
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-danger-600"
            onClick={() => setReviewOpen("reject")}
          >
            Reject
          </Button>
        </>
      )}
      {invoice.status === "approved" && (
        <Button size="sm" onClick={() => setPayOpen(true)}>
          Mark paid
        </Button>
      )}

      {reviewOpen && (
        <Modal
          open
          onClose={() => setReviewOpen(null)}
          title={reviewOpen === "reject" ? "Reject invoice" : "Approve invoice"}
          size="sm"
        >
          <div className="space-y-3">
            <div>
              <Label htmlFor="review-comment">Comment (optional)</Label>
              <textarea
                id="review-comment"
                rows={3}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setReviewOpen(null)}>
                Cancel
              </Button>
              <Button
                variant={reviewOpen === "reject" ? "danger" : "primary"}
                onClick={() => reviewMut.mutate()}
                loading={reviewMut.isPending}
              >
                {reviewOpen === "reject" ? "Reject" : "Approve"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {payOpen && (
        <Modal open onClose={() => setPayOpen(false)} title="Mark invoice as paid" size="sm">
          <div className="space-y-3">
            <div>
              <Label htmlFor="pay-ref">Payment reference (optional)</Label>
              <Input
                id="pay-ref"
                value={paymentReference}
                onChange={(e) => setPaymentReference(e.target.value)}
                placeholder="e.g. BANK-REF-001"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setPayOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => payMut.mutate()} loading={payMut.isPending}>
                Mark paid
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
