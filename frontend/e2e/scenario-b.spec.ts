/**
 * E2E: Scenario B — Autonomous Mitigation
 * Verifies Simulation and Digital Twin routes are reachable.
 */
import { test, expect } from "@playwright/test";

test.describe("Scenario B — Autonomous Mitigation (UI smoke)", () => {
  test("Simulation page is reachable", async ({ page }) => {
    await page.goto("/simulation");
    await expect(page.getByRole("heading", { name: /simulation/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("Digital Twin page is reachable", async ({ page }) => {
    await page.goto("/digital-twin");
    await expect(page.getByRole("heading", { name: /digital twin/i })).toBeVisible({
      timeout: 10_000,
    });
  });
});
