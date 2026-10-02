/**
 * Report 9 #72: the individual's Assessments page — "My Assessments" (free,
 * paid for, or licensed to his organization: Take / Resume / View Results)
 * apart from "Browse Assessments", where an unpaid priced assessment shows
 * its price and "Pay to take" (the Report 9 #73 pay prompt). A corporate
 * individual only ever lists what his organization was licensed, so all of
 * it is his.
 */
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import {
  Badge,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui";
import type { Assessment, AssessmentSession } from "@/api/assessment";
import { getPaymentConfig } from "@/api/payments";

import { isMine } from "./myAssessments";
import { formatPrice, isPaidAssessment } from "./takeAssessment";
import type { TakeAssessmentFlow } from "./useTakeAssessment";

const duration = (a: Assessment) =>
  a.total_duration_seconds ? `${Math.floor(a.total_duration_seconds / 60)} min` : "—";

const typeBadge = (a: Assessment) => (
  <Badge variant={a.assessment_type === "psychometric" ? "primary" : "default"}>
    {a.assessment_type === "psychometric" ? "Psychometric" : "Normal"}
  </Badge>
);

export function CandidateAssessments({
  assessments,
  sessionByAssessment,
  take,
  onResume,
  resuming,
}: {
  assessments: Assessment[];
  sessionByAssessment: Map<number, AssessmentSession>;
  take: TakeAssessmentFlow;
  onResume: (assessmentId: number) => void;
  resuming: boolean;
}) {
  const navigate = useNavigate();
  const { data: config } = useQuery({
    queryKey: ["payments", "config"],
    queryFn: getPaymentConfig,
    staleTime: 60_000,
  });
  const currency = config?.currency || "INR";
  const published = assessments.filter((a) => a.status === "published");
  const mine = published.filter((a) => isMine(a, sessionByAssessment.has(a.id)));
  const titleLink = (a: Assessment) => (
    <a href={`/assessments/${a.id}`} className="text-primary-600 hover:underline">
      {a.title}
    </a>
  );

  return (
    <Tabs defaultValue="mine">
      <div className="px-6">
        <TabsList>
          <TabsTrigger value="mine">My Assessments ({mine.length})</TabsTrigger>
          <TabsTrigger value="browse">Browse Assessments ({published.length})</TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="mine" className="pt-4">
        {mine.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            You have no assessments yet. Pay for one under Browse Assessments to take it.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Your status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mine.map((a) => {
                const session = sessionByAssessment.get(a.id);
                const inFlight = session?.status === "active" || session?.status === "suspended";
                return (
                  <TableRow key={a.id}>
                    <TableCell className="font-medium text-slate-900">{titleLink(a)}</TableCell>
                    <TableCell>{typeBadge(a)}</TableCell>
                    <TableCell className="text-slate-500">{duration(a)}</TableCell>
                    <TableCell>
                      {!session ? (
                        <Badge variant="default">Not started</Badge>
                      ) : inFlight ? (
                        <Badge variant="warning">
                          {session.status === "suspended" ? "Suspended" : "In progress"}
                        </Badge>
                      ) : session.status === "completed" ? (
                        <Badge variant="success">Completed</Badge>
                      ) : (
                        <Badge variant="default">{session.status}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        {!session && (
                          // Unlocked (free / paid / licensed): straight to the
                          // description page, whose Start begins it (#75).
                          <Button size="sm" onClick={() => navigate(`/assessments/${a.id}/start`)}>
                            Take Assessment
                          </Button>
                        )}
                        {inFlight && (
                          <Button size="sm" loading={resuming} onClick={() => onResume(a.id)}>
                            Resume
                          </Button>
                        )}
                        {session?.status === "completed" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigate(`/assessments/sessions/${session.id}/results`)}
                          >
                            View Results
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </TabsContent>

      <TabsContent value="browse" className="pt-4">
        {published.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No assessments are available to you yet.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Price</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {published.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium text-slate-900">{titleLink(a)}</TableCell>
                  <TableCell>{typeBadge(a)}</TableCell>
                  <TableCell className="text-slate-500">{duration(a)}</TableCell>
                  <TableCell className="text-slate-700">
                    {isPaidAssessment(a) ? formatPrice(a.price, currency) : "Free"}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end">
                      {isMine(a, sessionByAssessment.has(a.id)) ? (
                        <Badge variant="success">In My Assessments</Badge>
                      ) : (
                        <Button
                          size="sm"
                          loading={take.checkingId === a.id}
                          onClick={() => take.begin(a)}
                        >
                          Pay to take
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TabsContent>
    </Tabs>
  );
}
