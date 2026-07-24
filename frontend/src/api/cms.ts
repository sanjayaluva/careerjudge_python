/**
 * CMS API client.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/cms";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Page {
  id: number;
  title: string;
  slug: string;
  body: string;
  meta_description: string;
  status: "draft" | "published" | "archived";
  order: number;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageListItem {
  id: number;
  title: string;
  slug: string;
  status: string;
  order: number;
  updated_at: string;
}

export interface Banner {
  id: number;
  title: string;
  subtitle: string;
  body: string;
  image: string;
  link_url: string;
  link_text: string;
  position: "hero" | "sidebar" | "footer" | "inline";
  is_active: boolean;
  order: number;
  starts_at: string | null;
  ends_at: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface MenuItem {
  id: number;
  label: string;
  url: string;
  location: "header" | "footer" | "sidebar";
  order: number;
  is_active: boolean;
  opens_new_tab: boolean;
  parent: number | null;
}

// ---------------------------------------------------------------------------
// Page API
// ---------------------------------------------------------------------------

export function listPages(params?: { search?: string; status?: string }): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: PageListItem[];
}> {
  return apiGetPaged<PageListItem>(`${BASE}/pages/`, {
    params: {
      page: 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.status ? { status: params.status } : {}),
    },
  });
}

export function retrievePage(id: number): Promise<Page> {
  return apiGet<Page>(`${BASE}/pages/${id}/`);
}

export function retrievePageBySlug(slug: string): Promise<Page> {
  return apiGet<Page>(`${BASE}/pages/slug/${slug}/`);
}

export function createPage(payload: {
  title: string;
  slug: string;
  body: string;
  meta_description?: string;
  status?: string;
}): Promise<Page> {
  return apiPost<Page>(`${BASE}/pages/`, payload);
}

export function updatePage(id: number, payload: Record<string, unknown>): Promise<Page> {
  return apiPatch<Page>(`${BASE}/pages/${id}/`, payload);
}

export function deletePage(id: number): Promise<void> {
  return apiDelete(`${BASE}/pages/${id}/`);
}

// ---------------------------------------------------------------------------
// Banner API
// ---------------------------------------------------------------------------

export function listBanners(params?: {
  search?: string;
  active?: boolean;
  position?: string;
}): Promise<{ count: number; next: string | null; previous: string | null; results: Banner[] }> {
  return apiGetPaged<Banner>(`${BASE}/banners/`, {
    params: {
      page: 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.active !== undefined ? { active: String(params.active) } : {}),
      ...(params?.position ? { position: params.position } : {}),
    },
  });
}

export function createBanner(payload: Record<string, unknown>): Promise<Banner> {
  return apiPost<Banner>(`${BASE}/banners/`, payload);
}

export function updateBanner(id: number, payload: Record<string, unknown>): Promise<Banner> {
  return apiPatch<Banner>(`${BASE}/banners/${id}/`, payload);
}

export function deleteBanner(id: number): Promise<void> {
  return apiDelete(`${BASE}/banners/${id}/`);
}

// ---------------------------------------------------------------------------
// Menu API
// ---------------------------------------------------------------------------

export function listMenuItems(params?: { location?: string }): Promise<MenuItem[]> {
  return apiGetPaged<MenuItem>(`${BASE}/menu/`, {
    params: {
      page: 1,
      ...(params?.location ? { location: params.location } : {}),
    },
  }).then((r) => r.results);
}

export function createMenuItem(payload: {
  label: string;
  url: string;
  location?: string;
  order?: number;
}): Promise<MenuItem> {
  return apiPost<MenuItem>(`${BASE}/menu/`, payload);
}

export function deleteMenuItem(id: number): Promise<void> {
  return apiDelete(`${BASE}/menu/${id}/`);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const PAGE_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

export const BANNER_POSITIONS = [
  { value: "hero", label: "Hero (top of homepage)" },
  { value: "sidebar", label: "Sidebar" },
  { value: "footer", label: "Footer" },
  { value: "inline", label: "Inline" },
];
