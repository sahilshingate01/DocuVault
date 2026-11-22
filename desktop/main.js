const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow = null;
let backendProcess = null;
const BACKEND_PORT = 8000;
const BACKEND_HOST = '127.0.0.1';
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const PROJECT_ROOT = path.resolve(__dirname, '..');

/**
 * Check if the DocuVault FastAPI backend is already responsive
 */
function checkBackendHealth(timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(`${BACKEND_URL}/health`, { timeout: timeoutMs }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Launch DocuVault FastAPI Backend automatically if not running
 */
async function ensureBackendRunning() {
  const isHealthy = await checkBackendHealth();
  if (isHealthy) {
    console.log('[DocuVault Backend] Server is already running at', BACKEND_URL);
    return { status: 'connected', managed: false, url: BACKEND_URL };
  }

  // Locate python executable
  const venvPython = path.join(PROJECT_ROOT, 'venv', 'bin', 'python3');
  const pythonExec = fs.existsSync(venvPython) ? venvPython : 'python3';

  console.log('[DocuVault Backend] Starting local FastAPI server using:', pythonExec);

  backendProcess = spawn(pythonExec, ['app/main.py'], {
    cwd: PROJECT_ROOT,
    env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend stdout]: ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend stderr]: ${data.toString().trim()}`);
  });

  backendProcess.on('exit', (code, signal) => {
    console.log(`[Backend exit]: code ${code}, signal ${signal}`);
    backendProcess = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend:status-changed', {
        status: 'stopped',
        managed: true,
        code
      });
    }
  });

  // Poll for health until server is ready
  for (let attempt = 1; attempt <= 20; attempt++) {
    await new Promise((r) => setTimeout(r, 600));
    const healthy = await checkBackendHealth();
    if (healthy) {
      console.log('[DocuVault Backend] Server successfully initialized and verified at', BACKEND_URL);
      return { status: 'connected', managed: true, url: BACKEND_URL, pid: backendProcess ? backendProcess.pid : null };
    }
  }

  return { status: 'connecting', managed: true, url: BACKEND_URL, pid: backendProcess ? backendProcess.pid : null };
}

/**
 * Gracefully terminate managed backend process
 */
function terminateBackend() {
  if (backendProcess) {
    console.log('[DocuVault Backend] Terminating managed backend process...');
    try {
      backendProcess.kill('SIGINT');
    } catch (e) {
      try { backendProcess.kill('SIGKILL'); } catch (err) {}
    }
    backendProcess = null;
  }
}

/**
 * Create Native Application Window
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1080,
    minHeight: 700,
    backgroundColor: '#0b0f19',
    title: 'DocuVault - Secure Document Management System',
    icon: path.join(__dirname, 'assets', 'icon.svg'),
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 18, y: 16 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      spellcheck: false
    }
  });

  // Load index.html
  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Build Native Application Menu
  setupAppMenu();
}

/**
 * Setup native menu bar
 */
function setupAppMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }] : []),
    {
      label: 'File',
      submenu: [
        {
          label: 'Upload Document to Vault...',
          accelerator: 'CmdOrCtrl+U',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'upload-document')
        },
        {
          label: 'Create Secure Workspace...',
          accelerator: 'CmdOrCtrl+N',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'create-workspace')
        },
        { type: 'separator' },
        {
          label: 'Local File SHA-256 Verifier...',
          accelerator: 'CmdOrCtrl+O',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'open-local-verifier')
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' }
      ]
    },
    {
      label: 'Vault & Ledger',
      submenu: [
        {
          label: 'Verify Cryptographic Ledger',
          accelerator: 'CmdOrCtrl+L',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'verify-ledger')
        },
        {
          label: 'Simulate Ledger Tamper Check',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'simulate-tamper')
        },
        {
          label: 'Restore Chain Integrity',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'restore-ledger')
        },
        { type: 'separator' },
        {
          label: 'Refresh Vault Cache',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'refresh-vault')
        }
      ]
    },
    {
      label: 'Security & Access',
      submenu: [
        {
          label: 'ABAC Policy Simulator',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'open-abac')
        },
        {
          label: 'Security SOC Alerts',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'open-soc')
        },
        { type: 'separator' },
        {
          label: 'Switch to SP Vikram Sharma (Police)',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'persona-sp')
        },
        {
          label: 'Switch to Judge Sneha Kulkarni (Judiciary)',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'persona-judge')
        },
        {
          label: 'Switch to CEO Siddharth (Enterprise)',
          click: () => mainWindow && mainWindow.webContents.send('menu:action', 'persona-ceo')
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Interactive API Docs (Swagger)',
          click: () => shell.openExternal(`${BACKEND_URL}/docs`)
        },
        {
          label: 'DigiLocker Specifications',
          click: () => shell.openExternal('https://www.digilocker.gov.in')
        },
        { type: 'separator' },
        {
          label: 'About DocuVault Desktop',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About DocuVault Desktop',
              message: 'DocuVault Secure Document Management System',
              detail: 'Version 1.0.0\nDigiLocker-grade document governance with SHA-256 fingerprinting, RSA-PSS signatures, and tamper-evident hash-chained audit ledgers.'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// -----------------------------------------------------------------------------
// IPC Handlers: Native File System & Crypto
// -----------------------------------------------------------------------------

/**
 * Open native file picker for vault upload
 */
ipcMain.handle('dialog:open-file', async (event, options = {}) => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: options.title || 'Select Document to Upload to DocuVault',
    properties: ['openFile'],
    filters: options.filters || [
      { name: 'All Documents', extensions: ['pdf', 'docx', 'doc', 'txt', 'csv', 'json', 'jpg', 'png', 'zip'] },
      { name: 'PDF Documents', extensions: ['pdf'] },
      { name: 'Images', extensions: ['jpg', 'jpeg', 'png'] },
      { name: 'Text / Code', extensions: ['txt', 'csv', 'json', 'md'] }
    ]
  });

  if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
    return null;
  }

  const filePath = result.filePaths[0];
  const stats = fs.statSync(filePath);
  const fileName = path.basename(filePath);

  // Compute SHA-256 fingerprint streaming
  const hash = crypto.createHash('sha256');
  const buffer = fs.readFileSync(filePath);
  hash.update(buffer);
  const sha256 = hash.digest('hex');

  return {
    filePath,
    fileName,
    fileSize: stats.size,
    sha256,
    base64: buffer.toString('base64')
  };
});

/**
 * Native file picker for computing SHA-256 integrity verifier
 */
ipcMain.handle('file:compute-hash', async (event, customFilePath) => {
  let targetPath = customFilePath;
  if (!targetPath) {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: 'Select File to Verify Integrity',
      properties: ['openFile']
    });
    if (result.canceled || !result.filePaths.length) return null;
    targetPath = result.filePaths[0];
  }

  if (!fs.existsSync(targetPath)) {
    throw new Error(`File does not exist: ${targetPath}`);
  }

  const stats = fs.statSync(targetPath);
  const fileName = path.basename(targetPath);
  const hash = crypto.createHash('sha256');
  const buffer = fs.readFileSync(targetPath);
  hash.update(buffer);
  const sha256 = hash.digest('hex');

  return {
    filePath: targetPath,
    fileName,
    fileSize: stats.size,
    sha256,
    modifiedAt: stats.mtime.toISOString()
  };
});

/**
 * Save file dialog for exports (Certificates, Audit logs, Documents)
 */
ipcMain.handle('dialog:save-file', async (event, { defaultName, content, isBase64 }) => {
  if (!mainWindow) return null;
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: defaultName || 'docuvault-export.json',
    filters: [
      { name: 'JSON / Documents', extensions: ['json', 'txt', 'pdf', 'csv'] }
    ]
  });

  if (result.canceled || !result.filePath) return null;

  if (isBase64) {
    fs.writeFileSync(result.filePath, Buffer.from(content, 'base64'));
  } else {
    fs.writeFileSync(result.filePath, content, 'utf8');
  }

  return { success: true, filePath: result.filePath };
});

/**
 * Backend health check & process manager IPC
 */
ipcMain.handle('backend:get-status', async () => {
  const healthy = await checkBackendHealth();
  return {
    healthy,
    url: BACKEND_URL,
    managed: !!backendProcess,
    pid: backendProcess ? backendProcess.pid : null
  };
});

ipcMain.handle('backend:restart', async () => {
  terminateBackend();
  return await ensureBackendRunning();
});

ipcMain.handle('app:get-info', () => {
  return {
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    backendUrl: BACKEND_URL,
    electronVersion: process.versions.electron,
    nodeVersion: process.versions.node
  };
});

ipcMain.handle('shell:open-external', (event, url) => {
  shell.openExternal(url);
});

// App Lifecycle
app.whenReady().then(async () => {
  createWindow();
  await ensureBackendRunning();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  terminateBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  terminateBackend();
});
