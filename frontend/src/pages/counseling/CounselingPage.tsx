/**
 * Counseling page — browse counsellors + view my sessions.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Modal,
  PageCard,
  Spinner,
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
  useToast,
} from "@/components/ui";
import {
  COUNSELING_CATEGORIES,
  cancelSession,
  createCounsellorProfile,
  getCounselingSettings,
  listCounsellors,
  listMySessions,
  bookSession,
  listCounsellorTimeslotsForWeek,
  confirmFollowup,
  declineFollowup,
  listFollowups,
  submitSessionFeedback,
  type CounsellorProfile,
  type TimeSlot,
  type CounselingSession,
  type SessionFeedback,
} from "@/api/counseling";
import { extractApiError, apiPatch } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { CounsellorDashboard } from "./CounsellorDashboard";
import { JoinSessionButton } from "./JoinSession";

export default function CounselingPage() {
  const { user } = useAuth();
  const isCounsellor = user?.role === "counsellor";
  // CNS-3 (§2.1): show a payment-received confirmation when Stripe redirects
  // back to /counseling?payment=success.
  const [searchParams, setSearchParams] = useSearchParams();
  const paymentSuccess = searchParams.get("payment") === "success";
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [bookingCounsellor, setBookingCounsellor] = useState<CounsellorProfile | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["counseling", "counsellors", debouncedSearch, categoryFilter],
    queryFn: () =>
      listCounsellors({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(categoryFilter ? { category: categoryFilter } : {}),
      }),
  });

  const { data: mySessions } = useQuery({
    queryKey: ["counseling", "my-sessions"],
    queryFn: () => listMySessions(),
  });

  const counsellors = data?.results ?? [];
  const sessions = mySessions ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="p-6 pb-4">
          <h1 className="text-lg font-bold text-slate-900">Counseling</h1>
          <p className="text-sm text-slate-500">
            Book a session with one of our professional counsellors
          </p>
        </div>

        {paymentSuccess && (
          <div className="mx-6 mb-2 rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-900">
            <p className="font-medium">Payment received — your booking is confirmed.</p>
            <p className="mt-1">
              Your appointment will be confirmed by the counsellor within 6 hours (SRS §2.1). If you
              need any help, contact the helpdesk.
            </p>
            <div className="mt-2 flex gap-3">
              <Link to="/concerns" className="text-primary-600 hover:underline">
                Contact Helpdesk
              </Link>
              <button
                type="button"
                className="text-slate-500 hover:underline"
                onClick={() => setSearchParams({})}
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <Tabs defaultValue="browse">
          <div className="px-6">
            <TabsList>
              <TabsTrigger value="browse">Browse Counsellors ({counsellors.length})</TabsTrigger>
              {isCounsellor && <TabsTrigger value="dashboard">My Dashboard</TabsTrigger>}
              {/* Report 3 §1.18: counsellors don't book sessions — hide the tab */}
              {!isCounsellor && (
                <TabsTrigger value="my-sessions">My Sessions ({sessions.length})</TabsTrigger>
              )}
            </TabsList>
          </div>

          {/* === Browse Tab === */}
          <TabsContent value="browse" className="px-6 py-4">
            <div className="flex gap-2">
              <Input
                type="search"
                placeholder="Search counsellors..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setTimeout(() => setDebouncedSearch(e.target.value), 350);
                }}
                className="max-w-sm"
              />
              <select
                className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">All categories</option>
                {COUNSELING_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            {isLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : counsellors.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No counsellors available.</p>
            ) : (
              <Table className="mt-4">
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Categories</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Available Slots</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {counsellors.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium text-slate-900">
                        <Link
                          to={`/counseling/${c.id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {c.full_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {c.category_names.join(", ") || "—"}
                      </TableCell>
                      <TableCell className="text-slate-500">₹{c.hourly_rate}/Session</TableCell>
                      <TableCell>
                        <Badge variant={c.upcoming_slot_count > 0 ? "success" : "default"}>
                          {c.upcoming_slot_count} slot{c.upcoming_slot_count !== 1 ? "s" : ""}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button size="sm" onClick={() => setBookingCounsellor(c)}>
                          Book
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>

          {/* === Counsellor Dashboard Tab === */}
          {isCounsellor && (
            <TabsContent value="dashboard" className="px-6 py-4">
              <CounsellorDashboardWrapper />
            </TabsContent>
          )}

          {/* === My Sessions Tab === */}
          <TabsContent value="my-sessions" className="px-6 py-4">
            {sessions.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                You haven&apos;t booked any sessions yet.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Counsellor</TableHead>
                    <TableHead>Topic</TableHead>
                    <TableHead>Scheduled</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Fee</TableHead>
                    {/* H16/D8 §2.3: live-delivery — countdown + Join Session */}
                    <TableHead>Meeting</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium text-slate-900">
                        {s.counsellor_name}
                      </TableCell>
                      <TableCell className="text-slate-700">{s.topic}</TableCell>
                      <TableCell className="text-slate-500">
                        {s.timeslot_detail
                          ? new Date(s.timeslot_detail.start_time).toLocaleString()
                          : "—"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            s.status === "completed"
                              ? "success"
                              : s.status === "confirmed"
                                ? "primary"
                                : s.status === "cancelled"
                                  ? "danger"
                                  : "warning"
                          }
                        >
                          {s.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">₹{s.fee}</TableCell>
                      <TableCell>
                        {s.status === "confirmed" ? <JoinSessionButton session={s} /> : "—"}
                      </TableCell>
                      <TableCell>
                        <SessionActionsForCounselee session={s} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>
        </Tabs>
      </PageCard>

      {bookingCounsellor && (
        <BookingModal counsellor={bookingCounsellor} onClose={() => setBookingCounsellor(null)} />
      )}
    </div>
  );
}

function BookingModal({
  counsellor,
  onClose,
}: {
  counsellor: CounsellorProfile;
  onClose: () => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  // Report 3 §1.8: explicit terms acceptance (backend rejects without it).
  const [termsAccepted, setTermsAccepted] = useState(false);
  // D8 "browse future weeks": 0 = this week, 1 = next week, ...
  const [weekOffset, setWeekOffset] = useState(0);

  // Report 3 §1.9/§1.11: show the admin-managed terms + refund policy.
  const { data: settings } = useQuery({
    queryKey: ["counseling", "settings"],
    queryFn: getCounselingSettings,
  });

  const { data: week, isLoading } = useQuery({
    queryKey: ["counseling", "counsellors", counsellor.id, "timeslots", "week", weekOffset],
    queryFn: () => listCounsellorTimeslotsForWeek(counsellor.id, weekOffset),
  });
  const timeslots = week?.slots;
  const maxWeeksAhead = settings?.max_weeks_ahead ?? 3;

  // CNS-4: show the spec §2.1 confirmation message after a (free) booking
  // instead of a generic toast.
  const [booked, setBooked] = useState(false);
  const bookMutation = useMutation({
    mutationFn: () => {
      if (!selectedSlot) throw new Error("No slot selected");
      return bookSession({
        counsellor: counsellor.id,
        timeslot: selectedSlot.id,
        topic,
        description,
        mode: "online",
        terms_accepted: termsAccepted,
      });
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "my-sessions"] });
      void queryClient.invalidateQueries({
        queryKey: ["counseling", "counsellors", counsellor.id, "timeslots"],
        // matches both the plain and the ["...", "week", N] browsing keys
        exact: false,
      });
      // H15/D8 §2.1: paid sessions get a Stripe checkout URL — route through
      // the gateway like training's registerForCourse(), instead of assuming
      // payment is done.
      if (data.checkout_url) {
        toast.success("Redirecting to payment…");
        window.location.href = data.checkout_url;
        return;
      }
      setBooked(true);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const availableSlots = (timeslots ?? []).filter((s) => s.status === "available");

  return (
    <Modal
      open
      onClose={onClose}
      title={`Book with ${counsellor.full_name}`}
      description={`₹${counsellor.hourly_rate}/Session`}
      size="md"
    >
      <div className="space-y-4">
        {booked ? (
          <div className="space-y-4 py-2">
            <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-900">
              <p className="font-medium">Your booking is confirmed.</p>
              <p className="mt-1">
                Your appointment will be confirmed by the counsellor within 6 hours. If the
                counsellor is not available, you can select a fresh timeslot; or press Cancel and
                your money will be refunded within 48 hours (SRS §2.1).
              </p>
            </div>
            <div className="flex justify-end">
              <Button onClick={onClose}>Done</Button>
            </div>
          </div>
        ) : (
          <>
            {/* Report 3 §1.7: counsellor profile details */}
            <div className="flex items-start gap-3 rounded-md border border-slate-100 p-3">
              {counsellor.avatar ? (
                <img
                  src={counsellor.avatar}
                  alt={counsellor.full_name}
                  className="h-12 w-12 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-700">
                  {counsellor.full_name?.[0] ?? "?"}
                </div>
              )}
              <div className="text-sm">
                <div className="font-medium text-slate-900">{counsellor.full_name}</div>
                {(counsellor.gender || counsellor.language || counsellor.location) && (
                  <div className="mt-0.5 text-xs text-slate-500">
                    {[counsellor.gender, counsellor.language, counsellor.location]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                )}
                {counsellor.bio && (
                  <p className="mt-1 line-clamp-2 text-xs text-slate-600">{counsellor.bio}</p>
                )}
              </div>
            </div>

            {/* Report 3 §1.8: registration form (topic + description prefilled
            from the user's context) */}
            <div>
              <Label htmlFor="topic" required>
                Topic / Issue
              </Label>
              <Input
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., Career change advice"
                required
              />
              {user?.full_name && (
                <p className="mt-1 text-xs text-slate-400">
                  Booking as {user.full_name} ({user.email})
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="desc">Description (optional)</Label>
              <textarea
                id="desc"
                rows={2}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <Label required>Available time slots</Label>
                {/* D8 "browse future weeks" */}
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setWeekOffset((w) => Math.max(0, w - 1))}
                    disabled={weekOffset === 0}
                  >
                    ← Prev week
                  </Button>
                  <span className="px-1 text-xs text-slate-500">
                    {weekOffset === 0 ? "This week" : `Week +${weekOffset}`}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setWeekOffset((w) => Math.min(maxWeeksAhead, w + 1))}
                    disabled={weekOffset >= maxWeeksAhead}
                  >
                    Next week →
                  </Button>
                </div>
              </div>
              {isLoading ? (
                <Spinner />
              ) : availableSlots.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No available slots this week. Try browsing another week.
                </p>
              ) : (
                <div className="max-h-48 space-y-1 overflow-y-auto">
                  {availableSlots.map((slot) => (
                    <button
                      key={slot.id}
                      onClick={() => setSelectedSlot(slot)}
                      className={`block w-full rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                        selectedSlot?.id === slot.id
                          ? "border-primary-500 bg-primary-50 text-primary-900"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      {new Date(slot.start_time).toLocaleString()} —{" "}
                      {new Date(slot.end_time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Report 3 §1.11: refund policy display */}
            {settings?.cancellation_policy && (
              <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                <div className="mb-1 font-medium text-slate-700">Cancellation & refund policy</div>
                {settings.cancellation_policy}
              </div>
            )}

            {/* Report 3 §1.8: terms checkbox */}
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
              />
              <span className="text-slate-700">
                I accept the{" "}
                {settings?.terms_and_conditions ? (
                  <details className="inline">
                    <summary className="cursor-pointer text-primary-600">
                      Terms &amp; Conditions
                    </summary>
                    <div className="mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap rounded-md bg-slate-50 p-2 text-xs text-slate-600">
                      {settings.terms_and_conditions}
                    </div>
                  </details>
                ) : (
                  "Terms & Conditions"
                )}
              </span>
            </label>

            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={() => bookMutation.mutate()}
                loading={bookMutation.isPending}
                disabled={!topic || !selectedSlot || !termsAccepted}
              >
                Book session (₹{counsellor.hourly_rate})
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// CounsellorDashboardWrapper — finds the counsellor's profile and renders dashboard
// ---------------------------------------------------------------------------

function CounsellorDashboardWrapper() {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [bio, setBio] = useState("");
  const [hourlyRate, setHourlyRate] = useState("50");

  const { data: counsellors } = useQuery({
    queryKey: ["counseling", "counsellors", "me"],
    queryFn: () => listCounsellors({ search: user?.email ?? "" }),
  });

  const myProfile = counsellors?.results?.find((c) => c.user_email === user?.email);

  const createMut = useMutation({
    mutationFn: async () => {
      // Step 1: Update UserProfile with counsellor-specific fields
      await apiPatch("/me/profile/", {
        bio,
        hourly_rate: parseFloat(hourlyRate),
        is_available_for_counseling: true,
      });
      // Step 2: Create CounsellorProfile (lightweight — just links user + categories)
      return createCounsellorProfile({
        full_name: fullName,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "counsellors"] });
      toast.success("Profile created! You can now manage sessions.");
      setShowCreateForm(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (!myProfile && !showCreateForm) {
    return (
      <div className="space-y-4">
        <Alert variant="warning">
          <AlertDescription>
            You don&apos;t have a counsellor profile yet. Create one to start receiving session
            bookings.
          </AlertDescription>
        </Alert>
        <Button onClick={() => setShowCreateForm(true)}>Create my profile</Button>
      </div>
    );
  }

  if (!myProfile && showCreateForm) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Create Counsellor Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMut.mutate();
            }}
            className="space-y-4"
          >
            <div>
              <Label htmlFor="cp-name" required>
                Full name
              </Label>
              <Input
                id="cp-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="cp-bio">Bio</Label>
              <textarea
                id="cp-bio"
                rows={3}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Brief introduction about your counselling experience..."
              />
            </div>
            <div>
              <Label htmlFor="cp-rate" required>
                Rate per session (INR)
              </Label>
              <Input
                id="cp-rate"
                type="number"
                min="0"
                step="0.01"
                value={hourlyRate}
                onChange={(e) => setHourlyRate(e.target.value)}
                required
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" loading={createMut.isPending} disabled={!fullName}>
                Create profile
              </Button>
              <Button type="button" variant="outline" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    );
  }

  if (!myProfile) return null;

  return <CounsellorDashboard counsellorId={myProfile.id} />;
}

// ---------------------------------------------------------------------------
// Post-session actions for counselees — feedback + follow-up confirmation
// ---------------------------------------------------------------------------

function SessionActionsForCounselee({ session }: { session: CounselingSession }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [rebookOpen, setRebookOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  // Report 3 §2.2 — the 8 feedback fields.
  const [fb, setFb] = useState<{
    session_usefulness: SessionFeedback["session_usefulness"];
    usefulness_text: string;
    counsellor_empathy: SessionFeedback["counsellor_empathy"];
    session_ending: SessionFeedback["session_ending"];
    would_rechoose: SessionFeedback["would_rechoose"];
    rechoose_text: string;
    improvement_suggestions: string;
    rating: string;
  }>({
    session_usefulness: "",
    usefulness_text: "",
    counsellor_empathy: "",
    session_ending: "",
    would_rechoose: "",
    rechoose_text: "",
    improvement_suggestions: "",
    rating: "8",
  });

  const { data: followups } = useQuery({
    queryKey: ["counseling", "followups", session.id],
    queryFn: () => listFollowups(session.id),
    enabled: session.status === "completed",
  });

  const feedbackMut = useMutation({
    mutationFn: () =>
      submitSessionFeedback(session.id, {
        ...fb,
        rating: Number(fb.rating),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "my-sessions"] });
      toast.success("Feedback submitted.");
      setFeedbackOpen(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Report 3 §1.16: counselee cancels with a reason, then gets a rebook prompt.
  const cancelMut = useMutation({
    mutationFn: () => cancelSession(session.id, "counselee", cancelReason),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "my-sessions"] });
      const tier = data.cancellation?.refund_tier ?? "none";
      toast.success(
        tier === "full"
          ? "Session cancelled — full refund."
          : tier === "half"
            ? "Session cancelled — 50% refund."
            : "Session cancelled — no refund (under 4 hours).",
      );
      setCancelOpen(false);
      setRebookOpen(true);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const confirmFuMut = useMutation({
    mutationFn: (fuId: number) => confirmFollowup(fuId),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["counseling"] });
      // H15/D8 §2.1/§3.3: route the follow-up payment through the gateway
      // too — no longer assumed paid.
      if (data.checkout_url) {
        toast.success("Redirecting to payment…");
        window.location.href = data.checkout_url;
        return;
      }
      toast.success("Follow-up confirmed! A new session has been created.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const declineFuMut = useMutation({
    mutationFn: (fuId: number) => declineFollowup(fuId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling"] });
      toast.success("Follow-up declined.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const pendingFollowups = (followups ?? []).filter((f) => f.status === "proposed");
  const set = (k: keyof typeof fb) => (e: { target: { value: string } }) =>
    setFb((prev) => ({ ...prev, [k]: e.target.value }));

  return (
    <div className="flex flex-col gap-2">
      {/* Feedback button for completed sessions */}
      {session.status === "completed" && (
        <Button size="sm" variant="outline" onClick={() => setFeedbackOpen(true)}>
          Give Feedback
        </Button>
      )}

      {/* Report 3 §1.16: counselee cancel (confirmed/pending sessions) */}
      {(session.status === "confirmed" || session.status === "pending") && (
        <Button size="sm" variant="danger" onClick={() => setCancelOpen(true)}>
          Cancel
        </Button>
      )}

      {/* Follow-up proposals (Report 3 §2.7/§2.8: reminder + payment via confirm) */}
      {pendingFollowups.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2">
          <div className="text-xs font-medium text-amber-800">
            Follow-up proposed — confirm and pay to lock it in:
          </div>
          {pendingFollowups.map((fu) => (
            <div key={fu.id} className="mt-1 flex items-center gap-2">
              <span className="text-xs text-amber-700">
                {new Date(fu.proposed_time).toLocaleString()}
              </span>
              <FollowupCountdown target={fu.proposed_time} />
              <Button
                size="sm"
                onClick={() => confirmFuMut.mutate(fu.id)}
                loading={confirmFuMut.isPending}
              >
                Confirm &amp; pay
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => declineFuMut.mutate(fu.id)}
                loading={declineFuMut.isPending}
              >
                Decline
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Cancel modal (Report 3 §1.16) */}
      {cancelOpen && (
        <Modal open onClose={() => setCancelOpen(false)} title="Cancel session" size="sm">
          <div className="space-y-3">
            <div>
              <Label htmlFor="cancel-reason" required>
                Reason for cancellation
              </Label>
              <textarea
                id="cancel-reason"
                rows={3}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Tell us why you need to cancel…"
              />
            </div>
            <p className="text-xs text-slate-500">
              Refund: full if &gt;24h before the session, 50% if &gt;4h, none under 4h.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCancelOpen(false)}>
                Keep session
              </Button>
              <Button
                variant="danger"
                onClick={() => cancelMut.mutate()}
                loading={cancelMut.isPending}
                disabled={!cancelReason.trim()}
              >
                Cancel session
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Rebook prompt (Report 3 §1.16) */}
      {rebookOpen && (
        <Modal open onClose={() => setRebookOpen(false)} title="Book another session?" size="sm">
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              Your session was cancelled. Would you like to book another timeslot with this
              counsellor or browse other counsellors?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRebookOpen(false)}>
                Not now
              </Button>
              <Button
                onClick={() => {
                  setRebookOpen(false);
                  window.location.hash = "#browse";
                  window.location.reload();
                }}
              >
                Browse counsellors
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Feedback modal — 8 fields (Report 3 §2.2) */}
      {feedbackOpen && (
        <Modal open onClose={() => setFeedbackOpen(false)} title="Session Feedback" size="md">
          <div className="space-y-3">
            {/* 1 */}
            <div>
              <Label required>1. Was the session useful?</Label>
              <select
                className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                value={fb.session_usefulness}
                onChange={set("session_usefulness")}
              >
                <option value="">Select…</option>
                <option value="very_useful">Very useful</option>
                <option value="useful">Useful</option>
                <option value="somewhat_useful">Somewhat useful</option>
                <option value="not_useful">Not useful</option>
              </select>
            </div>
            {/* 2 */}
            <div>
              <Label>2. A few words on how it was (or wasn&apos;t) useful</Label>
              <textarea
                rows={2}
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                value={fb.usefulness_text}
                onChange={set("usefulness_text")}
              />
            </div>
            {/* 3 */}
            <div>
              <Label required>3. Was the counsellor friendly and empathetic?</Label>
              <select
                className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                value={fb.counsellor_empathy}
                onChange={set("counsellor_empathy")}
              >
                <option value="">Select…</option>
                <option value="very_much">Very much</option>
                <option value="somewhat">Somewhat</option>
                <option value="not_much">Not much</option>
              </select>
            </div>
            {/* 4 */}
            <div>
              <Label>4. How did the session end?</Label>
              <select
                className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                value={fb.session_ending}
                onChange={set("session_ending")}
              >
                <option value="">Select…</option>
                <option value="on_time">Ended on time</option>
                <option value="before_time">Ended before time</option>
                <option value="late">Ended late</option>
              </select>
            </div>
            {/* 5 */}
            <div>
              <Label required>5. Would you choose this counsellor again?</Label>
              <select
                className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                value={fb.would_rechoose}
                onChange={set("would_rechoose")}
              >
                <option value="">Select…</option>
                <option value="yes">Yes</option>
                <option value="maybe">Maybe</option>
                <option value="no">No</option>
              </select>
            </div>
            {/* 6 */}
            <div>
              <Label>6. Why would you (or wouldn&apos;t you) choose them again?</Label>
              <textarea
                rows={2}
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                value={fb.rechoose_text}
                onChange={set("rechoose_text")}
              />
            </div>
            {/* 7 */}
            <div>
              <Label>7. How can we improve the counselling service?</Label>
              <textarea
                rows={2}
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                value={fb.improvement_suggestions}
                onChange={set("improvement_suggestions")}
              />
            </div>
            {/* 8 */}
            <div>
              <Label required>8. Rate the counsellor (1 = very poor, 10 = excellent)</Label>
              <select
                className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                value={fb.rating}
                onChange={set("rating")}
              >
                {Array.from({ length: 10 }, (_, i) => 10 - i).map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
              <Button variant="outline" onClick={() => setFeedbackOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => feedbackMut.mutate()}
                loading={feedbackMut.isPending}
                disabled={!fb.session_usefulness || !fb.counsellor_empathy || !fb.would_rechoose}
              >
                Submit feedback
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// CNS-5 (§3.3): live countdown to a proposed follow-up session.
function FollowupCountdown({ target }: { target: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);
  const diff = new Date(target).getTime() - now;
  if (Number.isNaN(diff)) return null;
  if (diff <= 0) return <span className="text-xs font-medium text-amber-800">now</span>;
  const days = Math.floor(diff / 86_400_000);
  const hours = Math.floor((diff % 86_400_000) / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  const parts = [days ? `${days}d` : "", hours ? `${hours}h` : "", `${mins}m`].filter(Boolean);
  return <span className="text-xs font-medium text-amber-800">in {parts.join(" ")}</span>;
}
