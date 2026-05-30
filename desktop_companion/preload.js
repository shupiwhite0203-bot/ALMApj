const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  setMode: (mode) => ipcRenderer.send("set-mode", mode),
  setIgnoreMouseEvent: (ignore) => ipcRenderer.send("set-ignore-mouse-event", Boolean(ignore)),
  updateComponentHover: (componentId, hovering) =>
    ipcRenderer.send("update-component-hover", componentId, Boolean(hovering)),
  updateConfigFiles: () => {},
  onToggleInputSubtitle: (callback) => {
    const wrapped = () => callback();
    ipcRenderer.on("toggle-input-subtitle", wrapped);
    return () => ipcRenderer.removeListener("toggle-input-subtitle", wrapped);
  },
  toggleForceIgnoreMouse: () => ipcRenderer.send("toggle-force-ignore-mouse"),
  showContextMenu: () => ipcRenderer.send("show-context-menu"),
});

contextBridge.exposeInMainWorld("electron", {
  process: {
    platform: process.platform,
  },
  ipcRenderer: {
    send: (channel, ...args) => ipcRenderer.send(channel, ...args),
    on: (channel, listener) => {
      const wrapped = (_event, ...args) => listener(_event, ...args);
      ipcRenderer.on(channel, wrapped);
      return wrapped;
    },
    removeListener: (channel, listener) => ipcRenderer.removeListener(channel, listener),
    removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  },
});
