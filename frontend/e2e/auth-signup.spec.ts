import { expect, test } from "./fixtures";

test.describe("Auth: signup", () => {
  test("shows a success message after signup", async ({ page }) => {
    test.use({ skipIfNoBackend: undefined });
    await page.goto("/signup");

    const unique = `e2e_signup_${Date.now()}@example.com`;
    await page.getByLabel(/full name/i).fill("E2E Signup");
    await page.getByLabel(/^email$/i).fill(unique);
    await page.getByLabelText(/^password$/i).fill("TestPass123!");
    await page.getByLabelText(/confirm password/i).fill("TestPass123!");
    await page.getByRole("button", { name: /create account/i }).click();

    // Expect to see the "check your email" success screen.
    await expect(page.getByRole("heading", { name: /check your email/i })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(unique)).toBeVisible();
  });
});
