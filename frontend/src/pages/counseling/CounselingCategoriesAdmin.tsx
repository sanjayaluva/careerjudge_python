/**
 * Counselling categories — CJ Admin adds, renames, deactivates and deletes the
 * ("domain") categories used to tag counsellors (Report 9 #105). They used to
 * be fixed in code. A category still used by counsellors or sessions cannot
 * be deleted; deactivating hides it from new tags and bookings while existing
 * records keep it.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  Badge,
  Button,
  Input,
  Label,
  Modal,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  useToast,
} from "@/components/ui";
import { extractApiError } from "@/api/client";
import {
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
  type CounselingCategory,
} from "@/api/counseling";

const KEY = ["counseling", "categories"];

export function CounselingCategoriesAdmin() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<CounselingCategory | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: KEY,
    queryFn: () => listCategories(),
  });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: KEY });
    // Counsellor rows show the category names.
    void queryClient.invalidateQueries({ queryKey: ["counseling", "counsellors"] });
  };

  const add = useMutation({
    mutationFn: () => createCategory({ label: label.trim(), description: description.trim() }),
    onSuccess: () => {
      toast.success("Category added.");
      setLabel("");
      setDescription("");
      refresh();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const toggle = useMutation({
    mutationFn: (c: CounselingCategory) => updateCategory(c.id, { is_active: !c.is_active }),
    onSuccess: (c) => {
      toast.success(c.is_active ? "Category activated." : "Category deactivated.");
      refresh();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const remove = useMutation({
    mutationFn: (c: CounselingCategory) => deleteCategory(c.id),
    onSuccess: () => {
      toast.success("Category deleted.");
      refresh();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        The categories used to tag counsellors and to filter them. A category in use cannot be
        deleted — deactivate it to stop offering it; counsellors and sessions that already have it
        keep it.
      </p>

      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (label.trim()) add.mutate();
        }}
      >
        <div className="min-w-[14rem] flex-1">
          <Label htmlFor="cat-label" required>
            New category
          </Label>
          <Input
            id="cat-label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g., Study abroad counselling"
            maxLength={100}
          />
        </div>
        <div className="min-w-[14rem] flex-1">
          <Label htmlFor="cat-desc">Description (optional)</Label>
          <Input
            id="cat-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <Button type="submit" loading={add.isPending} disabled={!label.trim()}>
          Add category
        </Button>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner size="lg" />
        </div>
      ) : categories.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">No categories yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Category</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Counsellors</TableHead>
              <TableHead>Sessions</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {categories.map((c) => {
              const inUse = c.counsellor_count > 0 || c.session_count > 0;
              return (
                <TableRow key={c.id}>
                  <TableCell className="font-medium text-slate-900">{c.label || c.name}</TableCell>
                  <TableCell className="text-slate-600">{c.description || "—"}</TableCell>
                  <TableCell className="text-slate-600">{c.counsellor_count}</TableCell>
                  <TableCell className="text-slate-600">{c.session_count}</TableCell>
                  <TableCell>
                    <Badge variant={c.is_active ? "success" : "default"}>
                      {c.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={() => setEditing(c)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        loading={toggle.isPending && toggle.variables?.id === c.id}
                        onClick={() => toggle.mutate(c)}
                      >
                        {c.is_active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        disabled={inUse}
                        title={inUse ? "In use — deactivate it instead" : undefined}
                        loading={remove.isPending && remove.variables?.id === c.id}
                        onClick={() => {
                          if (window.confirm(`Delete the category "${c.label || c.name}"?`)) {
                            remove.mutate(c);
                          }
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {editing && (
        <EditCategoryModal
          category={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function EditCategoryModal({
  category,
  onClose,
  onSaved,
}: {
  category: CounselingCategory;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [label, setLabel] = useState(category.label || category.name);
  const [description, setDescription] = useState(category.description);
  const save = useMutation({
    mutationFn: () =>
      updateCategory(category.id, { label: label.trim(), description: description.trim() }),
    onSuccess: () => {
      toast.success("Category updated.");
      onSaved();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
  return (
    <Modal open onClose={onClose} title="Edit category" size="sm">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (label.trim()) save.mutate();
        }}
      >
        <div>
          <Label htmlFor="edit-cat-label" required>
            Name
          </Label>
          <Input
            id="edit-cat-label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={100}
          />
        </div>
        <div>
          <Label htmlFor="edit-cat-desc">Description</Label>
          <Input
            id="edit-cat-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={!label.trim()}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  );
}
