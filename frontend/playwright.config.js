import { defineConfig } from "@playwright/test"

// Browser tests. `pnpm test:e2e` starts the app with a fake model and fresh demo data (tests/serve.py),
// then clicks through every role. PYTHON can point at your venv, e.g. PYTHON=../.venv/bin/python
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  workers: 1,                  // the tests share one database and follow each other's steps
  use: { baseURL: "http://127.0.0.1:8765", viewport: { width: 1440, height: 900 }, locale: "fa-IR" },
  webServer: {
    command: `${process.env.PYTHON || "python3"} ../tests/serve.py`,
    url: "http://127.0.0.1:8765",
    timeout: 120_000,
    reuseExistingServer: false,
  },
})
