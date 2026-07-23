import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright e2e config.
 * Tests run against a pre-built Next.js export (no live backend).
 * For demo scenarios (A/B/C) with a live backend use:
 *   webServer: { command: "npm run dev", url: "http://localhost:3000" }
 *
 * Owning docs: 16-testing.md §11, 18-demo.md
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Start Next.js dev server before tests when running e2e suite
  // (optional — skip if server is already running)
  // webServer: {
  //   command: "npm run dev",
  //   url: "http://localhost:3000",
  //   reuseExistingServer: true,
  // },
});
