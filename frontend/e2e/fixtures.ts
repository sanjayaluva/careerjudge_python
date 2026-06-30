import { test as base, expect, type Page } from "@playwright/test";

/**
 * Skips the test if the backend at http://localhost:8000 is not reachable.
 * Used to keep E2E tests passing in environments where only the frontend
 * dev server is running.
 */
async function backendReachable(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 1500);
    const res = await fetch("http://localhost:8000/api/auth/signup", {
      method: "OPTIONS",
      signal: controller.signal,
    });
    clearTimeout(t);
    return res.ok || res.status === 405 || res.status === 401 || res.status === 400;
  } catch {
    return false;
  }
}

export const test = base.extend<{ skipIfNoBackend: void }>({
  skipIfNoBackend: async (_, use) => {
    const ok = await backendReachable();
    if (!ok) {
      test.skip(true, "Backend at http://localhost:8000 is not reachable — skipping E2E test.");
    }
    await use();
  },
});

export { expect };

/** A test account used by the signup/logout flows. The backend is expected to
 * already have this account (created via the demo seed command). If not, the
 * login E2E will fail — that's intentional. */
export const TEST_EMAIL = "e2e@example.com";
export const TEST_PASSWORD = "TestPass123!";

/** Sign in via the API directly, then navigate to the dashboard. */
export async function apiLoginAndVisit(page: Page, path = "/dashboard") {
  const res = await page.request.post("http://localhost:8000/api/auth/login", {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  const { access, refresh, user } = body.data;
  await page.addInitScript(
    ([access, refresh, user]) => {
      localStorage.setItem(
        "cj_auth_v1",
        JSON.stringify({ accessToken: access, refreshToken: refresh, user }),
      );
    },
    [access, refresh, user],
  );
  await page.goto(path);
}
