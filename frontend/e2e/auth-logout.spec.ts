import { expect, test, apiLoginAndVisit } from "./fixtures";

test.describe("Auth: logout", () => {
  test("logs the user out and redirects to /login", async ({ page }) => {
    test.use({ skipIfNoBackend: undefined });
    // Sign in via the API to avoid coupling this test to the login UI flow.
    await apiLoginAndVisit(page, "/dashboard");

    // Open the user dropdown.
    await page.getByRole("button", { name: /open user menu/i }).click();

    // Click the "Logout" item.
    await page.getByRole("menuitem", { name: /logout/i }).click();

    // Expect to be redirected to /login.
    await page.waitForURL(/\/login/, { timeout: 10_000 });
    expect(page.url()).toContain("/login");

    // And the auth state should be cleared.
    const stored = await page.evaluate(() => localStorage.getItem("cj_auth_v1"));
    expect(stored).toBeNull();
  });
});
