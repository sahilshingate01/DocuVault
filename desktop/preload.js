const { contextBridge, ipcRenderer } = require('electron');

/**
 * Expose secure native bridge to the renderer process
 */
contextBridge.exposeInMainWorld('docuvaultNative', {
  isDesktop: true,
  platform: process.platform,

  // Native File Dialogs & SHA-256 Crypto
  openFileDialog: (options) => ipcRenderer.invoke('dialog:open-file', options),
  computeFileHash: (filePath) => ipcRenderer.invoke('file:compute-hash', filePath),
  saveFileDialog: (options) => ipcRenderer.invoke('dialog:save-file', options),

  // Backend Process Lifecycle
  getBackendStatus: () => ipcRenderer.invoke('backend:get-status'),
  restartBackend: () => ipcRenderer.invoke('backend:restart'),

  // Environment & External Utilities
  getAppInfo: () => ipcRenderer.invoke('app:get-info'),
  openExternal: (url) => ipcRenderer.invoke('shell:open-external', url),

  // Event Listeners from Main Process (Menu items, Status)
  onBackendStatusChanged: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('backend:status-changed', handler);
    return () => ipcRenderer.removeListener('backend:status-changed', handler);
  },

  onMenuAction: (callback) => {
    const handler = (event, action) => callback(action);
    ipcRenderer.on('menu:action', handler);
    return () => ipcRenderer.removeListener('menu:action', handler);
  }
});
