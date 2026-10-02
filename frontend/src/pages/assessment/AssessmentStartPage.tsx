/**
 * Assessment description page — shown before an assessment begins.
 *
 * Report 9 #75 (signed Doc 3 §2.1 / SRS p.52): drawn from the assessment's
 * definition — the title (large, bold, centred, coloured), then "Objective of
 * the Assessment", "Description of the Assessment" and "Instructions", then
 * a Start button that begins (or resumes) the session.
 *
 * Route: /assessments/:id/start
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Alert, AlertDescription, Button, PageCard, Spinner, useToast } from "@/components/ui";
import { retrieveAssessment, startSession } from "@/api/assessment";
import { extractApiError, extractApiErrorCode } from "@/api/client";

import { DefinitionText } from "./DefinitionText";
import { hasRichContent } from "./richDefinition";
import { useTakeAssessment } from "./useTakeAssessment";

function DefinitionSection({ heading, value }: { heading: string; value: string }) {
  if (!hasRichContent(value)) return null;
  return (
    <section>
      <h2 className="mb-2 border-b border-slate-200 pb-1 text-lg font-semibold text-slate-900">
        {heading}
      </h2>
      <DefinitionText value={value} />
    </section>
  );
}

export default function AssessmentStartPage() {
  const { id } = useParams<{ id: string }>();
  const aid = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: a, isLoading } = useQuery({
    queryKey: ["assessments", aid],
    queryFn: () => retrieveAssessment(aid),
    enabled: !Number.isNaN(aid),
  });

  // Paid but not yet paid (e.g. the page was opened directly): the server
  // answers 402 and the pay prompt opens; once paid, Start runs again.
  const take = useTakeAssessment({ onReady: () => startMutation.mutate() });

  const startMutation = useMutation({
    mutationFn: () => startSession(aid),
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: ["my-sessions"] });
      navigate(`/assessments/sessions/${session.id}`);
    },
    onError: (err) => {
      if (extractApiErrorCode(err) === "payment_required" && a) {
        take.promptPayment(a);
        return;
      }
      toast.error(extractApiError(err));
    },
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!a) {
    return (
      <Alert variant="error">
        <AlertDescription>This assessment is not available.</AlertDescription>
      </Alert>
    );
  }

  const minutes = a.total_duration_seconds ? Math.floor(a.total_duration_seconds / 60) : null;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link to="/assessments" className="text-sm text-primary-600 hover:underline">
        ← Back to Assessments
      </Link>
      <PageCard>
        <div className="space-y-8 p-6 sm:p-10">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-primary-700 sm:text-4xl">{a.title}</h1>
            {minutes !== null && (
              <p className="mt-2 text-sm text-slate-500">Duration: {minutes} minutes</p>
            )}
          </div>

          <DefinitionSection heading="Objective of the Assessment" value={a.objective} />
          <DefinitionSection heading="Description of the Assessment" value={a.description} />
          <DefinitionSection heading="Instructions" value={a.instructions} />

          <div className="flex flex-col items-center gap-2 border-t border-slate-100 pt-6">
            {a.status === "published" ? (
              <Button
                size="lg"
                loading={startMutation.isPending}
                onClick={() => startMutation.mutate()}
              >
                Start Assessment
              </Button>
            ) : (
              <p className="text-sm text-slate-500">
                Preview — candidates can start this assessment once it is published.
              </p>
            )}
          </div>
        </div>
      </PageCard>
      {take.prompt}
    </div>
  );
}
