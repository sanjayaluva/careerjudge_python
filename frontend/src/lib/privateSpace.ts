/**
 * Report 9 #39-#47: a Corporate Exclusive Admin authors his organization's
 * PRIVATE question bank, assessments, reports and courses. When he manages
 * more than one exclusive organization, new content goes to the one he picked
 * (see PrivateSpaceNote); otherwise the backend uses his first organization.
 * The backend ignores the choice for every other role.
 *
 * The choice is remembered for the user who made it: another Corporate
 * Exclusive Admin signing in on the same browser must not send it (the server
 * refuses an organization that is not his, so he could create nothing). It is
 * also cleared on logout, and dropped when it is no longer one of the user's
 * organizations (usePrivateSpace).
 */
const STORAGE_KEY = "cj_private_org_v1";
/** The auth store's localStorage key (read directly to avoid an import cycle). */
const AUTH_STORAGE_KEY = "cj_auth_v1";

function currentUserId(): number | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    const id = raw ? (JSON.parse(raw) as { user?: { id?: unknown } | null }).user?.id : null;
    return typeof id === "number" ? id : null;
  } catch {
    return null;
  }
}

export function getPrivateOrgId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as { userId?: unknown; orgId?: unknown };
    const userId = currentUserId();
    if (userId === null || stored.userId !== userId) return null;
    const id = Number(stored.orgId);
    return Number.isFinite(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function setPrivateOrgId(id: number | null): void {
  try {
    const userId = currentUserId();
    if (id && userId !== null) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ userId, orgId: id }));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // storage unavailable — the backend falls back to the first organization
  }
}

/** Forget the choice (logout). */
export function clearPrivateOrgId(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

/** Adds the chosen exclusive organization to a create payload, if any. */
export function withPrivateOwner<T extends object>(payload: T): T {
  const id = getPrivateOrgId();
  return id ? { ...payload, owner_organization: id } : payload;
}
