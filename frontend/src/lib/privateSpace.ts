/**
 * Report 9 #39-#47: a Corporate Exclusive Admin authors his organization's
 * PRIVATE question bank, assessments, reports and courses. When he manages
 * more than one exclusive organization, new content goes to the one he picked
 * (see PrivateSpaceNote); otherwise the backend uses his first organization.
 * The backend ignores the choice for every other role.
 */
const STORAGE_KEY = "cj_private_org_v1";

export function getPrivateOrgId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const id = raw ? Number(raw) : NaN;
    return Number.isFinite(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function setPrivateOrgId(id: number | null): void {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, String(id));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // storage unavailable — the backend falls back to the first organization
  }
}

/** Adds the chosen exclusive organization to a create payload, if any. */
export function withPrivateOwner<T extends object>(payload: T): T {
  const id = getPrivateOrgId();
  return id ? { ...payload, owner_organization: id } : payload;
}
