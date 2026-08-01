const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");

const AUTH_TOKEN_PATH = path.join(__dirname, "..", "..", "data", ".auth_token");

app.commandLine.appendSwitch("no-sandbox");

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    transparent: false,
    backgroundColor: "#14161C",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  const isDev = process.argv.includes("--dev");
  if (isDev) {
    win.loadURL("http://localhost:9080");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  win.on("closed", () => { win = null; });
}

ipcMain.handle("auth:getToken", () => {
  try {
    return fs.readFileSync(AUTH_TOKEN_PATH, "utf-8").trim();
  } catch {
    return null;
  }
});

ipcMain.on("window:minimize", () => win?.minimize());
ipcMain.on("window:maximize", () => {
  if (win?.isMaximized()) win.unmaximize();
  else win?.maximize();
});
ipcMain.on("window:close", () => win?.close());

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
