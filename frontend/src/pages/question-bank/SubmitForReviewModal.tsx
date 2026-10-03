/**
 * "Submit for review" with a reviewer picker (Report 9 #65, client change
 * request): the SME chooses the Reviewer the question goes to from the pool
 * of active reviewers, pre-selected with the reviewer CJ Admin named on the
 * SME's task. A question that was sent back returns to the reviewer who sent
 * it back (Report 9 #71), so the picker is fixed to him.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Alert, AlertDescription, Button, Label, Modal, Spinner } from "@/components/ui";
import { extractApiError } from "@/api/client";
import { getReviewerOptions, submitForReview } from "@/api/questionBank";
import { nameWithExpertise } from "@/lib/profileFields";

export function SubmitForReviewModal({
  questionId,
  questionTitle,
  onClose,
  onSubmitted,
}: {
  /** The question to submit; the modal is open while this is set. */
  questionId: number | null;
  questionTitle?: string;
  onClose: () => void;
  onSubmitted: () => void;
}) {
  const open = questionId !== null;
  const [reviewer, setReviewer] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const optionsQuery = useQuery({
    queryKey: ["question-bank", "reviewer-options", questionId],
    queryFn: () => getReviewerOptions(questionId as number),
    enabled: open,
  });
  const options = optionsQuery.data;

  // Pre-select the task's (or the sending-back) reviewer when the list loads.
  useEffect(() => {
    if (!open) return;
    setError(null);
    setReviewer(options?.default_reviewer ?? "");
  }, [open, options]);

  const mutation = useMutation({
    mutationFn: () => submitForReview(questionId as number, reviewer === "" ? null : reviewer),
    onSuccess: () => onSubmitted(),
    onError: (err) => setError(extractApiError(err)),
  });

  const reviewers = options?.reviewers ?? [];
  const locked = Boolean(options?.locked);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Submit for review"
      description={questionTitle}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={mutation.isPending}
            disabled={optionsQuery.isLoading || (reviewers.length > 0 && reviewer === "")}
            onClick={() => mutation.mutate()}
          >
            Send for review
          </Button>
        </div>
      }
    >
      {optionsQuery.isLoading ? (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      ) : (
        <div className="space-y-2">
          {error && (
            <Alert variant="error">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {optionsQuery.isError && (
            <Alert variant="error">
              <AlertDescription>{extractApiError(optionsQuery.error)}</AlertDescription>
            </Alert>
          )}
          <Label htmlFor="submit-reviewer">Reviewer</Label>
          <select
            id="submit-reviewer"
            className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-70"
            value={reviewer}
            disabled={locked}
            onChange={(e) => setReviewer(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">
              {reviewers.length ? "Select a reviewer…" : "No reviewers available"}
            </option>
            {reviewers.map((r) => (
              <option key={r.id} value={r.id}>
                {nameWithExpertise(r.full_name, r.domains_of_expertise)}
                {r.id === options?.task_reviewer ? " (named on your task)" : ""}
              </option>
            ))}
          </select>
          {locked ? (
            <p className="text-xs text-slate-500">
              This question was sent back, so it returns to the reviewer who sent it back.
            </p>
          ) : options?.task_reviewer ? (
            <p className="text-xs text-slate-500">
              Pre-selected with the reviewer CJ Admin named on your task.
            </p>
          ) : reviewers.length === 0 ? (
            <p className="text-xs text-slate-500">
              The question will be routed to a reviewer automatically.
            </p>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
