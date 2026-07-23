/**
 * E2E: Scenario C — Failure and Recovery
 * Verifies Service Registry and Logs routes are reachable.
 */
import { test, expect } from "@playwright/test";

test.describe("Scenario C — Failure and Recovery (UI smoke)", () => {
  test("Service Registry page is reachable", async ({ page }) => {
    await page.goto("/service-registry");
    await expect(page.getByRole("heading", { name: /service registry/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("Logs page is reachable", async ({ page }) => {
    await page.goto("/logs");
    await expect(page.getByRole("heading", { name: /logs/i })).toBeVisible({
      timeout: 10_000,
    });
  });
});
