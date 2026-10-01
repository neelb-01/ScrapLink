// Starts the API (:8000, with reload) and the web client (:5173) together, and stops both
// on Ctrl+C, on `--stop` from another terminal, or when either exits. Both are spawned
// directly rather than through npm, and stopped as whole process trees, so nothing is left
// listening afterwards.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:http";
import { connect } from "node:net";
import { resolve } from "node:path";

const web = resolve(import.meta.dirname, "..");
const backend = resolve(web, "../backend");
const API_PORT = 8000;
const WEB_PORT = 5173;
// Local-only port that `--stop` uses to ask a running instance to shut down. Killing the
// terminal that started it doesn't always reach this process, so this is the reliable path.
const CONTROL_PORT = 8099;
const windows = process.platform === "win32";

if (process.argv.includes("--stop")) {
  const reply = await fetch(`http://127.0.0.1:${CONTROL_PORT}/stop`, { method: "POST" }).then(
    (r) => r.text(),
    () => null,
  );
  console.log(reply ? "Stopped the API and web servers." : "dev:all is not running.");
  process.exit(0);
}

const uvicorn = ["Scripts/uvicorn.exe", "bin/uvicorn"]
  .map((p) => resolve(backend, ".venv", p))
  .find(existsSync);
if (!uvicorn) fail("backend/.venv not found: create it first (see README)");
const vite = resolve(web, "node_modules/vite/bin/vite.js");
if (!existsSync(vite)) fail("vite not installed: run npm install in web/");

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

for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => stop(0));

if (await ready()) {
  console.log(`\nScrapLink is up: http://localhost:${WEB_PORT}  (API docs http://localhost:${API_PORT}/docs)`);
  console.log("Press Ctrl+C, or run `npm run dev:stop` from another terminal, to stop both.\n");
}

function start(name, command, args, cwd) {
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
    console.error(`[${name}] exited with code ${code}; stopping the other server`);
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
