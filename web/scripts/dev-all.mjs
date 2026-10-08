// Starts the API (:8000, with reload), the web client (:5173) and the ML suggestion service
// (:8001) together, and stops them all on Ctrl+C, on `--stop` from another terminal, or when
// the API or web exits. Each is spawned directly rather than through npm, and stopped as a
// whole process tree, so nothing is left listening afterwards.
//
// The ML service is optional: it is skipped with `--no-ml` or when ml/.venv doesn't exist, an
// already-running one on :8001 is reused, and if it stops the rest carry on. Without it,
// sellers choose the material by hand. It loads the model named by SCRAPLINK_ML_PROBE when set.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:http";
import { connect } from "node:net";
import { resolve } from "node:path";

const web = resolve(import.meta.dirname, "..");
const backend = resolve(web, "../backend");
const ml = resolve(web, "../ml");
const API_PORT = 8000;
const WEB_PORT = 5173;
const ML_PORT = 8001;
// Local-only port that `--stop` uses to ask a running instance to shut down. Killing the
// terminal that started it doesn't always reach this process, so this is the reliable path.
const CONTROL_PORT = 8099;
const windows = process.platform === "win32";

if (process.argv.includes("--stop")) {
  const reply = await fetch(`http://127.0.0.1:${CONTROL_PORT}/stop`, { method: "POST" }).then(
    (r) => r.text(),
    () => null,
  );
  console.log(reply ? "Stopped the dev servers." : "dev:all is not running.");
  process.exit(0);
}

const uvicorn = ["Scripts/uvicorn.exe", "bin/uvicorn"]
  .map((p) => resolve(backend, ".venv", p))
  .find(existsSync);
if (!uvicorn) fail("backend/.venv not found: create it first (see README)");
const vite = resolve(web, "node_modules/vite/bin/vite.js");
if (!existsSync(vite)) fail("vite not installed: run npm install in web/");
const mlUvicorn = ["Scripts/uvicorn.exe", "bin/uvicorn"]
  .map((p) => resolve(ml, ".venv", p))
  .find(existsSync);

for (const port of [API_PORT, WEB_PORT, CONTROL_PORT]) {
  if (await listening(port)) fail(`port ${port} is already in use; stop whatever is running there first`);
}

const children = [];
let stopping = false;

createServer((req, res) => {
  if (req.method !== "POST" || req.url !== "/stop") return res.writeHead(404).end();
  stopping = true;
  killChildren();
  res.end("stopped\n", () => process.exit(0));
}).listen(CONTROL_PORT, "127.0.0.1");

start("api", uvicorn, ["scraplink.app:create_app", "--factory", "--reload", "--port", String(API_PORT)], backend);
start("web", process.execPath, [vite, "--port", String(WEB_PORT), "--strictPort"], web);
const mlStarted = await startMl();

for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => stop(0));

if (await ready()) {
  console.log(`\nScrapLink is up: http://localhost:${WEB_PORT}  (API docs http://localhost:${API_PORT}/docs)`);
  console.log("Press Ctrl+C, or run `npm run dev:stop` from another terminal, to stop them.\n");
  if (mlStarted) void announceMl();
}

async function startMl() {
  if (process.argv.includes("--no-ml")) {
    console.log("[ml] skipped (--no-ml): sellers choose the material by hand");
    return false;
  }
  if (!mlUvicorn) {
    console.log("[ml] ml/.venv not found, so no material suggestions (see ml/README.md to set it up)");
    return false;
  }
  if (await listening(ML_PORT)) {
    console.log(`[ml] something is already listening on ${ML_PORT}; using it as the ML service`);
    return false;
  }
  const probe = process.env.SCRAPLINK_ML_PROBE;
  console.log(`[ml] starting on ${ML_PORT} with ${probe ? `the trained model ${probe}` : "zero-shot CLIP"}`);
  start("ml", mlUvicorn, ["scraplink_ml.app:create_app", "--factory", "--port", String(ML_PORT)], ml, {
    optional: true,
  });
  return true;
}

// The model takes a few seconds to load (longer the first time, while it downloads), so the
// API and web don't wait for it; this says when suggestions are available.
async function announceMl() {
  const deadline = Date.now() + 180_000;
  while (Date.now() < deadline && !stopping) {
    const health = await fetch(`http://127.0.0.1:${ML_PORT}/health`).then(
      (r) => (r.ok ? r.json() : null),
      () => null,
    );
    if (health) return console.log(`[ml] ready (${health.model}): lot photos now get material suggestions`);
    await new Promise((done) => setTimeout(done, 1000));
  }
  if (!stopping) console.error("[ml] not ready after 3 minutes; check its output above");
}

function start(name, command, args, cwd, { optional = false } = {}) {
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, FORCE_COLOR: "1" },
    stdio: ["ignore", "pipe", "pipe"],
    // On POSIX a new process group lets stop() signal the whole tree at once.
    detached: !windows,
  });
  children.push(child);
  for (const stream of [child.stdout, child.stderr]) prefix(stream, `[${name}] `);
  child.on("exit", (code) => {
    if (stopping) return;
    if (optional) {
      console.error(`[${name}] exited with code ${code}; carrying on without it`);
      return;
    }
    console.error(`[${name}] exited with code ${code}; stopping the other servers`);
    stop(1);
  });
}

function stop(code) {
  if (stopping) return;
  stopping = true;
  killChildren();
  process.exit(code);
}

function killChildren() {
  for (const child of children) {
    if (child.exitCode !== null || child.pid === undefined) continue;
    if (windows) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    else {
      try {
        process.kill(-child.pid, "SIGTERM");
      } catch {
        // already gone
      }
    }
  }
}

async function ready() {
  const deadline = Date.now() + 60_000;
  const urls = [`http://127.0.0.1:${API_PORT}/health`, `http://localhost:${WEB_PORT}/`];
  while (Date.now() < deadline && !stopping) {
    const ok = await Promise.all(urls.map((url) => fetch(url).then((r) => r.ok, () => false)));
    if (ok.every(Boolean)) return true;
    await new Promise((done) => setTimeout(done, 500));
  }
  if (!stopping) console.error("servers did not become ready within 60 s; check the output above");
  return false;
}

function prefix(stream, label) {
  let pending = "";
  stream.setEncoding("utf8");
  stream.on("data", (chunk) => {
    const lines = (pending + chunk).split(/\r?\n/);
    pending = lines.pop();
    for (const line of lines) process.stdout.write(label + line + "\n");
  });
  stream.on("end", () => pending && process.stdout.write(label + pending + "\n"));
}

function listening(port) {
  return new Promise((done) => {
    const socket = connect({ port, host: "127.0.0.1" });
    socket.once("connect", () => (socket.destroy(), done(true)));
    socket.once("error", () => done(false));
  });
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
