/**
 * CategoryManager — embeddable question category tree with CRUD.
 *
 * Used inside the QuestionBankPage (left panel) so category management lives
 * inside the main Question Bank page instead of a separate sidebar entry.
 *
 * Features:
 *   - Collapsible tree (click chevron to expand/collapse)
 *   - Create / Edit / Delete with parent nesting
 *   - Edit modal pre-fills ALL fields including description
 *   - Delete confirmation warns about cascade to subcategories
 *   - Only visible to psychometrician + cj_admin (canManage)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ChevronDown, ChevronRight, FolderPlus, Pencil, Trash2 } from "lucide-react";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
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

const TREE_KEY = ["question-bank", "categories", "tree"];
const CAT_KEY = ["question-bank", "categories"];

interface CategoryNode extends Category {
  subcategories?: CategoryNode[];
}

export interface CategoryManagerProps {
  /** When true, show the Create/Edit/Delete action buttons. */
  canManage: boolean;
  /** Optional callback invoked when a category is clicked (e.g. to filter questions). */
  onSelectCategory?: (categoryId: number | null) => void;
  /** Currently selected category ID (for highlighting). */
  selectedCategoryId?: number | null;
}

export function CategoryManager({
  canManage,
  onSelectCategory,
  selectedCategoryId,
}: CategoryManagerProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Category | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null);

  const { data: tree, isLoading } = useQuery({
    queryKey: TREE_KEY,
    queryFn: () => getCategoryTree() as Promise<CategoryNode[]>,
  });

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
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Categories</h3>
          <p className="text-xs text-slate-500">Organize questions hierarchically</p>
        </div>
        {canManage && (
          <Button variant="ghost" size="sm" onClick={() => setCreateOpen(true)}>
            <FolderPlus className="mr-1 h-4 w-4" />
            New
          </Button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-2">
        {error && (
          <Alert variant="error" className="mb-2">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spinner size="sm" />
          </div>
        ) : !tree || tree.length === 0 ? (
          <p className="py-6 text-center text-xs text-slate-500">
            No categories yet.
            {canManage && " Click 'New' to create one."}
          </p>
        ) : (
          <div className="space-y-0.5">
            {/* "All questions" pseudo-node */}
            <CategoryRow
              label="All questions"
              depth={0}
              isSelected={selectedCategoryId == null}
              onClick={() => onSelectCategory?.(null)}
            />
            {tree.map((node) => (
              <CategoryTreeRow
                key={node.id}
                node={node}
                depth={0}
                canManage={canManage}
                selectedCategoryId={selectedCategoryId}
                onSelect={onSelectCategory}
                onEdit={(c) => setEditTarget(c)}
                onDelete={(c) => setDeleteTarget(c)}
              />
            ))}
          </div>
        )}
      </div>

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
// Collapsible tree row
// ---------------------------------------------------------------------------

function CategoryTreeRow({
  node,
  depth,
  canManage,
  selectedCategoryId,
  onSelect,
  onEdit,
  onDelete,
}: {
  node: CategoryNode;
  depth: number;
  canManage: boolean;
  selectedCategoryId?: number | null;
  onSelect?: (id: number | null) => void;
  onEdit: (c: Category) => void;
  onDelete: (c: Category) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = Boolean(node.subcategories && node.subcategories.length > 0);
  const isSelected = selectedCategoryId === node.id;

  return (
    <>
      <div
        className="group flex items-center justify-between rounded-md py-1.5 pr-1 hover:bg-slate-100"
        style={{ paddingLeft: `${depth * 14 + 4}px` }}
      >
        <div className="flex min-w-0 flex-1 items-center gap-1">
          {/* Expand/collapse chevron — only shown if has children */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (hasChildren) setExpanded((v) => !v);
            }}
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-slate-400 hover:bg-slate-200 hover:text-slate-700 disabled:opacity-0"
            disabled={!hasChildren}
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            {hasChildren ? (
              expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )
            ) : (
              <span className="h-1 w-1 rounded-full bg-slate-300" />
            )}
          </button>
          <button
            type="button"
            onClick={() => onSelect?.(node.id)}
            className={`flex min-w-0 flex-1 items-center gap-1.5 truncate text-left text-sm ${
              isSelected ? "font-medium text-primary-700" : "text-slate-700"
            }`}
          >
            <span className="truncate">{node.name}</span>
            {!node.is_active && <Badge variant="default">Inactive</Badge>}
          </button>
        </div>
        {canManage && (
          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
            <button
              type="button"
              onClick={() => onEdit(node)}
              className="flex h-6 w-6 items-center justify-center rounded text-slate-500 hover:bg-slate-200 hover:text-slate-700"
              aria-label="Edit category"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => onDelete(node)}
              className="flex h-6 w-6 items-center justify-center rounded text-danger hover:bg-danger-50"
              aria-label="Delete category"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>
      {expanded &&
        hasChildren &&
        node.subcategories!.map((child) => (
          <CategoryTreeRow
            key={child.id}
            node={child}
            depth={depth + 1}
            canManage={canManage}
            selectedCategoryId={selectedCategoryId}
            onSelect={onSelect}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Plain (non-collapsible) row — used for the "All questions" pseudo-node
// ---------------------------------------------------------------------------

function CategoryRow({
  label,
  depth,
  isSelected,
  onClick,
}: {
  label: string;
  depth: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <div
      className="flex items-center rounded-md py-1.5 pr-1 hover:bg-slate-100"
      style={{ paddingLeft: `${depth * 14 + 4}px` }}
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center">
        <span className="h-1 w-1 rounded-full bg-slate-300" />
      </span>
      <button
        type="button"
        onClick={onClick}
        className={`flex-1 truncate text-left text-sm ${
          isSelected ? "font-medium text-primary-700" : "text-slate-700"
        }`}
      >
        {label}
      </button>
    </div>
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

  // Reset ALL fields when the target changes (e.g. opening edit on a different row).
  // Using a key based on initial?.id ensures every field — including description —
  // is reset to the new initial values.
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
