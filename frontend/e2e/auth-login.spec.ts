import { expect, test } from "./fixtures";

test.describe("Auth: login", () => {
  test("redirects to /dashboard on valid credentials", async ({ page }, testInfo) => {
    test.use({ skipIfNoBackend: undefined });
    // skipIfNoBackend fixture will skip if backend is unreachable.
    await page.goto("/login");

    // Fill the form.
    await page.getByLabel(/email/i).fill("e2e@example.com");
    await page.getByLabel(/password/i).fill("TestPass123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Expect to land on the dashboard.
    await page.waitForURL(/\/dashboard/, { timeout: 10_000 });
    expect(page.url()).toContain("/dashboard");

    // The topbar should show the page title.
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
    void testInfo;
  });

  test("shows an error on invalid credentials", async ({ page }) => {
    await page.goto("/login");

    await page.getByLabel(/email/i).fill("nobody@example.com");
    await page.getByLabel(/password/i).fill("WrongPassword123");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should stay on /login and show an error alert.
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("alert")).toBeVisible({ timeout: 10_000 });
  });
});
