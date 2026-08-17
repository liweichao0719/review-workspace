import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";


const backendUrl = "http://127.0.0.1:18010";
const frontendUrl = "http://127.0.0.1:15173";
const reviewDatabase = resolve("test-results/e2e-reviews.db");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  outputDir: "test-results",
  reporter: [["line"]],
  use: {
    baseURL: frontendUrl,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      name: "backend",
      command: "python3 -m tests.e2e_server",
      cwd: "../backend",
      env: { REVIEW_E2E_DATABASE: reviewDatabase },
      url: `${backendUrl}/api/health`,
      timeout: 30_000,
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGTERM", timeout: 2_000 },
    },
    {
      name: "frontend",
      command: "npm run dev -- --host 127.0.0.1 --port 15173",
      env: { REVIEW_API_PROXY: backendUrl },
      url: frontendUrl,
      timeout: 30_000,
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGTERM", timeout: 2_000 },
    },
  ],
});
