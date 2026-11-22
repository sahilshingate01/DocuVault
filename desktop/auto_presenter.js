/**
 * DocuVault Automated Screen Presentation & Recording Conductor
 * Synchronized with DBMS_VIVA_SCRIPT.md for clean video recording & voiceover.
 * NO on-screen HUD or overlays: renders 100% natural user interaction.
 */

(function () {
  const urlParams = new URLSearchParams(window.location.search);
  const isAuto = urlParams.get("autopresent") === "true";
  const speed = parseFloat(urlParams.get("speed") || "1.0");

  function highlight(el, duration = 5000) {
    if (!el) return;
    const origOutline = el.style.outline;
    const origShadow = el.style.boxShadow;
    const origTransition = el.style.transition;

    el.style.transition = "box-shadow 0.4s ease, outline 0.4s ease";
    el.style.outline = "2px solid oklch(52% 0.19 258 / 0.8)";
    el.style.boxShadow = "0 0 0 4px oklch(52% 0.19 258 / 0.25), 0 12px 28px -6px oklch(21% 0.028 262 / 0.25)";

    setTimeout(() => {
      el.style.outline = origOutline;
      el.style.boxShadow = origShadow;
      el.style.transition = origTransition;
    }, duration / speed);
  }

  function simulateTyping(inputEl, text, charDelay = 90) {
    if (!inputEl) return;
    inputEl.value = "";
    inputEl.focus();
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        inputEl.value += text.charAt(i);
        inputEl.dispatchEvent(new Event("input", { bubbles: true }));
        i++;
      } else {
        clearInterval(timer);
        inputEl.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }, charDelay / speed);
  }

  // Finely choreographed 540-second timeline (9 minutes)
  const TIMELINE = [
    // --- 0:00 - 0:45: INTRODUCTION ---
    {
      time: 0,
      desc: "Start on Workspaces & Cases overview",
      action: async () => {
        const wsBtn = document.querySelector('.nav-item[data-tab="workspaces"]') || document.querySelector('.sidebar-item[data-pane="workspaces"]');
        if (wsBtn) wsBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 10,
      desc: "Highlight primary case dossier card",
      action: async () => {
        const firstCard = document.querySelector(".grid-cards .card") || document.querySelector(".workspace-card");
        if (firstCard) {
          highlight(firstCard, 6000);
          firstCard.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 18,
      desc: "Demonstrate RBAC persona switch to Sub-Inspector Arjun Das (CONFIDENTIAL)",
      action: async () => {
        const pSelect = document.getElementById("personaSelect");
        if (pSelect) {
          pSelect.value = "si";
          pSelect.dispatchEvent(new Event("change"));
          highlight(document.getElementById("userBadge"), 5000);
        }
      }
    },
    {
      time: 27,
      desc: "Switch persona to Hon. Judge Sneha Kulkarni (TOP SECRET)",
      action: async () => {
        const pSelect = document.getElementById("personaSelect");
        if (pSelect) {
          pSelect.value = "judge";
          pSelect.dispatchEvent(new Event("change"));
          highlight(document.getElementById("userBadge"), 5000);
        }
      }
    },
    {
      time: 34,
      desc: "Switch persona back to SP Vikram Sharma",
      action: async () => {
        const pSelect = document.getElementById("personaSelect");
        if (pSelect) {
          pSelect.value = "sp";
          pSelect.dispatchEvent(new Event("change"));
        }
      }
    },
    {
      time: 38,
      desc: "Briefly inspect Document Vault with fingerprinted files",
      action: async () => {
        const docBtn = document.querySelector('.nav-item[data-tab="documents"]') || document.querySelector('.sidebar-item[data-pane="documents"]');
        if (docBtn) docBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 44,
      desc: "Navigate into DBMS Viva Studio",
      action: async () => {
        const dbmsBtn = document.querySelector('.nav-item[data-tab="dbms"]') || document.querySelector('.sidebar-item[data-pane="dbms"]');
        if (dbmsBtn) dbmsBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },

    // --- 0:45 - 2:15: QUESTION 1: DATABASE CHOICE & WORKLOAD ---
    {
      time: 50,
      desc: "Q1: Highlight Card 1 (Database Choice & Workload Profiles)",
      action: async () => {
        const q1Card = document.querySelector("#tab-dbms .grid-cards .card:nth-child(1)") || document.querySelector("#pane-dbms .cut-card:nth-child(1)");
        if (q1Card) {
          highlight(q1Card, 14000);
          q1Card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 75,
      desc: "Q1: Smoothly scroll down to Relational Table Inventory",
      action: async () => {
        const invCard = document.getElementById("webDbmsTableBody") || document.getElementById("dbmsTableInventoryBody");
        if (invCard) invCard.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    {
      time: 88,
      desc: "Q1: Highlight documents table row in inventory",
      action: async () => {
        const rows = document.querySelectorAll("#webDbmsTableBody tr, #dbmsTableInventoryBody tr");
        rows.forEach(r => {
          if (r.textContent.includes("documents") && !r.textContent.includes("versions")) {
            highlight(r, 8000);
          }
        });
      }
    },
    {
      time: 104,
      desc: "Q1: Highlight document_versions table row in inventory",
      action: async () => {
        const rows = document.querySelectorAll("#webDbmsTableBody tr, #dbmsTableInventoryBody tr");
        rows.forEach(r => {
          if (r.textContent.includes("document_versions")) {
            highlight(r, 8000);
          }
        });
      }
    },
    {
      time: 118,
      desc: "Q1: Highlight audit_logs table row in inventory",
      action: async () => {
        const rows = document.querySelectorAll("#webDbmsTableBody tr, #dbmsTableInventoryBody tr");
        rows.forEach(r => {
          if (r.textContent.includes("audit_logs")) {
            highlight(r, 8000);
          }
        });
      }
    },
    {
      time: 132,
      desc: "Q1: Smoothly scroll back up to the viva questions grid",
      action: async () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },

    // --- 2:15 - 4:00: QUESTION 2: SCHEMA ARCHITECTURE & MULTI-TABLE JOIN ---
    {
      time: 140,
      desc: "Q2: Highlight Card 2 (Schema Architecture & Relational Model)",
      action: async () => {
        const q2Card = document.querySelector("#tab-dbms .grid-cards .card:nth-child(2)") || document.querySelector("#pane-dbms .cut-card:nth-child(2)");
        if (q2Card) {
          highlight(q2Card, 10000);
          q2Card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 152,
      desc: "Q2: Click 'Run 6-Table JOIN' to execute live query",
      action: async () => {
        const joinBtn = document.getElementById("webBtnRunVivaJoin") || document.getElementById("btnRunVivaJoin");
        if (joinBtn) {
          highlight(joinBtn, 2000);
          joinBtn.click();
        }
      }
    },
    {
      time: 158,
      desc: "Q2: Focus and highlight the live multi-table query output",
      action: async () => {
        const outBox = document.getElementById("webVivaLiveOutput") || document.getElementById("vivaLiveOutput");
        if (outBox) {
          highlight(outBox, 16000);
          outBox.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 175,
      desc: "Q2: Smoothly scroll through the joined records JSON",
      action: async () => {
        const pre = document.querySelector("#webVivaLiveOutput pre, #vivaLiveOutput pre, #vivaOutputBody");
        if (pre) pre.scrollBy({ top: 120, behavior: "smooth" });
      }
    },
    {
      time: 195,
      desc: "Q2: Scroll further through joined records",
      action: async () => {
        const pre = document.querySelector("#webVivaLiveOutput pre, #vivaLiveOutput pre, #vivaOutputBody");
        if (pre) pre.scrollBy({ top: 140, behavior: "smooth" });
      }
    },
    {
      time: 215,
      desc: "Q2: Visit Digital Signatures view to visually verify RSA signatures",
      action: async () => {
        const sigBtn = document.querySelector('.nav-item[data-tab="signatures"]') || document.querySelector('.sidebar-item[data-pane="signatures"]');
        if (sigBtn) sigBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 232,
      desc: "Q2: Return to DBMS Viva Studio",
      action: async () => {
        const dbmsBtn = document.querySelector('.nav-item[data-tab="dbms"]') || document.querySelector('.sidebar-item[data-pane="dbms"]');
        if (dbmsBtn) dbmsBtn.click();
      }
    },

    // --- 4:00 - 5:30: QUESTION 3: NORMAL FORMS (3NF/BCNF) & DENORMALIZATION ---
    {
      time: 242,
      desc: "Q3: Close output box and highlight Card 3 (Normal Forms & Denormalization)",
      action: async () => {
        const closeBtn = document.getElementById("webBtnCloseVivaOutput") || document.getElementById("btnCloseVivaOutput");
        if (closeBtn) closeBtn.click();
        const q3Card = document.querySelector("#tab-dbms .grid-cards .card:nth-child(3)") || document.querySelector("#pane-dbms .cut-card:nth-child(3)");
        if (q3Card) {
          highlight(q3Card, 14000);
          q3Card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 265,
      desc: "Q3: Switch to Tamper-Evident Ledger to visually prove the denormalized user snapshot",
      action: async () => {
        const auditBtn = document.querySelector('.nav-item[data-tab="audit"]') || document.querySelector('.sidebar-item[data-pane="audit"]');
        if (auditBtn) auditBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 278,
      desc: "Q3: Smoothly scroll down the audit ledger table",
      action: async () => {
        window.scrollTo({ top: 220, behavior: "smooth" });
      }
    },
    {
      time: 290,
      desc: "Q3: Highlight audit entry showing frozen officer name and rank snapshot",
      action: async () => {
        const row = document.querySelector("#auditTableBody tr:nth-child(2)") || document.querySelector(".cobalt-table tbody tr:nth-child(2)");
        if (row) highlight(row, 12000);
      }
    },
    {
      time: 315,
      desc: "Q3: Return to DBMS Viva Studio",
      action: async () => {
        const dbmsBtn = document.querySelector('.nav-item[data-tab="dbms"]') || document.querySelector('.sidebar-item[data-pane="dbms"]');
        if (dbmsBtn) dbmsBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },

    // --- 5:30 - 7:15: QUESTION 4: DATA CORRECTNESS, CONSTRAINTS & TRANSACTIONS ---
    {
      time: 330,
      desc: "Q4: Highlight Card 4 (Constraints & Atomic Transactions)",
      action: async () => {
        const q4Card = document.querySelector("#tab-dbms .grid-cards .card:nth-child(4)") || document.querySelector("#pane-dbms .cut-card:nth-child(4)");
        if (q4Card) {
          highlight(q4Card, 12000);
          q4Card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 348,
      desc: "Q4: Click 'Test Atomic Rollback' with simulated fault",
      action: async () => {
        const txBtn = document.getElementById("webBtnTestTx") || document.getElementById("btnTestTransaction");
        if (txBtn) {
          highlight(txBtn, 2000);
          txBtn.click();
        }
      }
    },
    {
      time: 355,
      desc: "Q4: Highlight rollback output showing 0 orphan records persisted",
      action: async () => {
        const outBox = document.getElementById("webVivaLiveOutput") || document.getElementById("vivaLiveOutput");
        if (outBox) {
          highlight(outBox, 16000);
          outBox.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 395,
      desc: "Q4: EXTRA CREDIT — Click 'Trigger Constraint Rejection'",
      action: async () => {
        const constBtn = document.getElementById("webBtnTriggerConstraint") || document.getElementById("btnTriggerConstraintRejection");
        if (constBtn) {
          highlight(constBtn, 2000);
          constBtn.click();
        }
      }
    },
    {
      time: 402,
      desc: "Q4: Highlight bright red database kernel UNIQUE constraint error!",
      action: async () => {
        const outBox = document.getElementById("webVivaLiveOutput") || document.getElementById("vivaLiveOutput");
        if (outBox) {
          highlight(outBox, 18000);
          outBox.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 425,
      desc: "Q4: Open ABAC & Security SOC view to demonstrate clearance policy evaluation",
      action: async () => {
        const secBtn = document.querySelector('.nav-item[data-tab="security"]') || document.querySelector('.sidebar-item[data-pane="security"]');
        if (secBtn) secBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 435,
      desc: "Q4: Click 'Evaluate ABAC Policy' to show dynamic policy decision",
      action: async () => {
        const evalBtn = document.getElementById("btnRunAbacEval") || document.getElementById("btnEvaluateAbac");
        if (evalBtn) evalBtn.click();
        const resBox = document.getElementById("abacEvaluationResult");
        if (resBox) highlight(resBox, 8000);
      }
    },
    {
      time: 448,
      desc: "Q4: Return to DBMS Viva Studio",
      action: async () => {
        const dbmsBtn = document.querySelector('.nav-item[data-tab="dbms"]') || document.querySelector('.sidebar-item[data-pane="dbms"]');
        if (dbmsBtn) dbmsBtn.click();
      }
    },

    // --- 7:15 - 8:45: QUESTION 5: DATABASE EFFICIENCY, INDEXES & SCALING ---
    {
      time: 456,
      desc: "Q5: Highlight Card 5 (B-Tree Indexing & 100x Growth Scaling)",
      action: async () => {
        const q5Card = document.querySelector("#tab-dbms .grid-cards .card:nth-child(5)") || document.querySelector("#pane-dbms .cut-card:nth-child(5)");
        if (q5Card) {
          highlight(q5Card, 10000);
          q5Card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 468,
      desc: "Q5: Click 'EXPLAIN Index Plan'",
      action: async () => {
        const planBtn = document.getElementById("webBtnExplainPlan") || document.getElementById("btnExplainPlan");
        if (planBtn) {
          highlight(planBtn, 2000);
          planBtn.click();
        }
      }
    },
    {
      time: 474,
      desc: "Q5: Highlight query execution plan output",
      action: async () => {
        const outBox = document.getElementById("webVivaLiveOutput") || document.getElementById("vivaLiveOutput");
        if (outBox) {
          highlight(outBox, 18000);
          outBox.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    },
    {
      time: 495,
      desc: "Q5: Scroll down inside execution plan to 100x scaling strategy",
      action: async () => {
        const pre = document.querySelector("#webVivaLiveOutput pre, #vivaLiveOutput pre, #vivaOutputBody");
        if (pre) pre.scrollBy({ top: 150, behavior: "smooth" });
      }
    },
    {
      time: 510,
      desc: "Q5: Visit Clearance Search to show fast live index lookups",
      action: async () => {
        const searchBtn = document.querySelector('.nav-item[data-tab="search"]') || document.querySelector('.sidebar-item[data-pane="search"]');
        if (searchBtn) searchBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 516,
      desc: "Q5: Simulate typing 'FIR-402' in clearance search",
      action: async () => {
        const input = document.getElementById("searchInput") || document.getElementById("inputSearchQuery");
        simulateTyping(input, "FIR-402", 90);
      }
    },

    // --- 8:45 - 9:00: CONCLUSION & PRISTINE BADGE ---
    {
      time: 524,
      desc: "Conclusion: Navigate to Tamper-Evident Ledger",
      action: async () => {
        const auditBtn = document.querySelector('.nav-item[data-tab="audit"]') || document.querySelector('.sidebar-item[data-pane="audit"]');
        if (auditBtn) auditBtn.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    {
      time: 530,
      desc: "Conclusion: Highlight the green 'Chain Pristine' cryptographic badge",
      action: async () => {
        const badge = document.getElementById("ledgerHealthBadge") || document.getElementById("sidebarLedgerBadge") || document.querySelector(".status-badge-intact");
        if (badge) highlight(badge, 9000);
      }
    },
    {
      time: 540,
      desc: "Presentation Finished",
      action: async () => {
        console.log("=== VIVA DEMONSTRATION COMPLETE ===");
      }
    }
  ];

  function startConductor() {
    console.log("=== STARTING DOCUVAULT VIVA CONDUCTOR (Speed: " + speed + "x) ===");
    let startTime = Date.now();
    let currentStepIdx = -1;

    const interval = setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000 * speed;

      const nextStepIdx = TIMELINE.findIndex((s, idx) => {
        const nextS = TIMELINE[idx + 1];
        return elapsedSec >= s.time && (!nextS || elapsedSec < nextS.time);
      });

      if (nextStepIdx !== -1 && nextStepIdx !== currentStepIdx) {
        currentStepIdx = nextStepIdx;
        const step = TIMELINE[currentStepIdx];
        console.log(`[${Math.floor(elapsedSec)}s] Step ${currentStepIdx + 1}/${TIMELINE.length}: ${step.desc}`);

        try {
          step.action();
        } catch (e) {
          console.error("Step execution error:", e);
        }
      }

      if (elapsedSec >= 540) {
        clearInterval(interval);
      }
    }, 200);
  }

  // Auto start if ?autopresent=true
  if (isAuto) {
    window.addEventListener("DOMContentLoaded", () => {
      setTimeout(startConductor, 1200);
    });
  }

  window.startVivaPresentation = (customSpeed = 1.0) => {
    window.location.search = `?autopresent=true&speed=${customSpeed}`;
  };
})();
