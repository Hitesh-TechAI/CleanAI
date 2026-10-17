const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn, execSync } = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const net = require("net");
const os = require("os");
const path = require("path");

let backend = null,
  port = 0,
  token = "",
  stderrBuf = "";

function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => resolve(p));
    });
    s.on("error", reject);
  });
}

function backendPath() {
  const exe =
    process.platform === "win32" ? "cleanai-backend.exe" : "cleanai-backend";
  return app.isPackaged
    ? path.join(process.resourcesPath, "backend", exe)
    : path.join(__dirname, "..", "backend", "dist", "cleanai-backend", exe);
}

async function call(method, p, body) {
  const res = await fetch(`http://127.0.0.1:${port}${p}`, {
    method,
    headers: { "Content-Type": "application/json", "X-CleanAI-Token": token },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {}
  return { status: res.status, data };
}

async function startBackend() {
  port = await freePort();
  token = crypto.randomBytes(24).toString("hex");
  const exe = backendPath();
  if (!fs.existsSync(exe)) throw new Error(`Backend not found: ${exe}`);
  let exited = null;
  backend = spawn(
    exe,
    ["--port", String(port), "--parent-pid", String(process.pid)],
    {
      env: { ...process.env, CLEANAI_TOKEN: token },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    }
  );
  backend.stdout.on("data", () => {});
  backend.stderr.on("data", (d) => {
    stderrBuf = (stderrBuf + d).slice(-2000);
  });
  backend.on("exit", (code) => {
    exited = code;
  });

  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (exited !== null)
      throw new Error(`Backend exited (code ${exited}).\n${stderrBuf}`);
    try {
      const r = await call("GET", "/health");
      if (r.status === 200) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`Backend did not start within 30 s.\n${stderrBuf}`);
}

function stopBackend() {
  if (!backend) return;
  const pid = backend.pid;
  backend = null;
  try {
    if (process.platform === "win32")
      execSync(`taskkill /pid ${pid} /T /F`, { stdio: "ignore" });
    else process.kill(pid);
  } catch {}
}

async function selftest() {
  const log = [];
  const step = (name, ok, extra = "") => {
    log.push(`${ok ? "PASS" : "FAIL"}  ${name} ${extra}`);
    if (!ok) throw new Error(name);
  };
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cleanai-"));
  const csv = path.join(dir, "in.csv");
  const out = path.join(dir, "out.xlsx");
  fs.writeFileSync(csv, "name,age\nAnn,10\nBob,20\nBob,20\nCy,\n");
  let sid = null;
  try {
    let r = await call("POST", "/load", { path: csv });
    step(
      "load csv",
      r.status === 200 && r.data.state.rows === 4,
      `rows=${r.data?.state?.rows}`
    );
    sid = r.data.session_id;
    r = await call("GET", `/sessions/${sid}/profile`);
    step(
      "profile",
      r.status === 200 && r.data.null_cells === 1 && r.data.duplicate_rows === 1
    );
    r = await call("POST", `/sessions/${sid}/apply`, {
      op: { op: "drop_duplicates" },
    });
    step(
      "apply drop_duplicates",
      r.status === 200 && r.data.result.rows_after === 3
    );
    r = await call("POST", `/sessions/${sid}/undo`);
    step("undo", r.status === 200 && r.data.rows === 4);
    r = await call("POST", `/sessions/${sid}/redo`);
    step("redo", r.status === 200 && r.data.rows === 3);
    r = await call("POST", `/sessions/${sid}/export`, { path: out });
    step(
      "export xlsx",
      r.status === 200 && fs.existsSync(out) && fs.statSync(out).size > 0
    );
    log.push("ALL PASSED");
  } catch (e) {
    log.push(`STOPPED: ${e.message}`);
  } finally {
    if (sid) {
      try {
        await call("DELETE", `/sessions/${sid}`);
      } catch {}
    }
    fs.rmSync(dir, { recursive: true, force: true });
  }
  return log.join("\n");
}

ipcMain.handle("api", async (_e, { method, path: p, body }) => {
  if (typeof p !== "string" || !p.startsWith("/")) throw new Error("Bad path");
  return call(method, p, body);
});
ipcMain.handle("selftest", selftest);

ipcMain.handle("pick-open", async () => {
  const r = await dialog.showOpenDialog({
    properties: ["openFile"],
    filters: [
      { name: "Data files", extensions: ["csv", "tsv", "txt", "xlsx", "xlsm"] },
    ],
  });
  return r.canceled ? null : r.filePaths[0];
});

ipcMain.handle("pick-save", async (_e, name, preferCsv) => {
  const f = [
    { name: "Excel", extensions: ["xlsx"] },
    { name: "CSV", extensions: ["csv"] },
  ];
  const r = await dialog.showSaveDialog({
    defaultPath: String(name || "cleaned"),
    filters: preferCsv ? f.reverse() : f,
  });
  return r.canceled ? null : r.filePath;
});

app.whenReady().then(async () => {
  try {
    await startBackend();
  } catch (e) {
    dialog.showErrorBox("CleanAI failed to start", String(e.message || e));
    stopBackend();
    app.quit();
    return;
  }
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadFile("index.html");
});

app.on("window-all-closed", () => app.quit());
app.on("before-quit", stopBackend);
process.on("exit", stopBackend);
