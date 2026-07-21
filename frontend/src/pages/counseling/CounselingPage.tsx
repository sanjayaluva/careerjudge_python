/**
 * Counseling page — browse counsellors + view my sessions.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

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
  listCounsellors,
  listMySessions,
  bookSession,
  listCounsellorTimeslots,
  type CounsellorProfile,
  type TimeSlot,
} from "@/api/counseling";
import { extractApiError } from "@/api/client";

export default function CounselingPage() {
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

        <Tabs defaultValue="browse">
          <div className="px-6">
            <TabsList>
              <TabsTrigger value="browse">Browse Counsellors ({counsellors.length})</TabsTrigger>
              <TabsTrigger value="my-sessions">My Sessions ({sessions.length})</TabsTrigger>
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
                      <TableCell className="text-slate-500">${c.hourly_rate}/hr</TableCell>
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
                      <TableCell className="text-slate-500">${s.fee}</TableCell>
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
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);

  const { data: timeslots, isLoading } = useQuery({
    queryKey: ["counseling", "counsellors", counsellor.id, "timeslots"],
    queryFn: () => listCounsellorTimeslots(counsellor.id),
  });

  const bookMutation = useMutation({
    mutationFn: () => {
      if (!selectedSlot) throw new Error("No slot selected");
      return bookSession({
        counsellor: counsellor.id,
        timeslot: selectedSlot.id,
        topic,
        description,
        mode: "online",
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "my-sessions"] });
      void queryClient.invalidateQueries({
        queryKey: ["counseling", "counsellors", counsellor.id, "timeslots"],
      });
      toast.success("Session booked! Awaiting counsellor confirmation.");
      onClose();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const availableSlots = (timeslots ?? []).filter((s) => s.status === "available");

  return (
    <Modal
      open
      onClose={onClose}
      title={`Book with ${counsellor.full_name}`}
      description={`$${counsellor.hourly_rate}/hr`}
      size="md"
    >
      <div className="space-y-4">
        {counsellor.bio && (
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Bio</div>
            <p className="mt-1 text-sm text-slate-700">{counsellor.bio}</p>
          </div>
        )}

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
          <Label required>Available time slots</Label>
          {isLoading ? (
            <Spinner />
          ) : availableSlots.length === 0 ? (
            <p className="text-sm text-slate-500">No available slots. Check back later.</p>
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

        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => bookMutation.mutate()}
            loading={bookMutation.isPending}
            disabled={!topic || !selectedSlot}
          >
            Book session (${counsellor.hourly_rate})
          </Button>
        </div>
      </div>
    </Modal>
  );
}
