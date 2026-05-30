const { app, BrowserWindow, Menu, ipcMain, screen } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_URL = "http://127.0.0.1:18080/?mode=pet";
const LOG_PATH = path.join(process.cwd(), "runs", "desktop_companion.log");

let mainWindow = null;
let currentMode = "pet";
let forceIgnoreMouse = false;
const componentHover = new Map();

function log(message) {
  try {
    fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
    fs.appendFileSync(LOG_PATH, `[${new Date().toISOString()}] ${message}\n`, "utf8");
  } catch {
    // Logging should never prevent the companion from starting.
  }
}

function targetUrl() {
  const arg = process.argv.find((item) => item.startsWith("--url="));
  return arg ? arg.slice("--url=".length) : process.env.ALMA_COMPANION_URL || DEFAULT_URL;
}

function targetDisplay() {
  const displays = screen.getAllDisplays();
  const arg = process.argv.find((item) => item.startsWith("--display="));
  const rawDisplay = arg ? arg.slice("--display=".length) : process.env.ALMA_COMPANION_DISPLAY;
  const requested = Number.parseInt(rawDisplay || "1", 10);
  const index = Number.isFinite(requested) ? Math.max(0, requested - 1) : 0;
  const display = displays[index] || screen.getPrimaryDisplay();
  log(
    `targetDisplay requested=${rawDisplay || "1"} selected=${index + 1}/${displays.length} bounds=${JSON.stringify(display.bounds)}`
  );
  return display;
}

function createWindow() {
  log(`createWindow url=${targetUrl()}`);
  const display = targetDisplay();
  const { x, y, width, height } = display.bounds;

  mainWindow = new BrowserWindow({
    width,
    height,
    x,
    y,
    frame: false,
    transparent: true,
    hasShadow: false,
    resizable: false,
    movable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.setAlwaysOnTop(true, "screen-saver");
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  mainWindow.loadURL(targetUrl());

  mainWindow.webContents.once("did-finish-load", () => {
    setTimeout(() => setMode("pet"), 1000);
  });
}

function setMode(mode) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  currentMode = mode === "window" ? "window" : "pet";

  mainWindow.webContents.send("pre-mode-changed", currentMode);

  if (currentMode === "pet") {
    mainWindow.setBackgroundColor("#00000000");
    mainWindow.setAlwaysOnTop(true, "screen-saver");
    updateIgnoreMouse();
  } else {
    mainWindow.setAlwaysOnTop(false);
    mainWindow.setIgnoreMouseEvents(false);
  }

  setTimeout(sendModeChanged, 250);
}

function sendModeChanged() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("mode-changed", currentMode);
  }
}

function updateIgnoreMouse() {
  if (!mainWindow || mainWindow.isDestroyed() || currentMode !== "pet") return;
  const hoveringInteractive = Array.from(componentHover.values()).some(Boolean);
  mainWindow.setIgnoreMouseEvents(forceIgnoreMouse || !hoveringInteractive, { forward: true });
}

function showContextMenu() {
  const template = [
    {
      label: forceIgnoreMouse ? "Disable fixed click-through" : "Enable fixed click-through",
      click: () => toggleForceIgnoreMouse(),
    },
    { type: "separator" },
    {
      label: currentMode === "pet" ? "Window mode" : "Pet mode",
      click: () => setMode(currentMode === "pet" ? "window" : "pet"),
    },
    { label: "Reload", click: () => mainWindow?.reload() },
    { type: "separator" },
    { label: "Quit", click: () => app.quit() },
  ];
  Menu.buildFromTemplate(template).popup({ window: mainWindow });
}

function toggleForceIgnoreMouse() {
  forceIgnoreMouse = !forceIgnoreMouse;
  mainWindow?.webContents.send("force-ignore-mouse-changed", forceIgnoreMouse);
  updateIgnoreMouse();
}

app.whenReady().then(() => {
  ipcMain.on("set-mode", (_event, mode) => setMode(mode));
  ipcMain.on("renderer-ready-for-mode-change", (_event, mode) => {
    if (mode) currentMode = mode === "window" ? "window" : "pet";
    sendModeChanged();
  });
  ipcMain.on("mode-change-rendered", () => updateIgnoreMouse());
  ipcMain.on("set-ignore-mouse-event", (_event, ignore) => {
    if (mainWindow && currentMode === "pet") {
      mainWindow.setIgnoreMouseEvents(Boolean(ignore), { forward: true });
    }
  });
  ipcMain.on("update-component-hover", (_event, id, hovering) => {
    componentHover.set(String(id), Boolean(hovering));
    updateIgnoreMouse();
  });
  ipcMain.on("toggle-force-ignore-mouse", () => toggleForceIgnoreMouse());
  ipcMain.on("show-context-menu", () => showContextMenu());
  ipcMain.on("window-minimize", () => mainWindow?.minimize());
  ipcMain.on("window-close", () => app.quit());

  createWindow();
});

app.on("window-all-closed", () => {
  app.quit();
});

