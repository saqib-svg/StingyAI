/**
 * Cloud Bill Agent - Stitch UI Application Logic
 * Integrates directly with FastAPI backend (/services, /agent/run, /demo/reset).
 * Fully audited for strict state consistency, run isolation, and data integrity.
 */

const SCENARIOS = {
  A: "Review current services and reduce unnecessary cost without breaking latency or availability requirements.",
  B: "Orders traffic is increasing. Keep the service within its latency target.",
  C: "Reduce cost if it is safe.",
  D: "Scale the payment service only if the current state requires it."
};

let isWorkflowRunning = false;

// Initial load
document.addEventListener("DOMContentLoaded", () => {
  fetchServices();
});

/**
 * Fetches current cloud services from GET /services and renders dynamic service cards.
 */
async function fetchServices() {
  const container = document.getElementById("services-container");
  try {
    const res = await fetch("/services");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const services = await res.json();

    if (!Array.isArray(services) || services.length === 0) {
      container.innerHTML = `<div class="p-4 text-center font-mono text-xs text-outline">No cloud services found.</div>`;
      return;
    }

    container.innerHTML = services.map(service => {
      const isHealthy = service.healthy !== false;
      const isTargeted = service.service_id === "reports-worker";

      return `
        <div class="bg-surface-container rounded-lg p-3.5 border ${isTargeted ? 'border-primary shadow-[0_0_12px_1px_rgba(6,182,212,0.2)]' : 'border-surface-container-high'} flex flex-col gap-2 transition-all">
          
          <!-- Header -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full ${isHealthy ? 'bg-tertiary' : 'bg-error'}"></span>
              <span class="font-headline text-sm font-bold text-on-surface font-mono">${escapeHtml(service.service_id)}</span>
              <span class="font-mono text-[10px] px-1.5 py-0.5 rounded ${isHealthy ? 'bg-tertiary/10 text-tertiary' : 'bg-error/10 text-error'} font-semibold">
                ${isHealthy ? 'HEALTHY ●' : 'UNHEALTHY ✖'}
              </span>
            </div>
            <div class="font-mono text-xs text-outline">
              Cost: <span class="text-on-surface font-bold">${service.cost_per_hour !== undefined ? '$' + (service.cost_per_hour || 0).toFixed(2) + '/hr' : 'N/A'}</span>
            </div>
          </div>

          <!-- Metrics Grid -->
          <div class="grid grid-cols-3 sm:grid-cols-6 gap-2 bg-surface-container-lowest p-2 rounded border border-surface-container-high font-mono text-[11px]">
            <div>
              <span class="text-outline block text-[9px] uppercase font-semibold">Instances</span>
              <span class="text-on-surface font-bold">${service.instances} <span class="text-[9px] text-outline font-normal">(${service.min_instances || 0}-${service.max_instances || 0})</span></span>
            </div>
            <div>
              <span class="text-outline block text-[9px] uppercase font-semibold">CPU Load</span>
              <span class="text-on-surface">${service.cpu_percent !== undefined ? service.cpu_percent + '%' : 'N/A'}</span>
            </div>
            <div>
              <span class="text-outline block text-[9px] uppercase font-semibold">Memory</span>
              <span class="text-on-surface">${service.memory_percent !== undefined ? service.memory_percent + '%' : 'N/A'}</span>
            </div>
            <div>
              <span class="text-outline block text-[9px] uppercase font-semibold">Traffic</span>
              <span class="text-on-surface">${service.requests_per_minute !== undefined ? service.requests_per_minute + ' RPM' : 'N/A'}</span>
            </div>
            <div>
              <span class="text-outline block text-[9px] uppercase font-semibold">Latency</span>
              <span class="text-on-surface">${service.latency_ms !== undefined ? service.latency_ms + ' ms' : 'N/A'}</span>
            </div>
            <div>
              <span class="text-outline block text-[9px] uppercase font-semibold">Telemetry</span>
              <span class="text-tertiary">${service.timestamp ? escapeHtml(service.timestamp.substring(11, 16) || 'Fresh') : 'Fresh'}</span>
            </div>
          </div>

        </div>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `<div class="p-3 rounded bg-error-container/40 text-error font-mono text-xs border border-error/30">Failed to fetch services: ${escapeHtml(err.message)}</div>`;
  }
}

/**
 * Selects one of the 4 hackathon preset evaluation scenarios.
 * Populates request input without sending network requests.
 */
async function selectScenario(key) {
  if (SCENARIOS[key]) {
    document.getElementById("agent-input").value = SCENARIOS[key];

    // Update scenario button styling
    ['A', 'B', 'C', 'D'].forEach(k => {
      const btn = document.getElementById(`scenario-btn-${k}`);
      if (btn) {
        if (k === key) {
          btn.className = "px-2.5 py-1 rounded font-mono text-xs transition-all bg-primary-container text-on-primary-container font-bold shadow-[0_0_8px_rgba(6,182,212,0.3)]";
        } else {
          btn.className = "px-2.5 py-1 rounded font-mono text-xs transition-all text-on-surface-variant hover:bg-surface-container-high";
        }
      }
    });

    // Toggle Stale Data Banner preview for Scenario C
    const staleBanner = document.getElementById("stale-safeguard-banner");
    if (staleBanner) {
      if (key === 'C') {
        staleBanner.classList.remove("hidden");
      } else {
        staleBanner.classList.add("hidden");
      }
    }

    // Load backend scenario fixture and refresh UI state
    try {
      await fetch(`/demo/scenario/${key}`, { method: "POST" });
      await fetchServices();
    } catch (err) {
      console.error("Failed to set backend scenario:", err);
    }
  }
}

/**
 * Clears the agent directive prompt input.
 */
function clearInput() {
  const input = document.getElementById("agent-input");
  if (input) {
    input.value = "";
    input.focus();
  }
}

/**
 * Resets the simulated environment via POST /demo/reset after explicit browser confirmation.
 */
async function resetDemoEnvironment() {
  const confirmed = confirm("Reset the simulated cloud environment to its initial state?");
  if (!confirmed) return;

  try {
    const res = await fetch("/demo/reset", { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    await fetchServices();

    // Clear previous execution state
    clearPreviousRunState();

    document.getElementById("res-status-badge").textContent = "IDLE";
    document.getElementById("res-status-badge").className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container text-on-surface font-bold text-[11px]";
    document.getElementById("res-run-id").textContent = "run-reset";
    document.getElementById("res-phase-badge").textContent = "READY";
    document.getElementById("final-response-box").textContent = "Simulated cloud environment reset successfully to initial state.";

    alert("Simulated cloud environment has been reset to initial state.");

  } catch (err) {
    alert(`Reset failed: ${err.message}`);
  }
}

/**
 * Resets all 6 timeline pipeline cards to clean default states.
 */
function resetTimeline() {
  for (let i = 1; i <= 6; i++) {
    const num = i < 10 ? `0${i}` : `${i}`;
    const card = document.getElementById(`phase-card-${num}`);
    const icon = document.getElementById(`icon-phase-${num}`);
    const tool = document.getElementById(`tool-phase-${num}`);

    if (card) {
      card.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-surface-container-high transition-all";
    }
    if (icon) {
      icon.textContent = "pending";
      icon.className = "material-symbols-outlined text-outline text-[16px]";
    }
    if (tool) {
      tool.textContent = i === 1 ? "get_all_services()" : "Pending";
    }
  }
}

/**
 * Clears previous run's execution-specific UI state to enforce multiple run isolation.
 */
function clearPreviousRunState() {
  document.getElementById("res-run-id").textContent = "Executing...";
  document.getElementById("res-status-badge").textContent = "RUNNING";
  document.getElementById("res-status-badge").className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-warning/20 text-warning font-bold text-[11px] border border-warning/30";
  document.getElementById("res-phase-badge").textContent = "INVESTIGATING";

  document.getElementById("safety-alert-banner").classList.add("hidden");
  document.getElementById("stale-safeguard-banner").classList.add("hidden");

  document.getElementById("res-cost-initial").textContent = "...";
  document.getElementById("res-cost-final").textContent = "...";
  document.getElementById("res-cost-savings").textContent = "...";

  document.getElementById("comparison-container").innerHTML = `<div class="p-4 text-center font-mono text-xs text-outline"><span class="material-symbols-outlined text-[16px] animate-spin inline-block align-middle mr-1">sync</span> Evaluating optimization impact...</div>`;
  document.getElementById("final-response-box").textContent = "Agent workflow executing...";
  document.getElementById("ai-proposed-payload").textContent = "Executing investigation...";

  resetTimeline();

  const traceContainer = document.getElementById("trace-container");
  if (traceContainer) {
    traceContainer.innerHTML = `<div class="p-3 text-center text-outline font-mono text-xs"><span class="material-symbols-outlined text-[14px] animate-spin inline-block align-middle mr-1">sync</span> Logging trace events...</div>`;
  }
  const traceCountTag = document.getElementById("trace-count-tag");
  if (traceCountTag) {
    traceCountTag.textContent = "0 Trace Events";
  }
}

/**
 * Triggers autonomous CloudAgent execution by sending request to POST /agent/run.
 * Prevents concurrent runs and validates empty inputs.
 */
async function runAgent() {
  if (isWorkflowRunning) return;

  const inputEl = document.getElementById("agent-input");
  const requestText = (inputEl.value || "").trim();

  if (!requestText) {
    alert("Please enter a natural language directive or select one of the preset scenarios.");
    inputEl.focus();
    return;
  }

  const btn = document.getElementById("btn-run-agent");
  const btnIcon = document.getElementById("run-btn-icon");
  const btnText = document.getElementById("run-btn-text");

  isWorkflowRunning = true;
  btn.disabled = true;
  btnIcon.textContent = "sync";
  btnIcon.classList.add("animate-spin");
  btnText.textContent = "RUNNING AGENT WORKFLOW...";

  // Enforce Run Isolation by clearing previous run's UI state
  clearPreviousRunState();

  try {
    const res = await fetch("/agent/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: requestText })
    });

    if (!res.ok) {
      let errText = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) errText = errJson.detail;
      } catch (e) {}
      throw new Error(errText);
    }
    
    const data = await res.json();

    // Re-fetch live services after agent run to reflect updated environment state
    await fetchServices();

    // Render structured results
    renderAgentResults(data);

  } catch (err) {
    const statusBadge = document.getElementById("res-status-badge");
    statusBadge.textContent = "FAILED";
    statusBadge.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-error/20 text-error font-bold text-[11px] border border-error/30";
    document.getElementById("res-phase-badge").textContent = "ABORTED";
    document.getElementById("final-response-box").textContent = `Agent workflow execution failed: ${err.message}`;
    alert(`Agent execution failed: ${err.message}`);
  } finally {
    isWorkflowRunning = false;
    btn.disabled = false;
    btnIcon.textContent = "rocket_launch";
    btnIcon.classList.remove("animate-spin");
    btnText.textContent = "RUN AGENT WORKFLOW";
  }
}

/**
 * Renders structured CloudAgent workflow result onto the Stitch UI.
 */
function renderAgentResults(data) {
  if (!data || typeof data !== "object") return;

  // 1. Run ID & Status Badges
  document.getElementById("res-run-id").textContent = data.run_id || "run-N/A";
  
  const statusBadge = document.getElementById("res-status-badge");
  const statusStr = (data.status || "COMPLETED").toUpperCase();
  statusBadge.textContent = statusStr;

  if (statusStr === "COMPLETED" && data.success) {
    statusBadge.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-tertiary/20 text-tertiary font-bold text-[11px] border border-tertiary/30";
  } else if (statusStr === "ITERATION_LIMIT") {
    statusBadge.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-warning/20 text-warning font-bold text-[11px] border border-warning/30";
  } else if (statusStr === "NO_ACTION") {
    statusBadge.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-high text-on-surface font-bold text-[11px] border border-outline-variant";
  } else {
    statusBadge.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-error/20 text-error font-bold text-[11px] border border-error/30";
  }

  // 2. Cost Summary
  const costSavingsEl = document.getElementById("res-cost-savings");
  if (data.cost_summary) {
    const cs = data.cost_summary;
    document.getElementById("res-cost-initial").textContent = `$${(cs.before_hourly_cost || 0).toFixed(2)}`;
    document.getElementById("res-cost-final").textContent = `$${(cs.after_hourly_cost || 0).toFixed(2)}`;

    if (cs.has_cost_change && cs.estimated_hourly_savings > 0) {
      costSavingsEl.textContent = `-$${cs.estimated_hourly_savings.toFixed(2)}`;
      costSavingsEl.title = "";
    } else if (cs.note) {
      costSavingsEl.textContent = "Unavailable";
      costSavingsEl.title = cs.note;
    } else {
      costSavingsEl.textContent = "$0.00";
      costSavingsEl.title = "No cost change";
    }
  } else {
    document.getElementById("res-cost-initial").textContent = "N/A";
    document.getElementById("res-cost-final").textContent = "N/A";
    costSavingsEl.textContent = "N/A";
  }

  // 3. Execution Trace Timeline & Phase Highlights
  const traceEntries = Array.isArray(data.execution_trace) ? data.execution_trace : [];
  updateTimelinePipeline(traceEntries, data);
  renderExecutionTrace(traceEntries);

  // 4. Dual Plane AI vs Safety Boundary
  const proposedPayloadEl = document.getElementById("ai-proposed-payload");
  const actions = Array.isArray(data.actions) ? data.actions : [];
  const failedAction = actions.find(a => a && a.success === false);
  const adaptEntry = traceEntries.find(e => e && e.phase === "adapt");

  if (actions.length > 0) {
    const lastAction = actions[actions.length - 1];
    proposedPayloadEl.textContent = `${lastAction.action || 'tool'}(service_id="${lastAction.service_id}", args=${JSON.stringify(lastAction.arguments || {})})`;
  } else if (traceEntries.length > 0) {
    const toolCallTrace = traceEntries.find(e => e && e.tool);
    if (toolCallTrace) {
      proposedPayloadEl.textContent = `${toolCallTrace.tool}(${JSON.stringify(toolCallTrace.arguments || {})})`;
    } else {
      proposedPayloadEl.textContent = "get_all_services()";
    }
  } else {
    proposedPayloadEl.textContent = "get_all_services()";
  }

  const safetyAlertBanner = document.getElementById("safety-alert-banner");
  const safetyAlertMessage = document.getElementById("safety-alert-message");
  const safetyAdaptPill = document.getElementById("safety-adapt-pill");

  if (failedAction) {
    safetyAlertBanner.classList.remove("hidden");
    const wasResolved = Boolean(data.success && actions.some(a => a && a.success));
    if (wasResolved) {
      safetyAlertMessage.innerHTML = `<span class="font-bold text-secondary">[INTERMEDIATE EVENT]</span> Action '${failedAction.action}' rejected: ${escapeHtml(failedAction.error || 'Backend guardrail')}. Agent adapted strategy successfully.`;
      safetyAdaptPill.classList.remove("hidden");
      safetyAdaptPill.textContent = "ADAPTED & COMPLETED";
      safetyAdaptPill.className = "px-2 py-0.5 rounded bg-secondary/20 text-secondary font-bold text-[10px] border border-secondary/30";
    } else {
      safetyAlertMessage.innerHTML = `<span class="font-bold text-error">[SAFETY REJECTED]</span> Action '${failedAction.action}' rejected: ${escapeHtml(failedAction.error || 'Operation rejected by backend safety boundary')}`;
      safetyAdaptPill.classList.add("hidden");
    }
  } else {
    safetyAlertBanner.classList.add("hidden");
  }

  // 5. Scenario C Timestamp Safeguard Callout
  const isScenarioC = (data.request || "").toLowerCase().includes("reduce cost if it is safe") || traceEntries.some(e => e && e.phase === "timestamp_check");
  const staleBanner = document.getElementById("stale-safeguard-banner");
  if (staleBanner) {
    if (isScenarioC) {
      staleBanner.classList.remove("hidden");
    } else {
      staleBanner.classList.add("hidden");
    }
  }

  // 6. Optimization Impact Comparison Table
  renderOptimizationImpact(data.verification || []);

  // 7. Agent Final Explanation
  document.getElementById("final-response-box").textContent = data.final_response || "Investigation completed.";
}

/**
 * Updates the 6-stage execution sequence pipeline cards cleanly based on trace events and run state.
 * Fixes ADAPT state bug and ensures cards accurately reflect NOT REQUIRED vs COMPLETED vs PENDING vs FAILED.
 */
function updateTimelinePipeline(traceEntries, data) {
  resetTimeline();

  const isFinished = data.status === "completed" || data.status === "iteration_limit" || Boolean(data.final_response);
  const phasesPresent = new Set(traceEntries.map(e => e && (e.phase || "").toLowerCase()));

  const hasAdaptation = phasesPresent.has("adapt") || traceEntries.some(e => e && e.phase === "action_failed");
  const actions = Array.isArray(data.actions) ? data.actions : [];
  const hasAction = actions.length > 0;
  const successfulAction = actions.slice().reverse().find(a => a && a.success);
  const hasVerification = Array.isArray(data.verification) && data.verification.length > 0;

  // Step 01: INVESTIGATE
  const invCard = document.getElementById("phase-card-01");
  const invIcon = document.getElementById("icon-phase-01");
  const invTool = document.getElementById("tool-phase-01");
  if (phasesPresent.has("investigate") || traceEntries.length > 0) {
    invCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-tertiary/40 bg-tertiary/5 transition-all";
    invIcon.textContent = "check_circle";
    invIcon.className = "material-symbols-outlined text-tertiary text-[16px]";
    invTool.textContent = "get_all_services()";
  }

  // Step 02: DECIDE
  const decCard = document.getElementById("phase-card-02");
  const decIcon = document.getElementById("icon-phase-02");
  const decTool = document.getElementById("tool-phase-02");
  if (data.decision && data.decision.action) {
    decCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-tertiary/40 bg-tertiary/5 transition-all";
    decIcon.textContent = "check_circle";
    decIcon.className = "material-symbols-outlined text-tertiary text-[16px]";
    decTool.textContent = data.decision.action;
  }

  // Step 03: ACT
  const actCard = document.getElementById("phase-card-03");
  const actIcon = document.getElementById("icon-phase-03");
  const actTool = document.getElementById("tool-phase-03");
  if (successfulAction) {
    actCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-tertiary/40 bg-tertiary/5 transition-all";
    actIcon.textContent = "check_circle";
    actIcon.className = "material-symbols-outlined text-tertiary text-[16px]";
    actTool.textContent = successfulAction.action;
  } else if (hasAction) {
    actCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-error/50 bg-error/5 transition-all";
    actIcon.textContent = "cancel";
    actIcon.className = "material-symbols-outlined text-error text-[16px]";
    actTool.textContent = "REJECTED";
  } else if (isFinished) {
    actCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-outline-variant/40 transition-all opacity-75";
    actIcon.textContent = "do_not_disturb_on";
    actIcon.className = "material-symbols-outlined text-outline text-[16px]";
    actTool.textContent = "NOT REQUIRED";
  }

  // Step 04: VERIFY
  const verCard = document.getElementById("phase-card-04");
  const verIcon = document.getElementById("icon-phase-04");
  const verTool = document.getElementById("tool-phase-04");
  if (hasVerification) {
    const ver = data.verification[0];
    verCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-tertiary/40 bg-tertiary/5 transition-all";
    verIcon.textContent = ver.verification_success ? "check_circle" : "warning";
    verIcon.className = `material-symbols-outlined ${ver.verification_success ? 'text-tertiary' : 'text-warning'} text-[16px]`;
    verTool.textContent = ver.verification_success ? "VERIFIED" : "UNCONFIRMED";
  } else if (isFinished) {
    verCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-outline-variant/40 transition-all opacity-75";
    verIcon.textContent = "do_not_disturb_on";
    verIcon.className = "material-symbols-outlined text-outline text-[16px]";
    verTool.textContent = "NOT REQUIRED";
  }

  // Step 05: ADAPT (Fixed ADAPT State Bug)
  const adpCard = document.getElementById("phase-card-05");
  const adpIcon = document.getElementById("icon-phase-05");
  const adpTool = document.getElementById("tool-phase-05");
  if (hasAdaptation) {
    adpCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-secondary/50 bg-secondary/5 transition-all";
    adpIcon.textContent = "published_with_changes";
    adpIcon.className = "material-symbols-outlined text-secondary text-[16px]";
    adpTool.textContent = "COMPLETED";
  } else if (isFinished) {
    adpCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-outline-variant/40 transition-all opacity-75";
    adpIcon.textContent = "do_not_disturb_on";
    adpIcon.className = "material-symbols-outlined text-outline text-[16px]";
    adpTool.textContent = "NOT REQUIRED";
  } else {
    adpCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-warning/40 transition-all";
    adpIcon.textContent = "pending";
    adpIcon.className = "material-symbols-outlined text-warning text-[16px]";
    adpTool.textContent = "PENDING";
  }

  // Step 06: FINISH
  const finCard = document.getElementById("phase-card-06");
  const finIcon = document.getElementById("icon-phase-06");
  const finTool = document.getElementById("tool-phase-06");
  if (isFinished) {
    if (data.status === "completed" || data.success) {
      finCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-tertiary/40 bg-tertiary/5 transition-all";
      finIcon.textContent = "task_alt";
      finIcon.className = "material-symbols-outlined text-tertiary text-[16px]";
      finTool.textContent = "COMPLETED";
    } else if (data.status === "iteration_limit") {
      finCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-warning/40 bg-warning/5 transition-all";
      finIcon.textContent = "warning";
      finIcon.className = "material-symbols-outlined text-warning text-[16px]";
      finTool.textContent = "ITERATION LIMIT";
    } else {
      finCard.className = "bg-surface-container rounded-lg p-3 flex flex-col justify-between border border-error/40 bg-error/5 transition-all";
      finIcon.textContent = "error";
      finIcon.className = "material-symbols-outlined text-error text-[16px]";
      finTool.textContent = "FAILED";
    }
  }

  // Update current phase header badge
  const phaseBadge = document.getElementById("res-phase-badge");
  if (phaseBadge) {
    if (hasAdaptation) {
      phaseBadge.textContent = "ADAPTED & FINISHED";
    } else if (isFinished) {
      phaseBadge.textContent = "FINISH";
    } else {
      phaseBadge.textContent = "INVESTIGATING";
    }
  }
}

/**
 * Renders the structured step-by-step trace log timeline.
 */
function renderExecutionTrace(traceEntries) {
  const traceContainer = document.getElementById("trace-container");
  const traceCountTag = document.getElementById("trace-count-tag");
  if (!traceContainer) return;

  if (!Array.isArray(traceEntries) || traceEntries.length === 0) {
    traceContainer.innerHTML = `<div class="p-3 text-center text-outline font-mono text-xs">No execution trace events logged.</div>`;
    if (traceCountTag) traceCountTag.textContent = "0 Trace Events";
    return;
  }

  const validEntries = traceEntries.filter(e => e && typeof e === "object");
  if (traceCountTag) traceCountTag.textContent = `${validEntries.length} Trace Events`;

  traceContainer.innerHTML = validEntries.map((entry, idx) => {
    const phase = (entry.phase || "info").toLowerCase();
    let badgeColor = "bg-surface-container-high text-on-surface-variant border-surface-container-high";
    let icon = "info";

    if (phase === "investigate") {
      badgeColor = "bg-primary/10 text-primary border-primary/30";
      icon = "search";
    } else if (phase === "act") {
      badgeColor = "bg-primary-container/20 text-primary border-primary/40";
      icon = "bolt";
    } else if (phase === "action_failed") {
      badgeColor = "bg-error/20 text-error border-error/40";
      icon = "cancel";
    } else if (phase === "adapt") {
      badgeColor = "bg-secondary-container/30 text-secondary border-secondary/40";
      icon = "published_with_changes";
    } else if (phase === "verify") {
      badgeColor = "bg-tertiary/15 text-tertiary border-tertiary/30";
      icon = "check_circle";
    } else if (phase === "finish") {
      badgeColor = "bg-tertiary/20 text-tertiary border-tertiary/40";
      icon = "task_alt";
    }

    const stepNum = entry.step || (idx + 1);
    const phaseLabel = (entry.phase || "trace").toUpperCase();
    const reasonText = escapeHtml(entry.reason || entry.info || entry.error || "Executing workflow step");
    
    let metaDetails = [];
    if (entry.tool) {
      let toolStr = `Tool: ${escapeHtml(entry.tool)}`;
      if (entry.arguments && Object.keys(entry.arguments).length > 0) {
        toolStr += ` (${escapeHtml(JSON.stringify(entry.arguments))})`;
      }
      metaDetails.push(toolStr);
    }
    if (entry.error && entry.phase !== "action_failed") {
      metaDetails.push(`Error: ${escapeHtml(entry.error)}`);
    }

    return `
      <div class="p-2.5 rounded bg-surface-container-lowest border border-surface-container-high flex flex-col gap-1 font-mono text-xs">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <span class="text-outline text-[10px]">#${stepNum}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor} flex items-center gap-1">
              <span class="material-symbols-outlined text-[13px]">${icon}</span>
              ${phaseLabel}
            </span>
          </div>
          ${entry.verified !== undefined ? `
            <span class="text-[10px] ${entry.verified ? 'text-tertiary font-bold' : 'text-warning'}">
              ${entry.verified ? '✓ VERIFIED' : 'UNCONFIRMED'}
            </span>
          ` : ''}
        </div>
        <div class="text-on-surface text-xs mt-0.5">${reasonText}</div>
        ${metaDetails.length > 0 ? `
          <div class="text-[11px] text-outline bg-surface-container/50 px-2 py-1 rounded border border-surface-container-high mt-1">
            ${metaDetails.join(' | ')}
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
}

/**
 * Renders Before vs After Optimization Impact Comparison Table.
 */
function renderOptimizationImpact(verifications) {
  const container = document.getElementById("comparison-container");
  
  if (!Array.isArray(verifications) || verifications.length === 0) {
    container.innerHTML = `<div class="p-4 text-center font-mono text-xs text-outline">No infrastructure changes executed for this request.</div>`;
    return;
  }

  container.innerHTML = `
    <table class="comp-table">
      <thead>
        <tr>
          <th>Service</th>
          <th>Metric</th>
          <th>BEFORE Action</th>
          <th>AFTER Action</th>
          <th>Verification</th>
        </tr>
      </thead>
      <tbody>
        ${verifications.map(v => {
          const before = v.before || {};
          const after = v.after || {};
          const isSuccess = v.verification_success;

          const instBefore = before.instances !== undefined ? before.instances + ' nodes' : 'N/A';
          const instAfter = after.instances !== undefined ? after.instances + ' nodes' : 'N/A';
          const instChange = (before.instances !== undefined && after.instances !== undefined) ? 
            (after.instances === before.instances ? ' (Unchanged)' : ` (${after.instances - before.instances > 0 ? '+' : ''}${after.instances - before.instances})`) : '';

          const costBefore = before.cost_per_hour !== undefined ? '$' + (before.cost_per_hour || 0).toFixed(2) + '/hr' : 'N/A';
          const costAfter = after.cost_per_hour !== undefined ? '$' + (after.cost_per_hour || 0).toFixed(2) + '/hr' : 'N/A';

          return `
            <tr>
              <td><strong class="text-on-surface font-bold">${escapeHtml(v.service_id)}</strong></td>
              <td class="text-outline">Instances</td>
              <td class="text-on-surface-variant">${instBefore}</td>
              <td><strong class="text-tertiary font-bold">${instAfter}</strong> <span class="text-[10px] text-outline font-normal">${instChange}</span></td>
              <td>
                <span class="px-2 py-0.5 rounded ${isSuccess ? 'bg-tertiary/15 text-tertiary' : 'bg-error/15 text-error'} font-mono text-[10px] font-bold">
                  ${isSuccess ? '✅ VERIFIED' : '❌ UNCONFIRMED'}
                </span>
              </td>
            </tr>
            <tr>
              <td></td>
              <td class="text-outline">Cost/Hour</td>
              <td class="text-on-surface-variant">${costBefore}</td>
              <td><strong class="text-tertiary font-bold">${costAfter}</strong></td>
              <td></td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

function escapeHtml(str) {
  if (typeof str !== "string") return str;
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
