/**
 * Report 8 #55 / Doc 8 §3.3: "When counselee signs in to dashboard, System
 * shows countdown clock" — the next counselling session with a live
 * countdown (and Join when the window opens) on the individual's dashboard.
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Card, CardContent } from "@/components/ui";
import { listMySessions } from "@/api/counseling";
import { JoinSessionButton } from "@/pages/counseling/JoinSession";
import { useJoinWindow } from "@/pages/counseling/joinWindow";

export function UpcomingCounselingCard() {
  const { data } = useQuery({ queryKey: ["counseling", "my-sessions"], queryFn: listMySessions });
  const now = Date.now();
  const next = (data ?? [])
    .filter(
      (s) =>
        (s.status === "confirmed" || s.status === "pending") &&
        s.timeslot_detail &&
        new Date(s.timeslot_detail.end_time ?? s.timeslot_detail.start_time).getTime() > now,
    )
    .sort(
      (a, b) =>
        new Date(a.timeslot_detail!.start_time).getTime() -
        new Date(b.timeslot_detail!.start_time).getTime(),
    )[0];
  const { label } = useJoinWindow(
    next?.timeslot_detail?.start_time,
    next?.timeslot_detail?.end_time,
  );
  if (!next) return null;
  return (
    <Card className="border-primary-200 bg-primary-50/40">
      <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-primary-700">
            Upcoming counselling session
          </p>
          <p className="text-sm text-slate-800">
            With <strong>{next.counsellor_name}</strong> ·{" "}
            {new Date(next.timeslot_detail!.start_time).toLocaleString()}
            {next.status === "pending" && " · awaiting counsellor confirmation"}
          </p>
          <p className="mt-1 font-mono text-lg font-bold text-primary-700">{label}</p>
        </div>
        <div className="flex items-center gap-3">
          {next.status === "confirmed" && <JoinSessionButton session={next} />}
          <Link to="/counseling" className="text-sm text-primary-600 hover:underline">
            View sessions
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
