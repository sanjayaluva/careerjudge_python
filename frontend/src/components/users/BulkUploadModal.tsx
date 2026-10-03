import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient, extractApiError } from "@/api/client";
import { Alert, AlertDescription, Button, Label, Modal } from "@/components/ui";
import { usePermissions } from "@/hooks/usePermissions";

// ---------------------------------------------------------------------------
// Bulk Upload Modal — CSV upload with template download + results display
// ---------------------------------------------------------------------------

interface BulkResult {
  email_failed_count?: number;
  created_count: number;
  skipped_count: number;
  error_count: number;
  created: { row: number; email: string; full_name: string }[];
  skipped: { row: number; email: string; reason: string }[];
  errors: { row: number; email: string; error: string }[];
}

export interface BulkUploadModalProps {
  open: boolean;
  onClose: () => void;
  /** Organization page: link the created users to this organization… */
  organizationId?: number;
  /** …optionally into one of its groups (Report 9 #7/#24/#35/#55). */
  groups?: { id: number; name: string }[];
  /** Query keys to refresh after a successful upload. */
  invalidateKeys?: unknown[][];
}

export function BulkUploadModal({
  open,
  onClose,
  organizationId,
  groups = [],
  invalidateKeys = [["admin", "users"]],
}: BulkUploadModalProps) {
  const queryClient = useQueryClient();
  const { isSuperAdmin } = usePermissions();
  const [file, setFile] = useState<File | null>(null);
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkResult | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async (uploadedFile: File) => {
      const formData = new FormData();
      formData.append("file", uploadedFile);
      if (organizationId) formData.append("organization_id", String(organizationId));
      if (groupId) formData.append("group_id", groupId);
      const resp = await apiClient.post("/accounts/users/bulk-upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return resp.data as { message: string; data: BulkResult };
    },
    onSuccess: (resp) => {
      setResult(resp.data);
      for (const key of invalidateKeys) void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const handleDownloadTemplate = async () => {
    try {
      const resp = await apiClient.get("/accounts/users/bulk-upload/template/", {
        responseType: "blob",
      });
      // Create a download link from the blob
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "careerjudge_bulk_users_template.csv");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(extractApiError(err));
    }
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!file) {
      setError("Please select a CSV file.");
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleClose = () => {
    setFile(null);
    setGroupId("");
    setError(null);
    setResult(null);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Bulk upload users"
      description="Upload a CSV file to create multiple users at once."
      size="lg"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result ? (
        <div className="space-y-4">
          <Alert variant="success" className="mb-4">
            <AlertDescription>
              Upload complete: {result.created_count} created, {result.skipped_count} skipped,{" "}
              {result.error_count} errors.
            </AlertDescription>
          </Alert>
          {(result.email_failed_count ?? 0) > 0 && (
            <Alert variant="warning" className="mb-4">
              <AlertDescription>
                {result.email_failed_count} verification email(s) could not be sent. Those users can
                be re-invited later.
              </AlertDescription>
            </Alert>
          )}

          {result.created.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-900">
                Created ({result.created_count})
              </p>
              <div className="max-h-32 overflow-y-auto rounded-md border border-slate-200">
                {result.created.map((c, i) => (
                  <div key={i} className="border-b border-slate-100 px-3 py-1.5 text-xs">
                    <span className="font-medium text-slate-900">{c.full_name}</span>
                    <span className="mx-2 text-slate-400">—</span>
                    <span className="text-slate-500">{c.email}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.skipped.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">
                Skipped ({result.skipped_count})
              </p>
              <div className="max-h-32 overflow-y-auto rounded-md border border-slate-200">
                {result.skipped.map((s, i) => (
                  <div key={i} className="border-b border-slate-100 px-3 py-1.5 text-xs">
                    <span className="text-slate-600">{s.email}</span>
                    <span className="ml-2 text-slate-400">— {s.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-danger">
                Errors ({result.error_count})
              </p>
              <div className="max-h-32 overflow-y-auto rounded-md border border-danger-200">
                {result.errors.map((er, i) => (
                  <div key={i} className="border-b border-danger-100 px-3 py-1.5 text-xs">
                    <span className="text-slate-600">
                      Row {er.row}: {er.email}
                    </span>
                    <span className="ml-2 text-danger">— {er.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end border-t border-slate-100 pt-4">
            <Button type="button" onClick={handleClose}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <p className="mb-2 text-sm font-medium text-slate-700">Instructions</p>
            <ol className="ml-4 list-decimal space-y-1 text-xs text-slate-600">
              <li>Download the CSV template using the button below</li>
              <li>Fill in user details (full_name and email are required)</li>
              <li>
                Optional columns: phone, employee_id
                {/* An organization manager (Corp Admin, Corp Exclusive, Group
                    Admin, Channel Partner) bulk-creates individuals only;
                    Group Admins are set up one by one with "Add Group Admin". */}
                {!organizationId
                  ? ", role_name (e.g., individual, corp_admin, sme, reviewer)"
                  : isSuperAdmin
                    ? ", role_name (e.g., individual)"
                    : ", role_name (individual only)"}
              </li>
              <li>Upload the filled CSV file below</li>
              <li>Users will be created with a random password and signup email sent</li>
            </ol>
            <Button
              type="button"
              variant="link"
              size="sm"
              className="mt-2 p-0"
              onClick={handleDownloadTemplate}
            >
              Download CSV template
            </Button>
          </div>

          {organizationId && groups.length > 0 && (
            <div>
              <Label htmlFor="bulk-group">Add the users to group</Label>
              <select
                id="bulk-group"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                value={groupId}
                onChange={(e) => setGroupId(e.target.value)}
              >
                <option value="">No group</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <Label htmlFor="bulk-file">CSV file</Label>
            <input
              id="bulk-file"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-slate-500 file:mr-4 file:rounded-md file:border-0 file:bg-primary-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-700"
            />
            {file && (
              <p className="mt-1 text-xs text-slate-500">
                Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={uploadMutation.isPending} disabled={!file}>
              Upload & create users
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
