// Regenerates src/api/schema.d.ts from the backend's OpenAPI schema, so a backend change
// that breaks the client fails `npm run typecheck` instead of failing in a browser.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const backend = resolve(import.meta.dirname, "../../backend");
const python = ["Scripts/python.exe", "bin/python"]
  .map((p) => resolve(backend, ".venv", p))
  .find(existsSync);
if (!python) throw new Error("backend/.venv not found: create it first (see README)");

const schema = resolve(import.meta.dirname, "../src/api/openapi.json");
execFileSync(python, ["-m", "scraplink.cli", "openapi", "--out", schema], {
  cwd: backend,
  stdio: "inherit",
});
execFileSync(
  process.execPath,
  [
    resolve(import.meta.dirname, "../node_modules/openapi-typescript/bin/cli.js"),
    schema,
    "-o",
    resolve(import.meta.dirname, "../src/api/schema.d.ts"),
  ],
  { stdio: "inherit" },
);
