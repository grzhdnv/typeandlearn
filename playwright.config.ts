import { defineConfig, devices } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Never reuse the development server, database, or paid provider credentials.
const testDirectory = mkdtempSync(join(tmpdir(), "typeandlearn-e2e-"));

/**
 * Playwright end-to-end configuration for TypeAndLearn.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:13000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: ".venv/bin/python -m uvicorn apps.backend.main:app --port 18000 --host 127.0.0.1",
      env: {
        DATABASE_URL: `sqlite:///${join(testDirectory, "test.sqlite")}`,
        DEEPSEEK_API_KEY: "",
        GROQ_API_KEY: "",
        OPENROUTER_API_KEY: "",
        AUTH_MODE: "local",
      },
      url: "http://127.0.0.1:18000/docs",
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
    {
      command: "npm --prefix apps/frontend run dev -- --port 13000 --host 127.0.0.1 --strictPort",
      env: { TYPEANDLEARN_API_URL: "http://127.0.0.1:18000" },
      url: "http://127.0.0.1:13000",
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
  ],
});
