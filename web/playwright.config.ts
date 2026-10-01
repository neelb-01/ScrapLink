import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const backend = resolve(import.meta.dirname, "../backend");
const python =
  ["Scripts/python.exe", "bin/python"].map((p) => join(backend, ".venv", p)).find(existsSync) ??
  "python";

export const API = "http://localhost:8010";
const WEB = "http://localhost:5174";

export default defineConfig({
  testDir: "e2e",
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    ...devices["Pixel 7"],
    // The installed Chrome, so no browser download is needed.
    channel: "chrome",
    baseURL: WEB,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${python}" scripts/e2e_server.py --port 8010 --web-origin ${WEB} --data "${join(tmpdir(), "scraplink-e2e")}"`,
      cwd: backend,
      url: `${API}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npx vite --port 5174 --strictPort",
      env: { SCRAPLINK_API: API },
      url: WEB,
      reuseExistingServer: false,
    },
  ],
});
