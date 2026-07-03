/**
 * Question Bank Categories page — tree view + CRUD for question categories.
 *
 * Categories support unlimited nesting via parent FK. Created by Psychometrician,
 * deleted by CJ Admin (with permission). Each category shows question count and
 * subcategory count.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Modal,
  Spinner,
} from "@/components/ui";
import {
  createCategory,
  deleteCategory,
  getCategoryTree,
  updateCategory,
  type Category,
} from "@/api/questionBank";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const CAT_KEY = ["question-bank", "categories"];
const TREE_KEY = ["question-bank", "categories", "tree"];

interface CategoryNode extends Category {
  subcategories?: CategoryNode[];
}

export default function CategoriesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Category | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null);

  // Fetch the tree view (nested categories)
  const { data: tree, isLoading } = useQuery({
    queryKey: TREE_KEY,
    queryFn: () => getCategoryTree() as Promise<CategoryNode[]>,
  });

  const canManage = ["psychometrician", "cj_admin"].includes(user?.role ?? "");

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; parent?: number | null; description?: string }) =>
      createCategory(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TREE_KEY });
      void queryClient.invalidateQueries({ queryKey: CAT_KEY });
      setCreateOpen(false);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: Partial<{ name: string; description: string; is_active: boolean }>;
    }) => updateCategory(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TREE_KEY });
      void queryClient.invalidateQueries({ queryKey: CAT_KEY });
      setEditTarget(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TREE_KEY });
      void queryClient.invalidateQueries({ queryKey: CAT_KEY });
      setDeleteTarget(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Question Categories</CardTitle>
              <CardDescription>
                Organize questions into hierarchical categories. Categories help filter and group
                questions when building assessments.
              </CardDescription>
            </div>
            {canManage && <Button onClick={() => setCreateOpen(true)}>Create category</Button>}
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="error" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {isLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : !tree || tree.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">
              No categories yet. Create one to get started.
            </p>
          ) : (
            <div className="space-y-1">
              {tree.map((node) => (
                <CategoryTreeRow
                  key={node.id}
                  node={node}
                  depth={0}
                  canManage={canManage}
                  onEdit={(c) => setEditTarget(c)}
                  onDelete={(c) => setDeleteTarget(c)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create modal */}
      <CategoryFormModal
        open={createOpen}
        title="Create Category"
        description="Add a new category to organize questions."
        onClose={() => setCreateOpen(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
        loading={createMutation.isPending}
        tree={tree}
      />

      {/* Edit modal */}
      <CategoryFormModal
        open={Boolean(editTarget)}
        title="Edit Category"
        description="Update the category name, parent, or description."
        initial={editTarget ?? undefined}
        onClose={() => setEditTarget(null)}
        onSubmit={(payload) => editTarget && updateMutation.mutate({ id: editTarget.id, payload })}
        loading={updateMutation.isPending}
        tree={tree}
        excludeId={editTarget?.id}
      />

      {/* Delete confirm modal */}
      <DeleteCategoryModal
        category={deleteTarget}
        loading={deleteMutation.isPending}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recursive tree row
// ---------------------------------------------------------------------------

function CategoryTreeRow({
  node,
  depth,
  canManage,
  onEdit,
  onDelete,
}: {
  node: CategoryNode;
  depth: number;
  canManage: boolean;
  onEdit: (c: Category) => void;
  onDelete: (c: Category) => void;
}) {
  return (
    <>
      <div
        className="flex items-center justify-between rounded-md py-2 pr-2 hover:bg-slate-50"
        style={{ paddingLeft: `${depth * 1.5 + 0.5}rem` }}
      >
        <div className="flex items-center gap-2">
          {node.subcategories && node.subcategories.length > 0 ? (
            <span className="text-slate-400">▾</span>
          ) : (
            <span className="w-4 text-slate-300">•</span>
          )}
          <span className="text-sm font-medium text-slate-900">{node.name}</span>
          {!node.is_active && <Badge variant="default">Inactive</Badge>}
        </div>
        <div className="flex items-center gap-1">
          {canManage && (
            <>
              <Button variant="ghost" size="sm" onClick={() => onEdit(node)}>
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger hover:bg-danger-50"
                onClick={() => onDelete(node)}
              >
                Delete
              </Button>
            </>
          )}
        </div>
      </div>
      {node.subcategories &&
        node.subcategories.map((child) => (
          <CategoryTreeRow
            key={child.id}
            node={child}
            depth={depth + 1}
            canManage={canManage}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Create / Edit form modal
// ---------------------------------------------------------------------------

function CategoryFormModal({
  open,
  title,
  description,
  initial,
  onClose,
  onSubmit,
  loading,
  tree,
  excludeId,
}: {
  open: boolean;
  title: string;
  description: string;
  initial?: Category;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    parent?: number | null;
    description?: string;
    is_active?: boolean;
  }) => void;
  loading: boolean;
  tree?: CategoryNode[];
  excludeId?: number;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [parent, setParent] = useState<number | "">(initial?.parent ?? "");
  const [desc, setDesc] = useState(initial?.description ?? "");

  // Reset when initial changes (e.g. opening edit on a different row)
  const initialKey = initial?.id != null ? String(initial.id) : "new";
  const [lastKey, setLastKey] = useState<string>(initialKey);
  if (lastKey !== initialKey) {
    setLastKey(initialKey);
    setName(initial?.name ?? "");
    setParent(initial?.parent ?? "");
    setDesc(initial?.description ?? "");
  }

  // Flatten the tree into a list for the parent dropdown (excluding the
  // category being edited and its descendants to prevent cycles).
  const flatList: { id: number; path: string }[] = [];
  const collect = (nodes: CategoryNode[], path: string, excludeId?: number) => {
    for (const n of nodes) {
      if (n.id === excludeId) continue;
      const newPath = path ? `${path} > ${n.name}` : n.name;
      flatList.push({ id: n.id, path: newPath });
      if (n.subcategories) collect(n.subcategories, newPath, excludeId);
    }
  };
  if (tree) collect(tree, "", excludeId);

  return (
    <Modal open={open} onClose={onClose} title={title} description={description} size="md">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          onSubmit({
            name: name.trim(),
            parent: parent === "" ? null : parent,
            description: desc.trim(),
          });
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="cat-name" required>
            Category name
          </Label>
          <Input
            id="cat-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Quantitative Aptitude"
            autoFocus
          />
        </div>
        <div>
          <Label htmlFor="cat-parent">Parent category (optional)</Label>
          <select
            id="cat-parent"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={parent}
            onChange={(e) => setParent(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">No parent (top-level)</option>
            {flatList.map((c) => (
              <option key={c.id} value={c.id}>
                {c.path}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="cat-desc">Description (optional)</Label>
          <textarea
            id="cat-desc"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Brief description of what questions in this category cover"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            {initial ? "Update category" : "Create category"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Delete confirm modal
// ---------------------------------------------------------------------------

function DeleteCategoryModal({
  category,
  loading,
  onClose,
  onConfirm,
}: {
  category: Category | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!category) return null;
  return (
    <Modal
      open={Boolean(category)}
      onClose={onClose}
      title="Delete category"
      description="This action cannot be undone. If this category has subcategories, they will also be deleted. Questions in this category will have their category cleared (not deleted)."
      size="sm"
    >
      <p className="text-sm text-slate-600">
        Are you sure you want to delete the category{" "}
        <span className="font-medium text-slate-900">"{category.name}"</span>?
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" loading={loading} onClick={onConfirm}>
          Delete category
        </Button>
      </div>
    </Modal>
  );
}
