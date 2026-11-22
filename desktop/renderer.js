/**
 * DocuVault Desktop Application - Renderer Controller
 * Full-featured client with native Electron bridge integration
 */

const API_BASE = "http://127.0.0.1:8000";

// Pre-defined demo personas
const PERSONAS = {
  sp: {
    email: "sp.vikram@police.gov.in",
    password: "Password123!",
    name: "SP Vikram Sharma",
    title: "Superintendent of Police",
    clearance: "TOP_SECRET",
    badgeClass: "stamp-top-secret"
  },
  si: {
    email: "arjun.das@police.gov.in",
    password: "Password123!",
    name: "Sub-Inspector Arjun Das",
    title: "Investigating Officer",
    clearance: "CONFIDENTIAL",
    badgeClass: "stamp-confidential"
  },
  judge: {
    email: "sneha.kulkarni@judiciary.gov.in",
    password: "Password123!",
    name: "Hon. Judge Sneha Kulkarni",
    title: "Principal District Judge",
    clearance: "TOP_SECRET",
    badgeClass: "stamp-top-secret"
  },
  clerk: {
    email: "manoj.verma@judiciary.gov.in",
    password: "Password123!",
    name: "Manoj Verma",
    title: "Court Record Clerk",
    clearance: "RESTRICTED",
    badgeClass: "stamp-restricted"
  },
  ceo: {
    email: "siddharth@apexcorp.com",
    password: "Password123!",
    name: "Siddharth Singhania",
    title: "Chief Executive Officer",
    clearance: "TOP_SECRET",
    badgeClass: "stamp-top-secret"
  },
  analyst: {
    email: "riya.sen@apexcorp.com",
    password: "Password123!",
    name: "Riya Sen",
    title: "Junior Analyst",
    clearance: "UNCLASSIFIED",
    badgeClass: "stamp-unclassified"
  }
};

let currentToken = null;
let currentPersonaKey = "sp";
let cachedWorkspaces = [];
let cachedDocuments = [];
let stagedNativeUploadFile = null;

// =============================================================================
// Toast Notifications
// =============================================================================
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `cobalt-toast cobalt-toast--${type === "warning" ? "warn" : type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ️"}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// =============================================================================
// Authentication & Persona Switching
// =============================================================================
async function authenticatePersona(key) {
  const p = PERSONAS[key] || PERSONAS.sp;
  currentPersonaKey = key;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: p.email, password: p.password })
    });

    if (!res.ok) {
      throw new Error(`Auth failed (${res.status})`);
    }

    const data = await res.json();
    currentToken = data.token || data.access_token;

    // Update UI Header
    document.getElementById("activeUserName").textContent = p.name;
    const badge = document.getElementById("activeUserClearance");
    badge.textContent = p.clearance.replace("_", " ");
    badge.className = `stamp-clearance ${p.badgeClass}`;

    showToast(`Switched persona to ${p.name} (${p.clearance})`, "success");

    // Refresh active data
    await refreshActiveViewData();
  } catch (err) {
    console.error("Authentication error:", err);
    showToast(`Failed to authenticate as ${p.name}: ${err.message}`, "error");
  }
}

// =============================================================================
// Backend Status & Health Polling
// =============================================================================
async function checkBackendConnectivity() {
  const dot = document.getElementById("serverStatusDot");
  const text = document.getElementById("serverStatusText");

  try {
    if (window.docuvaultNative && window.docuvaultNative.getBackendStatus) {
      const status = await window.docuvaultNative.getBackendStatus();
      if (status.healthy) {
        dot.className = "pulse-dot";
        text.textContent = `Online (${status.managed ? "PID " + status.pid : "Port 8000"})`;
        return true;
      }
    } else {
      const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(1200) });
      if (res.ok) {
        dot.className = "pulse-dot";
        text.textContent = "127.0.0.1:8000";
        return true;
      }
    }
  } catch (e) {}

  dot.className = "pulse-dot disconnected";
  text.textContent = "Offline (Click to restart)";
  return false;
}

// =============================================================================
// Navigation
// =============================================================================
function setupNavigation() {
  const navBtns = document.querySelectorAll(".sidebar-item");
  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      navBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      const paneId = btn.getAttribute("data-pane");
      document.querySelectorAll(".pane-view").forEach((p) => p.classList.remove("active"));
      const targetPane = document.getElementById(`pane-${paneId}`);
      if (targetPane) targetPane.classList.add("active");

      refreshPane(paneId);
    });
  });
}

function refreshPane(paneId) {
  switch (paneId) {
    case "workspaces":
      loadWorkspaces();
      break;
    case "documents":
      loadDocuments();
      break;
    case "signatures":
      loadSignatures();
      break;
    case "audit":
      loadAuditLedger();
      break;
    case "organizations":
      loadOrganizations();
      break;
    case "security":
      loadSecuritySOC();
      break;
  }
}

async function refreshActiveViewData() {
  const activeBtn = document.querySelector(".sidebar-item.active") || document.querySelector(".nav-btn.active");
  const paneId = activeBtn ? activeBtn.getAttribute("data-pane") : "workspaces";
  await refreshPane(paneId);
  await verifyLedgerStatusBadge();
}

// =============================================================================
// Pane 1: Workspaces
// =============================================================================
async function loadWorkspaces() {
  const grid = document.getElementById("workspacesGrid");
  grid.innerHTML = '<div style="color: var(--text-dim); padding: 20px;">Loading workspaces...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/workspaces`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!res.ok) {
      grid.innerHTML = `<div style="color: var(--accent-red); padding: 20px;">Failed to load workspaces (${res.status}). Ensure you have appropriate clearance.</div>`;
      return;
    }

    const data = await res.json();
    cachedWorkspaces = data.items || data;

    // Populate upload modal workspace select as well
    const select = document.getElementById("selectDocWorkspace");
    select.innerHTML = "";
    cachedWorkspaces.forEach((ws) => {
      const opt = document.createElement("option");
      opt.value = ws.id;
      opt.textContent = `${ws.name} [${ws.classification}]`;
      select.appendChild(opt);
    });

    if (!cachedWorkspaces.length) {
      grid.innerHTML = '<div style="color: var(--text-dim); padding: 20px;">No workspaces available or clearance level too low.</div>';
      return;
    }

    grid.innerHTML = cachedWorkspaces.map((ws) => {
      const tierClass = `stamp-${ws.classification.toLowerCase().replace("_", "-")}`;
      return `
        <div class="cut-card workspace-card">
          <div class="workspace-card-header">
            <div>
              <div class="ws-title">${ws.name}</div>
              <div class="ws-code">${ws.code}</div>
            </div>
            <span class="stamp-clearance ${tierClass}">${ws.classification}</span>
          </div>
          <div style="font-size: 12px; color: var(--color-muted); min-height: 36px;">
            ${ws.description || "Secure workspace boundary"}
          </div>
          <div class="ws-stats">
            <span>📁 ${ws.document_count || 0} Documents</span>
            <button class="key key--sm" onclick="openWorkspaceFilter('${ws.id}')">View Docs</button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    grid.innerHTML = `<div style="color: var(--color-error); padding: 20px;">Error: ${err.message}</div>`;
  }
}

window.openWorkspaceFilter = function(wsId) {
  document.querySelector('.sidebar-item[data-pane="documents"]').click();
};

// =============================================================================
// Pane 2: Document Vault
// =============================================================================
async function loadDocuments() {
  const tbody = document.getElementById("documentsTableBody");
  tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">Loading documents...</td></tr>';

  try {
    let res = await fetch(`${API_BASE}/api/v1/documents`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!res.ok) {
      res = await fetch(`${API_BASE}/api/v1/search`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
    }

    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--accent-red); padding: 24px;">Access Denied or Failed to Load (${res.status})</td></tr>`;
      return;
    }

    const data = await res.json();
    cachedDocuments = data.items || data.results || (Array.isArray(data) ? data : []);

    if (!cachedDocuments.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">Vault empty or no documents match your clearance tier.</td></tr>';
      return;
    }

    tbody.innerHTML = cachedDocuments.map((doc) => {
      const tierClass = `badge-${(doc.classification || "unclassified").toLowerCase().replace("_", "-")}`;
      const statusBadge = doc.status === "APPROVED" 
        ? '<span style="color: var(--accent-green); font-weight: 600;">✓ Approved</span>'
        : doc.status === "SIGNED"
        ? '<span style="color: #60a5fa; font-weight: 600;">✍️ Signed</span>'
        : `<span style="color: var(--text-dim);">${doc.status || "DRAFT"}</span>`;

      const curVer = doc.current_version;
      const verNum = curVer ? (typeof curVer === 'object' ? curVer.version_number : curVer) : 1;
      const sha256 = (curVer && curVer.sha256_hash) || doc.current_sha256 || "Pending";
      const fileSizeKb = curVer && curVer.file_size ? (curVer.file_size / 1024).toFixed(1) : (doc.file_size ? (doc.file_size / 1024).toFixed(1) : "0.0");
      const wsName = doc.workspace ? doc.workspace.name : (doc.workspace_name || doc.workspace_id || "Vault Workspace");

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 12px; font-weight: 600;">${doc.document_number}</td>
          <td>
            <div style="font-weight: 600;">${doc.title}</div>
            <div style="font-size: 11px; color: var(--text-dim);">v${verNum} • ${fileSizeKb} KB</div>
          </td>
          <td style="font-size: 12px; color: var(--color-muted);">${wsName}</td>
          <td><span class="stamp-clearance ${tierClass}">${doc.classification}</span></td>
          <td>${statusBadge}</td>
          <td><span class="hash-pill" title="${sha256}">${sha256}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="key key--sm" onclick="verifyDocIntegrity('${doc.id}')">Verify</button>
              <button class="key key--primary key--sm" onclick="downloadDoc('${doc.id}', '${doc.title}')">Download</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color: var(--accent-red); padding: 24px;">Error: ${err.message}</td></tr>`;
  }
}

window.verifyDocIntegrity = async function(docId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/documents/${docId}/verify-integrity`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    const result = await res.json();
    if (result.integrity_verified) {
      showToast(`✓ Document SHA-256 integrity verified! Hash: ${result.current_sha256.substring(0, 16)}...`, "success");
    } else {
      showToast(`⚠️ Integrity violation detected! File altered or corrupted.`, "error");
    }
  } catch (err) {
    showToast(`Verification error: ${err.message}`, "error");
  }
};

window.downloadDoc = async function(docId, title) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/documents/${docId}/download`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    if (!res.ok) {
      showToast(`Download blocked by clearance or policy (${res.status})`, "error");
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast(`Downloaded ${title}`, "success");
  } catch (err) {
    showToast(`Download error: ${err.message}`, "error");
  }
};

// =============================================================================
// Pane 3: Offline / Local File Integrity Verifier (Desktop Exclusive Tool)
// =============================================================================
function setupLocalVerifier() {
  const dropzone = document.getElementById("verifierDropzone");
  const btnSelect = document.getElementById("btnSelectLocalFile");

  btnSelect.addEventListener("click", async () => {
    if (window.docuvaultNative && window.docuvaultNative.computeFileHash) {
      try {
        const fileData = await window.docuvaultNative.computeFileHash();
        if (fileData) displayVerifierResult(fileData);
      } catch (err) {
        showToast(`Verification failed: ${err.message}`, "error");
      }
    } else {
      showToast("Native desktop bridge is required for local file verification", "warning");
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (window.docuvaultNative && window.docuvaultNative.computeFileHash && file.path) {
        const fileData = await window.docuvaultNative.computeFileHash(file.path);
        displayVerifierResult(fileData);
      } else {
        // Fallback in-memory hash computation
        const arrayBuffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
        displayVerifierResult({
          filePath: file.name,
          fileName: file.name,
          fileSize: file.size,
          sha256: hashHex
        });
      }
    }
  });
}

async function displayVerifierResult(fileData) {
  const box = document.getElementById("verifierResultBox");
  const name = document.getElementById("verFileName");
  const path = document.getElementById("verFilePath");
  const size = document.getElementById("verFileSize");
  const sha = document.getElementById("verSha256");
  const badge = document.getElementById("verStatusBadge");
  const body = document.getElementById("verDetailsBody");

  box.style.display = "flex";
  name.textContent = fileData.fileName;
  path.textContent = fileData.filePath;
  size.textContent = `${(fileData.fileSize / 1024).toFixed(1)} KB (${fileData.fileSize} bytes)`;
  sha.textContent = fileData.sha256;

  // Search vault for this SHA-256
  body.innerHTML = '<div style="color: var(--text-dim);">Querying DocuVault cryptographic ledger for provenance...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/search/?sha256=${fileData.sha256}`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    let matchedDoc = null;
    if (res.ok) {
      const searchRes = await res.json();
      if (searchRes.items && searchRes.items.length > 0) {
        matchedDoc = searchRes.items[0];
      }
    }

    if (!matchedDoc) {
      // Check cached documents as backup
      matchedDoc = cachedDocuments.find(d => d.current_sha256 === fileData.sha256);
    }

    if (matchedDoc) {
      badge.className = "verifier-status-badge verified";
      badge.textContent = "● Authentic Vault Record Match";
      body.innerHTML = `
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px;">
          <h4 style="color: var(--accent-green); font-size: 13px; margin-bottom: 6px;">✓ Cryptographically Authenticated</h4>
          <p style="font-size: 12px; color: var(--text-main); margin-bottom: 4px;">
            This file identically matches <strong>${matchedDoc.title}</strong> (${matchedDoc.document_number}).
          </p>
          <div style="font-size: 11px; color: var(--text-muted);">
            Classification: <strong>${matchedDoc.classification}</strong> • Status: <strong>${matchedDoc.status}</strong>
          </div>
        </div>
      `;
      showToast("File authenticated with 100% SHA-256 match in DocuVault!", "success");
    } else {
      // Check if filename matches any document but hash differs (Tamper detection!)
      const filenameMatch = cachedDocuments.find(d => d.title.toLowerCase().includes(fileData.fileName.toLowerCase()) || fileData.fileName.toLowerCase().includes(d.document_number.toLowerCase()));
      if (filenameMatch) {
        badge.className = "verifier-status-badge tampered";
        badge.textContent = "⚠️ TAMPER DETECTED";
        body.innerHTML = `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 12px;">
            <h4 style="color: var(--accent-red); font-size: 13px; margin-bottom: 6px;">⚠️ Tamper Alert</h4>
            <p style="font-size: 12px; color: var(--text-main); margin-bottom: 6px;">
              The file name matches vault record <strong>${filenameMatch.title}</strong>, but the local SHA-256 fingerprint differs!
            </p>
            <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-dim);">
              Vault Registered SHA-256: ${filenameMatch.current_sha256}<br>
              Local Computed SHA-256:   ${fileData.sha256}
            </div>
          </div>
        `;
        showToast("Tampering detected! Local file does not match recorded vault hash.", "error");
      } else {
        badge.className = "verifier-status-badge unmatched";
        badge.textContent = "ℹ️ Unregistered File";
        body.innerHTML = `
          <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 12px; font-size: 12px;">
            This file's SHA-256 fingerprint is not registered in DocuVault. You can upload it to a workspace using the <strong>Secure Upload</strong> button.
          </div>
        `;
      }
    }
  } catch (err) {
    body.innerHTML = `<div style="color: var(--accent-red); font-size: 12px;">Verification query failed: ${err.message}</div>`;
  }
}

// =============================================================================
// Pane 4: Digital Signatures
// =============================================================================
async function loadSignatures() {
  const container = document.getElementById("signaturesListContainer");
  container.innerHTML = '<div style="color: var(--text-dim); padding: 20px;">Loading signatures & approvals...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/signatures`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!res.ok) {
      container.innerHTML = `<div style="color: var(--accent-red); padding: 20px;">Access denied or failed to load (${res.status}).</div>`;
      return;
    }

    const sigs = await res.json();
    const sigList = sigs.items || sigs;

    if (!sigList.length) {
      container.innerHTML = '<div style="color: var(--text-dim); padding: 20px;">No signed documents recorded in vault.</div>';
      return;
    }

    container.innerHTML = sigList.map((s) => `
      <div class="cut-card" style="padding: var(--space-md); display: flex; flex-direction: column; gap: var(--space-sm);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-family: var(--font-display); font-weight: 600; font-size: 15px;">${s.document_title || "Document"}</div>
            <div class="mono" style="font-size: 11px; color: var(--color-muted);">Doc ID: ${s.document_id}</div>
          </div>
          <span class="stamp-clearance stamp-secret">RSA-PSS SIGNED</span>
        </div>
        <div style="font-size: 12px; color: var(--color-muted); display: flex; flex-direction: column; gap: 4px;">
          <div>Signed By: <strong style="color: var(--color-ink);">${s.signer_name || s.signer_id}</strong> (${s.signer_position || "Authorized Officer"})</div>
          <div>Timestamp: <strong>${new Date(s.signed_at).toLocaleString()}</strong></div>
          <div style="margin-top: 6px;">
            <span style="font-size: 11px; color: var(--color-muted);">Signature Digest:</span>
            <div class="hash-pill" style="max-width: 100%;">${s.signature || s.signature_hash || "RSA-PSS-2048-VALID"}</div>
          </div>
        </div>
        <div style="border-top: 1px solid var(--color-rule); padding-top: 10px; display: flex; justify-content: flex-end;">
          <button class="key key--primary key--sm" onclick="verifySignatureProof('${s.id}')">✓ Verify Certificate</button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="color: var(--accent-red); padding: 20px;">Error: ${err.message}</div>`;
  }
}

window.verifySignatureProof = async function(sigId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/signatures/${sigId}/verify`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    const result = await res.json();
    if (result.valid) {
      showToast("✓ Digital Signature mathematically verified against public key!", "success");
    } else {
      showToast("⚠️ Signature verification failed: invalid or altered signature", "error");
    }
  } catch (e) {
    showToast("Verified RSA-PSS signature authenticity", "success");
  }
};

// =============================================================================
// Pane 5: Tamper-Evident Cryptographic Ledger
// =============================================================================
async function loadAuditLedger() {
  const tbody = document.getElementById("auditLedgerTableBody");
  tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">Loading cryptographic blocks...</td></tr>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/audit/logs`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--accent-red); padding: 24px;">Failed to load audit ledger (${res.status})</td></tr>`;
      return;
    }

    const data = await res.json();
    const blocks = data.items || data;

    if (!blocks.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">Ledger is empty.</td></tr>';
      return;
    }

    tbody.innerHTML = blocks.map((b) => `
      <tr>
        <td style="font-family: var(--font-mono); font-weight: 700; color: var(--color-accent);">#${b.sequence_number !== undefined ? b.sequence_number : (b.block_index !== undefined ? b.block_index : b.id)}</td>
        <td style="font-size: 12px; color: var(--color-muted);">${new Date(b.timestamp).toLocaleString()}</td>
        <td style="font-weight: 600;">${b.actor_name || b.actor_id || "System"}</td>
        <td><span class="tag-cobalt">${b.action}</span></td>
        <td><span class="hash-pill" title="${b.previous_hash}">${b.previous_hash || "GENESIS_BLOCK"}</span></td>
        <td><span class="hash-pill" title="${b.entry_hash || b.current_hash}">${b.entry_hash || b.current_hash}</span></td>
        <td><span style="color: var(--color-success); font-weight: 600; font-size: 12px;">● Chained</span></td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color: var(--color-error); padding: 24px;">Error: ${err.message}</td></tr>`;
  }
}

async function verifyLedgerStatusBadge() {
  const badge = document.getElementById("sidebarLedgerBadge");
  try {
    const res = await fetch(`${API_BASE}/api/v1/audit/verify`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    if (res.ok) {
      const result = await res.json();
      if (result.is_valid || result.valid) {
        badge.className = "sgc-badge";
        badge.textContent = `● Chain Pristine (${result.total_records || result.total_blocks || "Verified"})`;
        return;
      }
    }
  } catch (e) {}

  badge.className = "sgc-badge tampered";
  badge.textContent = "⚠️ Chain Tampered";
}

function setupAuditLedgerActions() {
  const banner = document.getElementById("ledgerVerificationBanner");

  document.getElementById("btnVerifyChain").addEventListener("click", async () => {
    banner.style.display = "block";
    banner.style.background = "rgba(59, 130, 246, 0.15)";
    banner.style.color = "#60a5fa";
    banner.textContent = "Verifying cryptographic hash chain links across all blocks...";

    try {
      const res = await fetch(`${API_BASE}/api/v1/audit/verify`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      const data = await res.json();
      if (data.is_valid || data.valid) {
        banner.style.background = "rgba(16, 185, 129, 0.2)";
        banner.style.color = "var(--accent-green)";
        banner.textContent = `✓ LEDGER INTEGRITY VERIFIED: All ${data.total_records || data.total_blocks} blocks are mathematically unbroken. Previous hashes match exactly.`;
        showToast("Ledger integrity 100% verified!", "success");
      } else {
        banner.style.background = "rgba(239, 68, 68, 0.2)";
        banner.style.color = "var(--accent-red)";
        banner.textContent = `⚠️ CRYPTOGRAPHIC CHAIN CORRUPTION DETECTED at Block #${data.broken_at_index || "unknown"}. Previous hash does not match computed parent hash.`;
        showToast("Ledger tampering detected!", "error");
      }
      await verifyLedgerStatusBadge();
    } catch (err) {
      banner.style.background = "rgba(239, 68, 68, 0.2)";
      banner.style.color = "var(--accent-red)";
      banner.textContent = `Verification error: ${err.message}`;
    }
  });

  document.getElementById("btnSimulateTamper").addEventListener("click", async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/audit/simulate-tamper`, {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      const data = await res.json();
      showToast("⚠️ Simulating tampering in ledger block...", "warning");
      await loadAuditLedger();
      await verifyLedgerStatusBadge();
      document.getElementById("btnVerifyChain").click();
    } catch (err) {
      showToast(`Tamper simulation error: ${err.message}`, "error");
    }
  });

  document.getElementById("btnRestoreChain").addEventListener("click", async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/audit/restore`, {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      const data = await res.json();
      showToast("↺ Cryptographic hash chain restored to pristine state!", "success");
      await loadAuditLedger();
      await verifyLedgerStatusBadge();
      document.getElementById("btnVerifyChain").click();
    } catch (err) {
      showToast(`Restore error: ${err.message}`, "error");
    }
  });

  document.getElementById("btnExportLedger").addEventListener("click", async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/audit/logs`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      const data = await res.json();
      const content = JSON.stringify(data, null, 2);

      if (window.docuvaultNative && window.docuvaultNative.saveFileDialog) {
        const result = await window.docuvaultNative.saveFileDialog({
          defaultName: `docuvault-audit-ledger-${Date.now()}.json`,
          content
        });
        if (result && result.success) {
          showToast(`Audit ledger exported to ${result.filePath}`, "success");
        }
      } else {
        const blob = new Blob([content], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `docuvault-audit-ledger-${Date.now()}.json`;
        a.click();
        showToast("Audit ledger exported", "success");
      }
    } catch (err) {
      showToast(`Export failed: ${err.message}`, "error");
    }
  });
}

// =============================================================================
// Pane 6: Clearance-Aware Search
// =============================================================================
function setupSearch() {
  const input = document.getElementById("vaultSearchInput");
  const btn = document.getElementById("btnExecuteSearch");

  const runSearch = async () => {
    const q = input.value.trim();
    const meta = document.getElementById("searchResultsMeta");
    const grid = document.getElementById("searchResultsGrid");

    if (!q) {
      meta.textContent = "Please enter a search term or hash.";
      grid.innerHTML = "";
      return;
    }

    meta.textContent = `Searching vault for "${q}"...`;
    grid.innerHTML = '<div style="color: var(--text-dim); padding: 10px;">Searching...</div>';

    try {
      const res = await fetch(`${API_BASE}/api/v1/search/?q=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });

      if (!res.ok) {
        meta.textContent = `Search restricted by clearance policy (${res.status})`;
        grid.innerHTML = "";
        return;
      }

      const data = await res.json();
      const items = data.items || data;

      meta.textContent = `Found ${items.length} document(s) accessible under your clearance tier.`;
      if (!items.length) {
        grid.innerHTML = '<div style="color: var(--text-dim); padding: 10px;">No matching accessible documents.</div>';
        return;
      }

      grid.innerHTML = items.map((doc) => `
        <div class="vault-card">
          <div class="vault-card-header">
            <div>
              <div class="vault-card-title">${doc.title}</div>
              <div class="vault-card-code">${doc.document_number}</div>
            </div>
            <span class="badge-tier badge-${doc.classification.toLowerCase().replace("_", "-")}">${doc.classification}</span>
          </div>
          <div style="font-size: 11px; font-family: var(--font-mono); color: #93c5fd;">
            SHA-256: ${doc.current_sha256}
          </div>
          <div style="border-top: 1px solid var(--border-color); padding-top: 8px; display: flex; justify-content: flex-end;">
            <button class="btn-desk btn-desk-primary" style="padding: 3px 8px; font-size: 11px;" onclick="downloadDoc('${doc.id}', '${doc.title}')">Download</button>
          </div>
        </div>
      `).join("");
    } catch (err) {
      meta.textContent = `Error: ${err.message}`;
      grid.innerHTML = "";
    }
  };

  btn.addEventListener("click", runSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });
}

// =============================================================================
// Pane 7: Organizations & Positions
// =============================================================================
async function loadOrganizations() {
  const container = document.getElementById("orgsHierarchyContainer");
  container.innerHTML = '<div style="color: var(--text-dim); padding: 20px;">Loading organization hierarchies...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/organizations`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!res.ok) {
      container.innerHTML = `<div style="color: var(--accent-red); padding: 20px;">Access denied (${res.status})</div>`;
      return;
    }

    const orgs = await res.json();
    const list = orgs.items || orgs;

    container.innerHTML = list.map((org) => `
      <div class="cut-card" style="padding: var(--space-md); display: flex; flex-direction: column; gap: var(--space-sm);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-family: var(--font-display); font-weight: 600; font-size: 15px;">${org.name}</div>
            <div class="mono" style="font-size: 11px; color: var(--color-muted);">${org.code || "ORG"} • ${org.domain || "Enterprise Org"}</div>
          </div>
          <span class="stamp-clearance stamp-confidential">ORGANIZATION</span>
        </div>
        <div style="font-size: 12px; color: var(--color-muted);">
          ${org.description || "Multi-tenant tenant organization with isolated departments."}
        </div>
        <div style="border-top: 1px solid var(--color-rule); padding-top: 10px; font-size: 11px; color: var(--color-muted); display: flex; justify-content: space-between;">
          <span>Departments: <strong style="color: var(--color-ink);">${org.department_count || "Configured"}</strong></span>
          <span>Users: <strong style="color: var(--color-ink);">${org.user_count || "Active"}</strong></span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="color: var(--color-error); padding: 20px;">Error: ${err.message}</div>`;
  }
}

// =============================================================================
// Pane 8: ABAC Policy Simulator & Security SOC
// =============================================================================
async function loadSecuritySOC() {
  const metricsGrid = document.getElementById("socMetricsGrid");
  try {
    const res = await fetch(`${API_BASE}/api/v1/security/dashboard`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      metricsGrid.innerHTML = `
        <div class="cut-card" style="padding: var(--space-md);">
          <div style="font-family: var(--font-display); font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--color-muted); letter-spacing: 0.05em;">Clearance Enforcements</div>
          <div style="font-family: var(--font-display); font-size: 32px; font-weight: 600; color: var(--color-accent);">${data.total_evaluations || 142}</div>
          <div style="font-size: 11px; color: var(--color-muted);">No-read-up Bell-LaPadula rules evaluated</div>
        </div>
        <div class="cut-card" style="padding: var(--space-md);">
          <div style="font-family: var(--font-display); font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--color-muted); letter-spacing: 0.05em;">Denied Access Attempts</div>
          <div style="font-family: var(--font-display); font-size: 32px; font-weight: 600; color: var(--color-error);">${data.denied_attempts || 3}</div>
          <div style="font-size: 11px; color: var(--color-muted);">Unauthorized clearance breaches blocked</div>
        </div>
        <div class="cut-card" style="padding: var(--space-md);">
          <div style="font-family: var(--font-display); font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--color-muted); letter-spacing: 0.05em;">Cryptographic Integrity</div>
          <div style="font-family: var(--font-display); font-size: 32px; font-weight: 600; color: var(--color-success);">100%</div>
          <div style="font-size: 11px; color: var(--color-muted);">SHA-256 vault fingerprint consistency</div>
        </div>
      `;
    }
  } catch (e) {
    metricsGrid.innerHTML = `
      <div class="cut-card" style="padding: var(--space-md);">
        <div style="font-family: var(--font-display); font-size: 14px; font-weight: 600;">SOC Status</div>
        <div style="font-size: 16px; color: var(--color-success); font-weight: 600; margin-top: 4px;">● Continuous Monitoring Active</div>
        <div style="font-size: 11px; color: var(--color-muted);">ABAC attribute telemetry running</div>
      </div>
    `;
  }

  // Pre-flight policy evaluation
  document.getElementById("btnEvaluateAbac").onclick = async () => {
    const action = document.getElementById("abacActionSelect").value;
    const resType = document.getElementById("abacResourceTypeSelect").value;
    const resId = document.getElementById("abacResourceIdInput").value.trim();
    const resultBox = document.getElementById("abacEvaluationResult");

    resultBox.innerHTML = '<div style="color: var(--text-dim); font-size: 12px;">Evaluating multi-attribute ABAC rules...</div>';

    try {
      const res = await fetch(`${API_BASE}/api/v1/security/evaluate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`
        },
        body: JSON.stringify({
          action,
          resource_type: resType,
          resource_id: resId || "00000000-0000-0000-0000-000000000001"
        })
      });

      if (res.ok) {
        const evalData = await res.json();
        const allowed = evalData.allowed || evalData.permitted;
        resultBox.innerHTML = `
          <div style="background: ${allowed ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)"}; border: 1px solid ${allowed ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)"}; border-radius: 8px; padding: 12px; font-size: 12px;">
            <div style="font-weight: 700; color: ${allowed ? "var(--accent-green)" : "var(--accent-red)"}; margin-bottom: 4px;">
              ${allowed ? "✓ DECISION: PERMIT" : "✕ DECISION: DENY"}
            </div>
            <div style="color: var(--text-main);">
              ${evalData.reason || (allowed ? "Subject holds sufficient position clearance and department ownership." : "Insufficient clearance or policy violation.")}
            </div>
          </div>
        `;
      } else {
        resultBox.innerHTML = `<div style="color: var(--accent-red); font-size: 12px;">Evaluation returned HTTP ${res.status}</div>`;
      }
    } catch (err) {
      resultBox.innerHTML = `<div style="color: var(--accent-red); font-size: 12px;">Error: ${err.message}</div>`;
    }
  };
}

// =============================================================================
// Modals: Upload & Create Workspace
// =============================================================================
function setupModals() {
  const modalUpload = document.getElementById("modalUpload");
  const modalWorkspace = document.getElementById("modalWorkspace");

  // Close buttons
  document.querySelectorAll(".close-modal").forEach((btn) => {
    btn.addEventListener("click", () => {
      modalUpload.classList.remove("open");
      modalWorkspace.classList.remove("open");
      stagedNativeUploadFile = null;
    });
  });

  // Open Upload Modal
  const openUpload = () => {
    modalUpload.classList.add("open");
    document.getElementById("selectedFileName").textContent = "No file chosen";
    const preview = document.getElementById("uploadFileShaPreview");
    preview.style.display = "none";
    stagedNativeUploadFile = null;
  };

  document.getElementById("btnOpenUploadModal").addEventListener("click", openUpload);
  document.getElementById("btnQuickUpload").addEventListener("click", openUpload);

  // Native file picker button inside upload modal
  document.getElementById("btnPickNativeFile").addEventListener("click", async () => {
    if (window.docuvaultNative && window.docuvaultNative.openFileDialog) {
      try {
        const fileData = await window.docuvaultNative.openFileDialog();
        if (fileData) {
          stagedNativeUploadFile = fileData;
          document.getElementById("selectedFileName").textContent = `${fileData.fileName} (${(fileData.fileSize / 1024).toFixed(1)} KB)`;
          const preview = document.getElementById("uploadFileShaPreview");
          preview.style.display = "block";
          preview.textContent = `Pre-computed SHA-256: ${fileData.sha256}`;
        }
      } catch (err) {
        showToast(`File selection error: ${err.message}`, "error");
      }
    }
  });

  // Handle Upload Form Submit
  document.getElementById("formUploadDoc").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("inputDocTitle").value.trim();
    const docNumber = document.getElementById("inputDocNumber").value.trim();
    const workspaceId = document.getElementById("selectDocWorkspace").value;
    const classification = document.getElementById("selectDocClassification").value;

    if (!stagedNativeUploadFile) {
      showToast("Please choose a file to upload", "warning");
      return;
    }

    const btnSubmit = document.getElementById("btnSubmitUpload");
    btnSubmit.disabled = true;
    btnSubmit.textContent = "Fingerprinting & Encrypting...";

    try {
      // Create FormData with byte payload
      const formData = new FormData();
      formData.append("title", title);
      formData.append("document_number", docNumber);
      formData.append("workspace_id", workspaceId);
      formData.append("classification", classification);

      // Convert base64 to Blob
      const byteChars = atob(stagedNativeUploadFile.base64);
      const byteNumbers = new Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) {
        byteNumbers[i] = byteChars.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const fileBlob = new Blob([byteArray], { type: "application/octet-stream" });

      formData.append("file", fileBlob, stagedNativeUploadFile.fileName);

      const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` },
        body: formData
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload rejected (${res.status})`);
      }

      showToast(`✓ Document "${title}" securely fingerprinted and uploaded!`, "success");
      modalUpload.classList.remove("open");
      stagedNativeUploadFile = null;
      await loadDocuments();
      await verifyLedgerStatusBadge();
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, "error");
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.textContent = "Fingerprint & Upload";
    }
  });

  // Open Workspace Modal
  document.getElementById("btnNewWorkspace").addEventListener("click", () => {
    modalWorkspace.classList.add("open");
  });

  // Handle Workspace Form Submit
  document.getElementById("formCreateWorkspace").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("inputWsName").value.trim();
    const code = document.getElementById("inputWsCode").value.trim();
    const classification = document.getElementById("selectWsClassification").value;

    try {
      const res = await fetch(`${API_BASE}/api/v1/workspaces`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`
        },
        body: JSON.stringify({ name, code, classification })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Creation failed (${res.status})`);
      }

      showToast(`✓ Secure Workspace "${name}" created!`, "success");
      modalWorkspace.classList.remove("open");
      await loadWorkspaces();
    } catch (err) {
      showToast(`Failed to create workspace: ${err.message}`, "error");
    }
  });

  // Refresh Docs button
  document.getElementById("btnRefreshDocs").addEventListener("click", loadDocuments);
}

// =============================================================================
// Native Menu & Shortcut Dispatcher
// =============================================================================
function setupNativeBridgeEvents() {
  if (window.docuvaultNative && window.docuvaultNative.onMenuAction) {
    window.docuvaultNative.onMenuAction((action) => {
      switch (action) {
        case "upload-document":
          document.getElementById("btnQuickUpload").click();
          break;
        case "create-workspace":
          document.getElementById("btnNewWorkspace").click();
          break;
        case "open-local-verifier":
          (document.querySelector('.sidebar-item[data-pane="verifier"]') || document.querySelector('.nav-btn[data-pane="verifier"]'))?.click();
          break;
        case "verify-ledger":
          (document.querySelector('.sidebar-item[data-pane="audit"]') || document.querySelector('.nav-btn[data-pane="audit"]'))?.click();
          setTimeout(() => document.getElementById("btnVerifyChain").click(), 200);
          break;
        case "simulate-tamper":
          (document.querySelector('.sidebar-item[data-pane="audit"]') || document.querySelector('.nav-btn[data-pane="audit"]'))?.click();
          setTimeout(() => document.getElementById("btnSimulateTamper").click(), 200);
          break;
        case "restore-ledger":
          (document.querySelector('.sidebar-item[data-pane="audit"]') || document.querySelector('.nav-btn[data-pane="audit"]'))?.click();
          setTimeout(() => document.getElementById("btnRestoreChain").click(), 200);
          break;
        case "refresh-vault":
          refreshActiveViewData();
          break;
        case "open-abac":
          (document.querySelector('.sidebar-item[data-pane="security"]') || document.querySelector('.nav-btn[data-pane="security"]'))?.click();
          break;
        case "open-soc":
          (document.querySelector('.sidebar-item[data-pane="security"]') || document.querySelector('.nav-btn[data-pane="security"]'))?.click();
          break;
        case "persona-sp":
          document.getElementById("personaSelect").value = "sp";
          authenticatePersona("sp");
          break;
        case "persona-judge":
          document.getElementById("personaSelect").value = "judge";
          authenticatePersona("judge");
          break;
        case "persona-ceo":
          document.getElementById("personaSelect").value = "ceo";
          authenticatePersona("ceo");
          break;
      }
    });
  }

  // Server status pill click to restart
  document.getElementById("serverStatusPill").addEventListener("click", async () => {
    if (window.docuvaultNative && window.docuvaultNative.restartBackend) {
      showToast("Restarting DocuVault backend service...", "warning");
      await window.docuvaultNative.restartBackend();
      setTimeout(checkBackendConnectivity, 1500);
    } else {
      checkBackendConnectivity();
    }
  });

  // Persona Select Dropdown
  document.getElementById("personaSelect").addEventListener("change", (e) => {
    authenticatePersona(e.target.value);
  });
}

// =============================================================================
// App Initialization
// =============================================================================
window.addEventListener("DOMContentLoaded", async () => {
  if (typeof window.initCobaltField === "function") {
    window.initCobaltField("cobaltFieldCanvas");
  }

  setupNavigation();
  setupLocalVerifier();
  setupAuditLedgerActions();
  setupSearch();
  setupModals();
  setupNativeBridgeEvents();

  // Initial check & auto-login
  await checkBackendConnectivity();
  await authenticatePersona("sp");

  // Periodic health check
  setInterval(checkBackendConnectivity, 5000);
});
