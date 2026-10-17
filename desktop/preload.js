const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("cleanai", {
  api: (method, path, body) =>
    ipcRenderer.invoke("api", { method, path, body }),
  selftest: () => ipcRenderer.invoke("selftest"),
  pickOpen: () => ipcRenderer.invoke("pick-open"),
  pickSave: (name, preferCsv) =>
    ipcRenderer.invoke("pick-save", name, preferCsv),
});
