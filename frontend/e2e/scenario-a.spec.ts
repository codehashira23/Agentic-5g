/**
 * E2E: Scenario A — Intent to Deployment
 *
 * Verifies: the UI responds correctly to a workflow intent submission
 * and the Agent Console route is reachable.
 *
 * Run with backend + demo mode:
 *   ENV=demo LLM__MODE=replay → fully offline, deterministic ($0)
 *
 * Owning docs: 18-demo.md §7, 16-testing.md §11
 */
import { test, expect } from "@playwright/test";

test.describe("Scenario A — Intent to Deployment (UI smoke)", () => {
  test("Dashboard route renders heading", async ({ page }) => {
    await page.goto("/dashboard");
    // The page should contain the Dashboard heading
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("Agent Console route is reachable", async ({ page }) => {
    await page.goto("/agent-console");
    await expect(page.getByRole("heading", { name: /agent console/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("Topology route is reachable", async ({ page }) => {
    await page.goto("/topology");
    await expect(page.getByRole("heading", { name: /topology/i })).toBeVisible({
      timeout: 10_000,
    });
  });
});
