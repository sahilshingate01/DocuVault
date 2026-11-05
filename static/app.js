/**
 * DocuVault Interactive Client Application
 */

// Predefined demo personas representing Police, Judiciary, and Enterprise roles
const PERSONAS = {
    sp: {
        email: "sp.vikram@police.gov.in",
        password: "Password123!",
        name: "SP Vikram Sharma",
        title: "Superintendent of Police",
        clearance: "TOP_SECRET",
        badge: "badge-top-secret"
    },
    si: {
        email: "arjun.das@police.gov.in",
        password: "Password123!",
        name: "Sub-Inspector Arjun Das",
        title: "Investigating Officer",
        clearance: "CONFIDENTIAL",
        badge: "badge-confidential"
    },
    judge: {
        email: "sneha.kulkarni@judiciary.gov.in",
        password: "Password123!",
        name: "Hon. Judge Sneha Kulkarni",
        title: "Principal District Judge",
        clearance: "TOP_SECRET",
        badge: "badge-top-secret"
    },
    clerk: {
        email: "manoj.verma@judiciary.gov.in",
        password: "Password123!",
        name: "Manoj Verma",
        title: "Court Record Clerk",
        clearance: "RESTRICTED",
        badge: "badge-restricted"
    },
    ceo: {
        email: "siddharth@apexcorp.com",
        password: "Password123!",
        name: "Siddharth Singhania",
        title: "Chief Executive Officer",
        clearance: "TOP_SECRET",
        badge: "badge-top-secret"
    },
    analyst: {
        email: "riya.sen@apexcorp.com",
        password: "Password123!",
        name: "Riya Sen",
        title: "Junior Analyst",
        clearance: "UNCLASSIFIED",
        badge: "badge-unclassified"
    }
};

let currentToken = null;
let currentUser = null;
let cachedWorkspaces = [];

// DOM Elements
const personaSelect = document.getElementById("personaSelect");
const activeUserName = document.getElementById("activeUserName");
const activeUserClearance = document.getElementById("activeUserClearance");
const alertBanner = document.getElementById("alertBanner");
const workspacesGrid = document.getElementById("workspacesGrid");
const documentsTableBody = document.getElementById("documentsTableBody");
const auditTableBody = document.getElementById("auditTableBody");
const verificationResultCard = document.getElementById("verificationResultCard");
const ledgerHealthBadge = document.getElementById("ledgerHealthBadge");
const signaturesContainer = document.getElementById("signaturesContainer");
const searchInput = document.getElementById("searchInput");
const searchResultsGrid = document.getElementById("searchResultsGrid");
const searchResultsCount = document.getElementById("searchResultsCount");

// Modals
const uploadModal = document.getElementById("uploadModal");
const workspaceModal = document.getElementById("workspaceModal");
const upWorkspaceSelect = document.getElementById("upWorkspaceSelect");

// Utility: Show User Notifications
function showAlert(message, type = "danger") {
    alertBanner.className = `alert-banner alert-${type}`;
    alertBanner.innerHTML = message;
    alertBanner.classList.remove("hidden");
    setTimeout(() => {
        alertBanner.classList.add("hidden");
    }, 7000);
}

// Authenticate Active Persona
async function switchPersona(key) {
    const persona = PERSONAS[key];
    try {
        const resp = await fetch("/api/v1/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: persona.email, password: persona.password })
        });
        
        if (!resp.ok) {
            const err = await resp.json();
            showAlert(`Login Failed for ${persona.name}: ${err.detail || "Error"}`, "danger");
            return;
        }

        const data = await resp.json();
        currentToken = data.token;
        currentUser = data.user;

        activeUserName.textContent = currentUser.full_name;
        activeUserClearance.textContent = currentUser.clearance_level;
        activeUserClearance.className = `badge ${persona.badge}`;

        showAlert(`Logged in as <strong>${currentUser.full_name}</strong> (${currentUser.position ? currentUser.position.title : 'Staff'}) with <strong>${currentUser.clearance_level}</strong> clearance.`, "success");

        // Reload data for current active view
        refreshActiveTab();
    } catch (e) {
        console.error("Auth error:", e);
        showAlert("Failed to connect to DocuVault API backend.", "danger");
    }
}

// Fetch helper with Bearer token
async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (currentToken) {
        options.headers["Authorization"] = `Bearer ${currentToken}`;
    }
    const response = await fetch(url, options);
    if (response.status === 403) {
        const data = await response.json();
        const reason = data.detail && data.detail.reason ? data.detail.reason : (data.detail || "Clearance or Permission Denied");
        showAlert(`🛑 <strong>SECURITY VIOLATION [403 FORBIDDEN]</strong>: ${reason}`, "danger");
    }
    return response;
}

// Tab Switching
document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

        btn.classList.add("active");
        const tabId = `tab-${btn.dataset.tab}`;
        document.getElementById(tabId).classList.add("active");

        refreshActiveTab();
    });
});

function refreshActiveTab() {
    const activeTab = document.querySelector(".tab-pane.active").id;
    if (activeTab === "tab-workspaces") loadWorkspaces();
    else if (activeTab === "tab-documents") loadDocuments();
    else if (activeTab === "tab-signatures") loadSignaturesView();
    else if (activeTab === "tab-audit") loadAuditLedger();
    else if (activeTab === "tab-search") performSearch();
}

// --- TAB 1: WORKSPACES ---
async function loadWorkspaces() {
    workspacesGrid.innerHTML = `<p class="subtitle">Loading authorized workspaces...</p>`;
    const resp = await apiFetch("/api/v1/workspaces");
    if (!resp.ok) return;

    cachedWorkspaces = await resp.json();
    workspacesGrid.innerHTML = "";
    upWorkspaceSelect.innerHTML = "";

    if (cachedWorkspaces.length === 0) {
        workspacesGrid.innerHTML = `<p class="subtitle">No accessible workspaces for your current clearance level.</p>`;
        return;
    }

    cachedWorkspaces.forEach(ws => {
        const card = document.createElement("div");
        card.className = "card";
        const badgeClass = `badge-${ws.classification.toLowerCase().replace('_', '-')}`;
        card.innerHTML = `
            <div>
                <span class="card-code">${ws.code}</span>
                <h3 class="card-title">${ws.name}</h3>
                <p class="subtitle">${ws.description || "Secure dossier container"}</p>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                <span class="badge ${badgeClass}">${ws.classification}</span>
                <span style="font-size: 0.8rem; color: var(--text-secondary);">${ws.document_count || 0} documents</span>
            </div>
        `;
        workspacesGrid.appendChild(card);

        // Populate upload select options
        const opt = document.createElement("option");
        opt.value = ws.id;
        opt.textContent = `${ws.code} - ${ws.name}`;
        upWorkspaceSelect.appendChild(opt);
    });
}

// --- TAB 2: DOCUMENTS ---
async function loadDocuments() {
    documentsTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">Loading fingerprinted documents...</td></tr>`;
    const resp = await apiFetch("/api/v1/search");
    if (!resp.ok) return;

    const data = await resp.json();
    const docs = data.results || [];
    documentsTableBody.innerHTML = "";

    if (docs.length === 0) {
        documentsTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">No documents accessible at your clearance level.</td></tr>`;
        return;
    }

    docs.forEach(doc => {
        const tr = document.createElement("tr");
        const badgeClass = `badge-${doc.classification.toLowerCase().replace('_', '-')}`;
        const curVer = doc.current_version;
        const fingerprint = curVer ? curVer.sha256_hash : "Pending";
        const statusBadge = `badge-status-${doc.status.toLowerCase()}`;

        tr.innerHTML = `
            <td style="font-family: monospace; font-weight: 600;">${doc.document_number}</td>
            <td><strong>${doc.title}</strong></td>
            <td><span class="badge ${badgeClass}">${doc.classification}</span></td>
            <td><span class="badge ${statusBadge}">${doc.status}</span></td>
            <td><span class="hash-pill" title="${fingerprint}">${fingerprint}</span></td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="inspectDocument('${doc.id}')">Inspect & Verify</button>
                ${curVer ? `<button class="btn btn-primary btn-sm" onclick="downloadVersion('${doc.id}', ${curVer.version_number})">⬇ Download</button>` : ''}
            </td>
        `;
        documentsTableBody.appendChild(tr);
    });
}

// Inspect document version & approvals
async function inspectDocument(docId) {
    const resp = await apiFetch(`/api/v1/documents/${docId}`);
    if (!resp.ok) return;

    const doc = await resp.json();
    const latest = doc.current_version;
    let detailsMsg = `Document: ${doc.title} (${doc.document_number})\n` +
        `Classification: ${doc.classification}\n` +
        `Status: ${doc.status}\n` +
        `Current SHA-256: ${latest ? latest.sha256_hash : 'N/A'}\n` +
        `Approved: ${latest && latest.is_approved ? 'YES' : 'NO'}\n` +
        `Total Versions: ${doc.versions.length}`;
    
    alert(detailsMsg);
}

// Download and verify file
async function downloadVersion(docId, versionNum) {
    const resp = await apiFetch(`/api/v1/documents/${docId}/versions/${versionNum}/download`);
    if (!resp.ok) return;

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `doc-${docId}-v${versionNum}.bin`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showAlert(`Document downloaded. Live SHA-256 fingerprint verified against vault storage.`, "success");
}

// --- TAB 3: DIGITAL SIGNATURES ---
async function loadSignaturesView() {
    signaturesContainer.innerHTML = `<p class="subtitle">Loading signable documents...</p>`;
    const resp = await apiFetch("/api/v1/search");
    if (!resp.ok) return;

    const data = await resp.json();
    const docs = data.results || [];
    signaturesContainer.innerHTML = "";

    docs.forEach(doc => {
        const curVer = doc.current_version;
        if (!curVer) return;

        const card = document.createElement("div");
        card.className = "card";
        card.style.marginBottom = "1rem";

        const isApproved = curVer.is_approved;
        const isSigned = doc.status === "SIGNED";

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <span class="card-code">${doc.document_number} (Version ${curVer.version_number})</span>
                    <h3 class="card-title">${doc.title}</h3>
                    <p class="subtitle">Fingerprint: <code class="hash-pill">${curVer.sha256_hash}</code></p>
                </div>
                <div>
                    <span class="badge ${isSigned ? 'badge-status-signed' : (isApproved ? 'badge-status-approved' : 'badge-status-draft')}">
                        ${doc.status}
                    </span>
                </div>
            </div>

            <div style="display:flex; gap:0.5rem; margin-top:1rem; align-items:center;">
                ${!isApproved ? `
                    <button class="btn btn-warning btn-sm" onclick="approveVersion('${curVer.id}')">
                        ✓ Formally Approve Version
                    </button>
                ` : ''}

                ${isApproved && !isSigned ? `
                    <button class="btn btn-primary btn-sm" onclick="signVersion('${curVer.id}')">
                        ✍️ Apply RSA-PSS Digital Signature
                    </button>
                ` : ''}

                ${curVer.signatures && curVer.signatures.length > 0 ? `
                    <button class="btn btn-success btn-sm" onclick="verifySignatureModal('${curVer.signatures[0].id}')">
                        🔍 Verify Cryptographic Signature
                    </button>
                ` : ''}
            </div>
        `;
        signaturesContainer.appendChild(card);
    });
}

async function approveVersion(versionId) {
    const resp = await apiFetch(`/api/v1/signatures/approve/${versionId}`, { method: "POST" });
    if (resp.ok) {
        showAlert("Document version formally approved! It may now be digitally signed.", "success");
        loadSignaturesView();
    }
}

async function signVersion(versionId) {
    const resp = await apiFetch(`/api/v1/signatures/sign/${versionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Official endorsement by authorized authority" })
    });

    if (resp.ok) {
        const sig = await resp.json();
        showAlert(`Successfully digitally signed using RSA-PSS-SHA256! Signature ID: ${sig.id.substring(0, 8)}...`, "success");
        loadSignaturesView();
    }
}

async function verifySignatureModal(signatureId) {
    const resp = await apiFetch(`/api/v1/signatures/verify/${signatureId}`);
    if (resp.ok) {
        const report = await resp.json();
        alert(
            `DIGITAL SIGNATURE VERIFICATION REPORT:\n` +
            `Valid: ${report.is_valid ? 'YES (AUTHENTIC)' : 'NO (TAMPERED)'}\n` +
            `Document: ${report.document_title} (v${report.version_number})\n` +
            `Signer: ${report.signer_name} (${report.signer_title})\n` +
            `Signed Fingerprint: ${report.sha256_fingerprint}\n` +
            `Algorithm: ${report.algorithm}\n` +
            `Details: ${report.message}`
        );
    }
}

// --- TAB 4: TAMPER-EVIDENT LEDGER ---
async function loadAuditLedger() {
    auditTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">Loading hash-chained ledger...</td></tr>`;
    const resp = await apiFetch("/api/v1/audit/logs");
    if (!resp.ok) return;

    const logs = await resp.json();
    auditTableBody.innerHTML = "";

    logs.forEach(log => {
        const tr = document.createElement("tr");
        const statusColor = log.status === "SUCCESS" ? "color:#34d399;" : (log.status === "DENIED" ? "color:#f87171;" : "color:#fbbf24;");
        tr.innerHTML = `
            <td>#${log.sequence_number}</td>
            <td style="font-size:0.75rem; color:var(--text-secondary);">${new Date(log.timestamp).toLocaleTimeString()}</td>
            <td><strong>${log.user_name || "System"}</strong> <span style="font-size:0.7rem; color:var(--text-secondary);">(${log.user_position || 'N/A'})</span></td>
            <td><code>${log.action}</code></td>
            <td><span class="hash-pill" title="${log.previous_hash}">${log.previous_hash}</span></td>
            <td><span class="hash-pill" title="${log.entry_hash}">${log.entry_hash}</span></td>
            <td style="${statusColor} font-weight:600;">${log.status}</td>
        `;
        auditTableBody.appendChild(tr);
    });
}

// Verify Ledger Integrity
document.getElementById("btnVerifyLedger").addEventListener("click", async () => {
    const resp = await apiFetch("/api/v1/audit/verify");
    if (!resp.ok) return;

    const res = await resp.json();
    verificationResultCard.classList.remove("hidden");
    if (res.is_valid) {
        verificationResultCard.className = "verification-card valid";
        verificationResultCard.innerHTML = `
            <strong>✓ Cryptographic Audit Ledger Intact:</strong> ${res.message} 
            (${res.total_records} chained blocks verified to genesis).
        `;
        ledgerHealthBadge.textContent = "● Chain Pristine";
        ledgerHealthBadge.className = "status-badge-intact";
    } else {
        verificationResultCard.className = "verification-card invalid";
        verificationResultCard.innerHTML = `
            <strong>⚠️ CRITICAL TAMPER ALERT:</strong> ${res.message} 
            (Integrity broken at block sequence #${res.broken_at_sequence}).
        `;
        ledgerHealthBadge.textContent = `▲ Tamper Detected (#${res.broken_at_sequence})`;
        ledgerHealthBadge.style.background = "rgba(239, 68, 68, 0.2)";
        ledgerHealthBadge.style.color = "#f87171";
    }
});

// Simulate Tampering
document.getElementById("btnSimulateTamper").addEventListener("click", async () => {
    const resp = await apiFetch("/api/v1/audit/simulate-tampering", { method: "POST" });
    if (!resp.ok) return;

    const res = await resp.json();
    showAlert("Database record tampered for demonstration! Notice how verification instantly catches the modification.", "warning");
    loadAuditLedger();
    document.getElementById("btnVerifyLedger").click();
});

// Restore Ledger
document.getElementById("btnRestoreLedger").addEventListener("click", async () => {
    const resp = await apiFetch("/api/v1/audit/recalculate-ledger", { method: "POST" });
    if (resp.ok) {
        showAlert("Ledger hash chain restored to consistent cryptographic state.", "success");
        loadAuditLedger();
        document.getElementById("btnVerifyLedger").click();
    }
});

// --- TAB 5: CLEARANCE SEARCH ---
async function performSearch() {
    const q = searchInput.value.trim();
    searchResultsGrid.innerHTML = `<p class="subtitle">Searching vault records...</p>`;
    const resp = await apiFetch(`/api/v1/search?q=${encodeURIComponent(q)}`);
    if (!resp.ok) return;

    const data = await resp.json();
    const docs = data.results || [];
    searchResultsCount.textContent = `Found ${data.total_matches} documents accessible to clearance tier '${currentUser.clearance_level}'.`;
    searchResultsGrid.innerHTML = "";

    docs.forEach(doc => {
        const card = document.createElement("div");
        card.className = "card";
        const badgeClass = `badge-${doc.classification.toLowerCase().replace('_', '-')}`;
        card.innerHTML = `
            <div>
                <span class="card-code">${doc.document_number}</span>
                <h3 class="card-title">${doc.title}</h3>
                <p class="subtitle">${doc.description || 'No description provided'}</p>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge ${badgeClass}">${doc.classification}</span>
                <button class="btn btn-secondary btn-sm" onclick="inspectDocument('${doc.id}')">Inspect</button>
            </div>
        `;
        searchResultsGrid.appendChild(card);
    });
}

document.getElementById("btnSearch").addEventListener("click", performSearch);
searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") performSearch();
});

// --- MODAL HANDLERS ---
document.getElementById("btnUploadDoc").addEventListener("click", () => {
    uploadModal.classList.remove("hidden");
});

document.getElementById("btnNewWorkspace").addEventListener("click", () => {
    workspaceModal.classList.remove("hidden");
});

document.querySelectorAll(".close-modal").forEach(b => {
    b.addEventListener("click", () => {
        uploadModal.classList.add("hidden");
        workspaceModal.classList.add("hidden");
    });
});

// Upload Form Submit
document.getElementById("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("title", document.getElementById("upTitle").value);
    formData.append("document_number", document.getElementById("upDocNumber").value);
    formData.append("workspace_id", document.getElementById("upWorkspaceSelect").value);
    formData.append("classification", document.getElementById("upClassification").value);
    formData.append("file", document.getElementById("upFile").files[0]);

    const resp = await apiFetch("/api/v1/documents/upload", {
        method: "POST",
        body: formData
    });

    if (resp.ok) {
        showAlert("Document successfully uploaded and fingerprinted with SHA-256!", "success");
        uploadModal.classList.add("hidden");
        document.getElementById("uploadForm").reset();
        loadDocuments();
    }
});

// Workspace Form Submit
document.getElementById("workspaceForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        name: document.getElementById("wsName").value,
        code: document.getElementById("wsCode").value,
        classification: document.getElementById("wsClassification").value
    };

    const resp = await apiFetch("/api/v1/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });

    if (resp.ok) {
        showAlert("New workspace successfully created!", "success");
        workspaceModal.classList.add("hidden");
        document.getElementById("workspaceForm").reset();
        loadWorkspaces();
    }
});

// Persona select listener
personaSelect.addEventListener("change", (e) => {
    switchPersona(e.target.value);
});

// Initialize with Superintendent of Police persona
switchPersona("sp");
