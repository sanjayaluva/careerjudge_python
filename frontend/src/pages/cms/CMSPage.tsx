/**
 * CMS Page — manage content pages, banners, and menu items.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

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
  BANNER_POSITIONS,
  createBanner,
  createPage,
  deleteBanner,
  deletePage,
  listBanners,
  listPages,
  retrievePage,
  updateBanner,
  updatePage,
  type Banner,
  type PageListItem,
} from "@/api/cms";
import { extractApiError } from "@/api/client";

const CMS_KEY = ["cms"];

export default function CMSPage() {
  return (
    <PageCard>
      <div className="p-6 pb-4">
        <h1 className="text-lg font-bold text-slate-900">Content Management</h1>
        <p className="text-sm text-slate-500">Manage pages, banners, and navigation</p>
      </div>

      <Tabs defaultValue="pages">
        <div className="px-6">
          <TabsList>
            <TabsTrigger value="pages">Pages</TabsTrigger>
            <TabsTrigger value="banners">Banners</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="pages" className="px-6 py-4">
          <PagesTab />
        </TabsContent>
        <TabsContent value="banners" className="px-6 py-4">
          <BannersTab />
        </TabsContent>
      </Tabs>
    </PageCard>
  );
}

// ---------------------------------------------------------------------------
// Pages Tab
// ---------------------------------------------------------------------------

function PagesTab() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<PageListItem | "new" | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: [...CMS_KEY, "pages"],
    queryFn: () => listPages(),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deletePage(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CMS_KEY, "pages"] });
      toast.success("Page deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const pages = data?.results ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setEditing("new")}>+ New page</Button>
      </div>
      {isLoading ? (
        <Spinner />
      ) : pages.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">No pages yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pages.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium text-slate-900">{p.title}</TableCell>
                <TableCell className="text-slate-500">/{p.slug}</TableCell>
                <TableCell>
                  <Badge
                    variant={
                      p.status === "published"
                        ? "success"
                        : p.status === "archived"
                          ? "warning"
                          : "default"
                    }
                  >
                    {p.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-slate-500">
                  {new Date(p.updated_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" onClick={() => setEditing(p)}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-danger-600"
                      onClick={() => deleteMut.mutate(p.id)}
                    >
                      ✕
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {editing && (
        <PageEditor page={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}

function PageEditor({ page, onClose }: { page: PageListItem | null; onClose: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(page?.title ?? "");
  const [slug, setSlug] = useState(page?.slug ?? "");
  const [body, setBody] = useState("");
  const [status, setStatus] = useState("draft");

  const { data: fullPage } = useQuery({
    queryKey: [...CMS_KEY, "pages", page?.id],
    queryFn: () => retrievePage(page!.id),
    enabled: !!page?.id,
  });

  // Sync form when full page loads
  if (fullPage && body === "" && fullPage.body) {
    setTitle(fullPage.title);
    setSlug(fullPage.slug);
    setBody(fullPage.body);
    setStatus(fullPage.status);
  }

  const saveMut = useMutation({
    mutationFn: () => {
      if (page) {
        return updatePage(page.id, { title, slug, body, status });
      }
      return createPage({ title, slug, body, status });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CMS_KEY, "pages"] });
      toast.success(page ? "Page updated." : "Page created.");
      onClose();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Modal open onClose={onClose} title={page ? "Edit Page" : "New Page"} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          saveMut.mutate();
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="p-title" required>
              Title
            </Label>
            <Input id="p-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="p-slug" required>
              Slug (URL)
            </Label>
            <Input
              id="p-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="about"
              required
            />
          </div>
        </div>
        <div>
          <Label htmlFor="p-body" required>
            Body (HTML)
          </Label>
          <textarea
            id="p-body"
            rows={10}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 font-mono text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="<h1>About Us</h1><p>Content here...</p>"
            required
          />
        </div>
        <div>
          <Label htmlFor="p-status">Status</Label>
          <select
            id="p-status"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saveMut.isPending} disabled={!title || !slug || !body}>
            {page ? "Save changes" : "Create page"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Banners Tab
// ---------------------------------------------------------------------------

function BannersTab() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Banner | "new" | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: [...CMS_KEY, "banners"],
    queryFn: () => listBanners(),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteBanner(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CMS_KEY, "banners"] });
      toast.success("Banner deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const toggleMut = useMutation({
    mutationFn: (b: Banner) => updateBanner(b.id, { is_active: !b.is_active }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CMS_KEY, "banners"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const banners = data?.results ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setEditing("new")}>+ New banner</Button>
      </div>
      {isLoading ? (
        <Spinner />
      ) : banners.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">No banners yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Position</TableHead>
              <TableHead>Active</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {banners.map((b) => (
              <TableRow key={b.id}>
                <TableCell className="font-medium text-slate-900">
                  {b.title}
                  {b.subtitle && (
                    <span className="ml-1 text-xs text-slate-400">— {b.subtitle}</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="outline">
                    {BANNER_POSITIONS.find((p) => p.value === b.position)?.label ?? b.position}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant={b.is_active ? "primary" : "outline"}
                    onClick={() => toggleMut.mutate(b)}
                  >
                    {b.is_active ? "Active" : "Inactive"}
                  </Button>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" onClick={() => setEditing(b)}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-danger-600"
                      onClick={() => deleteMut.mutate(b.id)}
                    >
                      ✕
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {editing && (
        <BannerEditor
          banner={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function BannerEditor({ banner, onClose }: { banner: Banner | null; onClose: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(banner?.title ?? "");
  const [subtitle, setSubtitle] = useState(banner?.subtitle ?? "");
  const [body, setBody] = useState(banner?.body ?? "");
  const [image, setImage] = useState(banner?.image ?? "");
  const [linkUrl, setLinkUrl] = useState(banner?.link_url ?? "");
  const [linkText, setLinkText] = useState(banner?.link_text ?? "Learn more");
  const [position, setPosition] = useState<Banner["position"]>(banner?.position ?? "hero");
  const [isActive, setIsActive] = useState(banner?.is_active ?? true);

  const saveMut = useMutation({
    mutationFn: () => {
      const payload = {
        title,
        subtitle,
        body,
        image,
        link_url: linkUrl,
        link_text: linkText,
        position,
        is_active: isActive,
      };
      if (banner) {
        return updateBanner(banner.id, payload);
      }
      return createBanner(payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CMS_KEY, "banners"] });
      toast.success(banner ? "Banner updated." : "Banner created.");
      onClose();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Modal open onClose={onClose} title={banner ? "Edit Banner" : "New Banner"} size="md">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          saveMut.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="b-title" required>
            Title
          </Label>
          <Input id="b-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>
        <div>
          <Label htmlFor="b-subtitle">Subtitle</Label>
          <Input id="b-subtitle" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="b-body">Body text</Label>
          <textarea
            id="b-body"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="b-image">Image URL</Label>
          <Input
            id="b-image"
            value={image}
            onChange={(e) => setImage(e.target.value)}
            placeholder="https://... or base64 data URL"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="b-link-url">Link URL</Label>
            <Input id="b-link-url" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="b-link-text">Link text</Label>
            <Input
              id="b-link-text"
              value={linkText}
              onChange={(e) => setLinkText(e.target.value)}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="b-position">Position</Label>
            <select
              id="b-position"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={position}
              onChange={(e) => setPosition(e.target.value as Banner["position"])}
            >
              {BANNER_POSITIONS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4"
              />
              Active
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saveMut.isPending} disabled={!title}>
            {banner ? "Save changes" : "Create banner"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
