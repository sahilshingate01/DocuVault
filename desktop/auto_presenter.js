/**
 * DocuVault Automated Screen Presentation & Recording Conductor
 * Synchronized with DBMS_VIVA_SCRIPT.md for video recording & voiceover.
 */

(function () {
  const urlParams = new URLSearchParams(window.location.search);
  const isAuto = urlParams.get("autopresent") === "true";
  const speed = parseFloat(urlParams.get("speed") || "1.0");

  // Step timeline definition in seconds (at speed 1.0)
  const TIMELINE = [
    {
      time: 0,
      title: "Introduction",
      text: "DocuVault: DigiLocker-Grade Secure Document Management & Cryptographic Provenance System.",
      action: async () => {
        const wsBtn = document.querySelector('.nav-item[data-tab="workspaces"]') || document.querySelector('.sidebar-item[data-pane="workspaces"]');
        if (wsBtn) wsBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 15,
      title: "Introduction: Clearance & Multi-Tenant Access",
      text: "Demonstrating role-based access control and case dossier workspace boundaries.",
      action: async () => {
        const pSelect = document.getElementById("personaSelect");
        if (pSelect) {
          pSelect.value = "judge";
          pSelect.dispatchEvent(new Event("change"));
          setTimeout(() => {
            if (pSelect) {
              pSelect.value = "sp";
              pSelect.dispatchEvent(new Event("change"));
            }
          }, 8000 / speed);
        }
      }
    },
    {
      time: 35,
      title: "Navigating to DBMS Viva Studio",
      text: "Opening the DBMS Architecture & Live Query Console.",
      action: async () => {
        const dbmsBtn = document.querySelector('.nav-item[data-tab="dbms"]') || document.querySelector('.sidebar-item[data-pane="dbms"]');
        if (dbmsBtn) dbmsBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 45,
      title: "Q1: Why Did You Choose This Database?",
      text: "Relational RDBMS (SQLite 3 WAL Mode / PostgreSQL). 80% Reads : 20% Writes. Immediate Strong Consistency.",
      action: async () => {
        const q1Card = document.querySelector('.card:nth-child(1)') || document.querySelector('.cut-card:nth-child(1)');
        if (q1Card) q1Card.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    {
      time: 80,
      title: "Q1: Rejected Alternative (MongoDB)",
      text: "MongoDB rejected: lack of native cascading foreign keys and hash-chain ordering guarantees across collections.",
      action: async () => {
        const invTable = document.getElementById("webDbmsTableBody") || document.getElementById("dbmsTableInventoryBody");
        if (invTable) invTable.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    {
      time: 120,
      title: "Q1: Table Inventory Inspection",
      text: "Inspecting all 11 normalized tables, row counts, and primary key constraints.",
      action: async () => {
        window.scrollTo({ top: 350, behavior: "smooth" });
      }
    },
    {
      time: 145,
      title: "Q2: Schema Architecture & Relational Model",
      text: "11 Normalized Tables. 1:N relations and Many-to-Many resolved via digital_signatures and temporary_clearances.",
      action: async () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 165,
      title: "Q2: Live 6-Table Relational JOIN",
      text: "Executing multi-table JOIN across documents, workspaces, versions, users, positions, and signatures.",
      action: async () => {
        const joinBtn = document.getElementById("webBtnRunVivaJoin") || document.getElementById("btnRunVivaJoin");
        if (joinBtn) joinBtn.click();
      }
    },
    {
      time: 210,
      title: "Q2: Relational Integrity & Cascades",
      text: "ON DELETE CASCADE on child versions; ON DELETE SET NULL on user actors to preserve historical audit evidence.",
      action: async () => {
        const outBox = document.getElementById("webVivaLiveOutput") || document.getElementById("vivaLiveOutput");
        if (outBox) outBox.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    {
      time: 245,
      title: "Q3: Normalization (3NF / BCNF)",
      text: "1NF (atomic attributes), 2NF (UUID key dependencies), 3NF (transitive dependencies removed). BCNF in documents.",
      action: async () => {
        const closeBtn = document.getElementById("webBtnCloseVivaOutput") || document.getElementById("btnCloseVivaOutput");
        if (closeBtn) closeBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 285,
      title: "Q3: Deliberate Denormalization in audit_logs",
      text: "audit_logs preserves user snapshot (name, email, position) to prevent evidence tampering if staff leaves.",
      action: async () => {
        window.scrollTo({ top: 120, behavior: "smooth" });
      }
    },
    {
      time: 330,
      title: "Q4: Data Correctness & Atomic Transactions",
      text: "NOT NULL, UNIQUE, FOREIGN KEYs. Atomic uploads commit [Doc] + [Version] + [AuditLink] simultaneously.",
      action: async () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 350,
      title: "Q4: Atomic Transaction & Rollback Demo",
      text: "Simulating disk fault halfway through upload. Zero orphan records persisted; rollback verified.",
      action: async () => {
        const txBtn = document.getElementById("webBtnTestTx") || document.getElementById("btnTestTransaction");
        if (txBtn) txBtn.click();
      }
    },
    {
      time: 405,
      title: "Q4: EXTRA CREDIT — Live Constraint Rejection",
      text: "Deliberately inserting duplicate document_number into database. Kernel rejects write immediately!",
      action: async () => {
        const constBtn = document.getElementById("webBtnTriggerConstraint") || document.getElementById("btnTriggerConstraintRejection");
        if (constBtn) constBtn.click();
      }
    },
    {
      time: 465,
      title: "Q5: Database Efficiency & EXPLAIN Index Plan",
      text: "B-Tree index on sha256_hash enables O(log N) lookup. Full table scan required for unindexed search.",
      action: async () => {
        const planBtn = document.getElementById("webBtnExplainPlan") || document.getElementById("btnExplainPlan");
        if (planBtn) planBtn.click();
      }
    },
    {
      time: 500,
      title: "Q5: 100x Growth Scaling Strategy",
      text: "Range partitioning on audit_logs, read replicas, cloud blob decoupling to S3/GCS, and Redis clearance caching.",
      action: async () => {
        const outBox = document.getElementById("webVivaLiveOutput") || document.getElementById("vivaLiveOutput");
        if (outBox) {
          outBox.scrollIntoView({ behavior: "smooth", block: "center" });
          const pre = outBox.querySelector("pre") || document.getElementById("vivaOutputBody");
          if (pre) pre.scrollTop = pre.scrollHeight;
        }
      }
    },
    {
      time: 525,
      title: "Conclusion & Audit Verification",
      text: "Returning to Tamper-Evident Ledger. Cryptographic hash chain verified 100% pristine.",
      action: async () => {
        const auditBtn = document.querySelector('.nav-item[data-tab="audit"]') || document.querySelector('.sidebar-item[data-pane="audit"]');
        if (auditBtn) auditBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 540,
      title: "Viva Demonstration Complete",
      text: "Screen demonstration finished successfully. Video ready for submission.",
      action: async () => {
        console.log("Auto-presentation finished.");
      }
    }
  ];

  function createHUD() {
    const hud = document.createElement("div");
    hud.id = "autoPresenterHUD";
    hud.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: oklch(18% 0.024 262 / 0.95);
      border: 1px solid oklch(52% 0.19 258 / 0.6);
      box-shadow: 0 12px 32px oklch(10% 0.02 260 / 0.5);
      backdrop-filter: blur(10px);
      border-radius: 8px;
      padding: 14px 18px;
      z-index: 99999;
      color: #fff;
      font-family: "IBM Plex Sans", -apple-system, sans-serif;
      max-width: 440px;
      transition: all 0.3s ease;
      pointer-events: auto;
    `;
    hud.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: oklch(76% 0.13 254); text-transform: uppercase; font-weight: 600; display: flex; align-items: center; gap: 6px;">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: #ef4444; display: inline-block; animation: pulse 1.2s infinite;"></span>
          REC SYNC • <span id="hudTimer">00:00</span> / 09:00
        </div>
        <div style="font-size: 11px; color: #9ca3af; font-family: monospace;">Speed: ${speed}x</div>
      </div>
      <div id="hudTitle" style="font-family: 'Familjen Grotesk', sans-serif; font-size: 14px; font-weight: 600; margin-bottom: 4px; color: #60a5fa;">
        Starting Auto-Presentation...
      </div>
      <div id="hudSubtitle" style="font-size: 12px; color: #e5e7eb; line-height: 1.4;">
        Screen will automatically click and demonstrate each DBMS viva question.
      </div>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end; gap: 8px;">
        <button id="btnToggleHudSubtitles" style="background: rgba(255,255,255,0.1); border: none; color: #9ca3af; font-size: 10px; padding: 3px 8px; border-radius: 4px; cursor: pointer;">Hide Subtitles</button>
      </div>
    `;
    document.body.appendChild(hud);

    const toggleBtn = document.getElementById("btnToggleHudSubtitles");
    if (toggleBtn) {
      toggleBtn.onclick = () => {
        const sub = document.getElementById("hudSubtitle");
        if (sub.style.display === "none") {
          sub.style.display = "block";
          toggleBtn.textContent = "Hide Subtitles";
        } else {
          sub.style.display = "none";
          toggleBtn.textContent = "Show Subtitles";
        }
      };
    }
  }

  function startConductor() {
    createHUD();
    let startTime = Date.now();
    let currentStepIdx = -1;

    const interval = setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000 * speed;
      const mins = Math.floor(elapsedSec / 60);
      const secs = Math.floor(elapsedSec % 60);
      const timerEl = document.getElementById("hudTimer");
      if (timerEl) timerEl.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

      // Check next step
      const nextStepIdx = TIMELINE.findIndex((s, idx) => {
        const nextS = TIMELINE[idx + 1];
        return elapsedSec >= s.time && (!nextS || elapsedSec < nextS.time);
      });

      if (nextStepIdx !== -1 && nextStepIdx !== currentStepIdx) {
        currentStepIdx = nextStepIdx;
        const step = TIMELINE[currentStepIdx];
        const titleEl = document.getElementById("hudTitle");
        const subEl = document.getElementById("hudSubtitle");
        if (titleEl) titleEl.textContent = step.title;
        if (subEl) subEl.textContent = step.text;

        try {
          step.action();
        } catch (e) {
          console.error("Step execution error:", e);
        }
      }

      if (elapsedSec >= 540) {
        clearInterval(interval);
      }
    }, 250);
  }

  // Auto start if ?autopresent=true
  if (isAuto) {
    window.addEventListener("DOMContentLoaded", () => {
      setTimeout(startConductor, 1200);
    });
  }

  // Expose manual trigger
  window.startVivaPresentation = (customSpeed = 1.0) => {
    window.location.search = `?autopresent=true&speed=${customSpeed}`;
  };
})();
