/**
 * Course Structure Editor — interactive tree for building course structure.
 *
 * Hierarchy: Lesson → Topic → Session → Content + Assignments
 * Each level has an inline "Add" form.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Input, Label, useToast } from "@/components/ui";
import {
  addAssignment,
  addContent,
  addLesson,
  addSession,
  addTopic,
  deleteLesson,
  deleteTopic,
  deleteSession,
  deleteContent,
  deleteAssignment,
  updateLesson,
  updateTopic,
  updateSession,
  type CourseLesson,
  type LessonTopic,
  type TopicSession,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { TimelinerEditor } from "./TimelinerEditor";

// Hook: refresh all course data after a mutation
function useRefreshCourse() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
  };
}

// Generic delete button
function DeleteButton({ onDelete }: { onDelete: () => void }) {
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <Button
        size="sm"
        variant="outline"
        onClick={() => setConfirming(true)}
        className="text-danger-600 hover:bg-danger-50"
      >
        ✕
      </Button>
    );
  }
  return (
    <div className="flex gap-1">
      <Button
        size="sm"
        variant="danger"
        onClick={() => {
          onDelete();
          setConfirming(false);
        }}
      >
        Delete?
      </Button>
      <Button size="sm" variant="outline" onClick={() => setConfirming(false)}>
        No
      </Button>
    </div>
  );
}

// Inline editable title
function EditableTitle({ title, onSave }: { title: string; onSave: (newTitle: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(title);

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="text-left hover:underline"
        title="Click to edit"
      >
        {title}
      </button>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-8 text-sm"
        autoFocus
      />
      <Button
        size="sm"
        onClick={() => {
          onSave(value);
          setEditing(false);
        }}
      >
        ✓
      </Button>
      <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
        ✕
      </Button>
    </div>
  );
}

export function CourseStructureEditor({
  courseId,
  lessons,
  canManage,
}: {
  courseId: number;
  lessons: CourseLesson[];
  canManage: boolean;
}) {
  if (!canManage) {
    // Read-only view for students
    if (lessons.length === 0) {
      return <p className="py-4 text-center text-sm text-slate-500">No lessons defined yet.</p>;
    }
    return (
      <div className="space-y-4">
        {lessons.map((lesson) => (
          <LessonTree key={lesson.id} lesson={lesson} canManage={false} courseId={courseId} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {lessons.length === 0 ? (
        <p className="py-4 text-center text-sm text-slate-500">
          No lessons yet. Add your first lesson below.
        </p>
      ) : (
        lessons.map((lesson) => (
          <LessonTree key={lesson.id} lesson={lesson} canManage={true} courseId={courseId} />
        ))
      )}
      <AddLessonForm courseId={courseId} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lesson tree (lesson → topics → sessions → contents/assignments)
// ---------------------------------------------------------------------------

function LessonTree({
  lesson,
  canManage,
  courseId,
}: {
  lesson: CourseLesson;
  canManage: boolean;
  courseId: number;
}) {
  const toast = useToast();
  const refresh = useRefreshCourse();
  const [expanded, setExpanded] = useState(true);
  const [showAddTopic, setShowAddTopic] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteLesson(lesson.id),
    onSuccess: () => {
      refresh();
      toast.success("Lesson deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const editMutation = useMutation({
    mutationFn: (newTitle: string) => updateLesson(lesson.id, { title: newTitle }),
    onSuccess: () => {
      refresh();
      toast.success("Lesson updated.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="rounded-md border border-slate-200 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)}>
            <span className="text-sm text-slate-400">{expanded ? "▼" : "▶"}</span>
          </button>
          <span className="font-semibold text-slate-900">
            {canManage ? (
              <EditableTitle title={lesson.title} onSave={(t) => editMutation.mutate(t)} />
            ) : (
              lesson.title
            )}
          </span>
          <span className="text-xs text-slate-500">(Week {lesson.week_number})</span>
        </div>
        {canManage && (
          <div className="flex items-center gap-1">
            {expanded && (
              <Button size="sm" variant="outline" onClick={() => setShowAddTopic(!showAddTopic)}>
                + Topic
              </Button>
            )}
            <DeleteButton onDelete={() => deleteMutation.mutate()} />
          </div>
        )}
      </div>

      {expanded && (
        <div className="ml-4 mt-3 space-y-3">
          {lesson.topics.length === 0 ? (
            <p className="text-xs text-slate-500">No topics.</p>
          ) : (
            lesson.topics.map((topic) => (
              <TopicTree key={topic.id} topic={topic} canManage={canManage} courseId={courseId} />
            ))
          )}
          {showAddTopic && (
            <AddTopicForm lessonId={lesson.id} onDone={() => setShowAddTopic(false)} />
          )}
        </div>
      )}
    </div>
  );
}

function TopicTree({
  topic,
  canManage,
}: {
  topic: LessonTopic;
  canManage: boolean;
  courseId: number;
}) {
  const toast = useToast();
  const refresh = useRefreshCourse();
  const [expanded, setExpanded] = useState(true);
  const [showAddSession, setShowAddSession] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteTopic(topic.id),
    onSuccess: () => {
      refresh();
      toast.success("Topic deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const editMutation = useMutation({
    mutationFn: (newTitle: string) => updateTopic(topic.id, { title: newTitle }),
    onSuccess: () => {
      refresh();
      toast.success("Topic updated.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="border-l-2 border-slate-100 pl-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)}>
            <span className="text-xs text-slate-400">{expanded ? "▼" : "▶"}</span>
          </button>
          <span className="text-sm font-medium text-slate-700">
            {canManage ? (
              <EditableTitle title={topic.title} onSave={(t) => editMutation.mutate(t)} />
            ) : (
              topic.title
            )}
          </span>
        </div>
        {canManage && (
          <div className="flex items-center gap-1">
            {expanded && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAddSession(!showAddSession)}
              >
                + Session
              </Button>
            )}
            <DeleteButton onDelete={() => deleteMutation.mutate()} />
          </div>
        )}
      </div>

      {expanded && (
        <div className="ml-3 mt-2 space-y-2">
          {topic.sessions.length === 0 ? (
            <p className="text-xs text-slate-500">No sessions.</p>
          ) : (
            topic.sessions.map((session) => (
              <SessionTree key={session.id} session={session} canManage={canManage} />
            ))
          )}
          {showAddSession && (
            <AddSessionForm topicId={topic.id} onDone={() => setShowAddSession(false)} />
          )}
        </div>
      )}
    </div>
  );
}

function SessionTree({ session, canManage }: { session: TopicSession; canManage: boolean }) {
  const toast = useToast();
  const refresh = useRefreshCourse();
  const [expanded, setExpanded] = useState(false);
  const [showAddContent, setShowAddContent] = useState(false);
  const [showAddAssignment, setShowAddAssignment] = useState(false);
  const [timelinerContent, setTimelinerContent] = useState<{
    id: number;
    url: string;
    title: string;
  } | null>(null);

  const deleteMutation = useMutation({
    mutationFn: () => deleteSession(session.id),
    onSuccess: () => {
      refresh();
      toast.success("Session deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const editMutation = useMutation({
    mutationFn: (newTitle: string) => updateSession(session.id, { title: newTitle }),
    onSuccess: () => {
      refresh();
      toast.success("Session updated.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const deleteContentMutation = useMutation({
    mutationFn: (contentId: number) => deleteContent(contentId),
    onSuccess: () => {
      refresh();
      toast.success("Content deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const deleteAssignmentMutation = useMutation({
    mutationFn: (assignmentId: number) => deleteAssignment(assignmentId),
    onSuccess: () => {
      refresh();
      toast.success("Assignment deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="rounded border border-slate-100 p-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)}>
            <span className="text-xs text-slate-400">{expanded ? "▼" : "▶"}</span>
          </button>
          <span className="text-xs font-medium text-slate-700">
            {canManage ? (
              <EditableTitle title={session.title} onSave={(t) => editMutation.mutate(t)} />
            ) : (
              session.title
            )}
          </span>
          <span className="text-xs text-slate-400">
            ({session.contents.length} content, {session.assignments.length} assignment)
          </span>
          {session.contents.some((c) => c.interactive_questions?.length > 0) && (
            <Badge variant="warning">interactive</Badge>
          )}
        </div>
        {canManage && (
          <div className="flex items-center gap-1">
            {expanded && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAddContent(!showAddContent)}
                >
                  + Content
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAddAssignment(!showAddAssignment)}
                >
                  + Assignment
                </Button>
              </>
            )}
            <DeleteButton onDelete={() => deleteMutation.mutate()} />
          </div>
        )}
      </div>

      {expanded && (
        <div className="ml-3 mt-2 space-y-2">
          {/* Contents */}
          {session.contents.length > 0 && (
            <div>
              <div className="text-xs font-medium uppercase text-slate-400">Contents</div>
              {session.contents.map((c) => (
                <div key={c.id} className="ml-2 flex items-center gap-1 text-xs text-slate-600">
                  <Badge variant="outline">{c.content_format}</Badge> {c.title}
                  {c.duration_seconds && (
                    <span className="text-slate-400">({c.duration_seconds}s)</span>
                  )}
                  {c.interactive_questions?.length > 0 && (
                    <span className="text-amber-600">({c.interactive_questions.length} Q)</span>
                  )}
                  {canManage && c.content_format === "video" && c.content_url && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setTimelinerContent({ id: c.id, url: c.content_url, title: c.title })
                      }
                    >
                      🎬 Timeliner
                    </Button>
                  )}
                  {canManage && (
                    <DeleteButton onDelete={() => deleteContentMutation.mutate(c.id)} />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Assignments */}
          {session.assignments.length > 0 && (
            <div>
              <div className="text-xs font-medium uppercase text-slate-400">Assignments</div>
              {session.assignments.map((a) => (
                <div key={a.id} className="ml-2 flex items-center gap-1 text-xs text-slate-600">
                  {a.title}
                  {a.report_submission_enabled && <Badge variant="primary">report</Badge>}
                  {canManage && (
                    <DeleteButton onDelete={() => deleteAssignmentMutation.mutate(a.id)} />
                  )}
                </div>
              ))}
            </div>
          )}

          {showAddContent && (
            <AddContentForm sessionId={session.id} onDone={() => setShowAddContent(false)} />
          )}
          {showAddAssignment && (
            <AddAssignmentForm sessionId={session.id} onDone={() => setShowAddAssignment(false)} />
          )}
        </div>
      )}

      {timelinerContent && (
        <TimelinerEditor
          contentId={timelinerContent.id}
          contentUrl={timelinerContent.url}
          title={timelinerContent.title}
          onClose={() => setTimelinerContent(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline Add Forms
// ---------------------------------------------------------------------------

function useCourseRefresh(courseId: number) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
  };
}

function AddLessonForm({ courseId }: { courseId: number }) {
  const toast = useToast();
  const refresh = useCourseRefresh(courseId);
  const [title, setTitle] = useState("");
  const [weekNumber, setWeekNumber] = useState("1");

  const mutation = useMutation({
    mutationFn: () =>
      addLesson(courseId, {
        title,
        week_number: Number(weekNumber),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Lesson added.");
      setTitle("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="flex items-end gap-2 border-t border-slate-100 pt-3"
    >
      <div className="flex-1">
        <Label htmlFor="lesson-title" required>
          New lesson title
        </Label>
        <Input
          id="lesson-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., Introduction to Python"
          required
        />
      </div>
      <div className="w-24">
        <Label htmlFor="lesson-week">Week</Label>
        <Input
          id="lesson-week"
          type="number"
          min="1"
          value={weekNumber}
          onChange={(e) => setWeekNumber(e.target.value)}
        />
      </div>
      <Button type="submit" loading={mutation.isPending} disabled={!title}>
        Add lesson
      </Button>
    </form>
  );
}

function AddTopicForm({ lessonId, onDone }: { lessonId: number; onDone: () => void }) {
  const toast = useToast();
  const [title, setTitle] = useState("");

  const mutation = useMutation({
    mutationFn: () => addTopic(lessonId, { title }),
    onSuccess: () => {
      // Invalidate all course queries to refresh the tree
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success("Topic added.");
      setTitle("");
      onDone();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const queryClient = useQueryClient();

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="flex items-end gap-2"
    >
      <div className="flex-1">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Topic title"
          required
        />
      </div>
      <Button type="submit" size="sm" loading={mutation.isPending} disabled={!title}>
        Add
      </Button>
      <Button type="button" size="sm" variant="outline" onClick={onDone}>
        Cancel
      </Button>
    </form>
  );
}

function AddSessionForm({ topicId, onDone }: { topicId: number; onDone: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");

  const mutation = useMutation({
    mutationFn: () => addSession(topicId, { title }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success("Session added.");
      setTitle("");
      onDone();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="flex items-end gap-2"
    >
      <div className="flex-1">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Session title"
          required
        />
      </div>
      <Button type="submit" size="sm" loading={mutation.isPending} disabled={!title}>
        Add
      </Button>
      <Button type="button" size="sm" variant="outline" onClick={onDone}>
        Cancel
      </Button>
    </form>
  );
}

function AddContentForm({ sessionId, onDone }: { sessionId: number; onDone: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [format, setFormat] = useState<"video" | "audio" | "text">("video");
  const [url, setUrl] = useState("");
  const [textContent, setTextContent] = useState("");
  const [duration, setDuration] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      addContent(sessionId, {
        title,
        content_format: format,
        content_url: url,
        text_content: textContent,
        duration_seconds: duration ? Number(duration) : undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success("Content added.");
      setTitle("");
      setUrl("");
      setTextContent("");
      setDuration("");
      onDone();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="space-y-2 rounded border border-slate-100 p-2"
    >
      <div className="flex gap-2">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Content title"
          required
          className="flex-1"
        />
        <select
          className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm"
          value={format}
          onChange={(e) => setFormat(e.target.value as "video" | "audio" | "text")}
        >
          <option value="video">Video</option>
          <option value="audio">Audio</option>
          <option value="text">Text</option>
        </select>
      </div>
      {(format === "video" || format === "audio") && (
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Media URL (or base64 data URL)"
        />
      )}
      {format === "text" && (
        <textarea
          value={textContent}
          onChange={(e) => setTextContent(e.target.value)}
          placeholder="Text content"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
        />
      )}
      {(format === "video" || format === "audio") && (
        <Input
          type="number"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          placeholder="Duration (seconds, optional)"
        />
      )}
      <div className="flex gap-2">
        <Button type="submit" size="sm" loading={mutation.isPending} disabled={!title}>
          Add content
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function AddAssignmentForm({ sessionId, onDone }: { sessionId: number; onDone: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [resourceUrl, setResourceUrl] = useState("");
  const [reportEnabled, setReportEnabled] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      addAssignment(sessionId, {
        title,
        description,
        resource_url: resourceUrl,
        report_submission_enabled: reportEnabled,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success("Assignment added.");
      setTitle("");
      setDescription("");
      setResourceUrl("");
      setReportEnabled(false);
      onDone();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="space-y-2 rounded border border-slate-100 p-2"
    >
      <Input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Assignment title"
        required
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        rows={2}
        className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
      />
      <Input
        value={resourceUrl}
        onChange={(e) => setResourceUrl(e.target.value)}
        placeholder="Resource URL (YouTube, doc link, etc.)"
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={reportEnabled}
          onChange={(e) => setReportEnabled(e.target.checked)}
          className="h-4 w-4"
        />
        Enable report submission
      </label>
      <div className="flex gap-2">
        <Button type="submit" size="sm" loading={mutation.isPending} disabled={!title}>
          Add assignment
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
