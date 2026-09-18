/**
 * Cloud Bill Agent Dashboard JavaScript Application.
 * Communicates with FastAPI backend (/services, /agent/run, /demo/reset).
 */

const SCENARIOS = {
  A: "Review current services and reduce unnecessary cost without breaking latency or availability requirements.",
  B: "Orders traffic is increasing. Keep the service within its latency target.",
  C: "Reduce cost if it is safe.",
  D: "Scale the payment service only if the current state requires it."
};

// Initial load
document.addEventListener("DOMContentLoaded", () => {
  fetchServices();
});

/**
 * Fetches current cloud services from GET /services and populates service cards.
 */
async function fetchServices() {
  const container = document.getElementById("services-container");
  try {
    const res = await fetch("/services");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const services = await res.json();

    if (!Array.isArray(services) || services.length === 0) {
      container.innerHTML = `<div class="loading-spinner">No services found.</div>`;
      return;
    }

    container.innerHTML = services.map(service => `
      <div class="service-card">
        <div class="service-card-header">
          <span class="service-name">${escapeHtml(service.service_id)}</span>
          <span class="service-cost">$${(service.cost_per_hour || 0).toFixed(2)}/hr</span>
        </div>
        <div class="service-metrics-grid">
          <div class="metric-box">
            <span class="metric-label">Instances</span>
            <div class="metric-val">${service.instances} (${service.min_instances}-${service.max_instances})</div>
          </div>
          <div class="metric-box">
            <span class="metric-label">CPU %</span>
            <div class="metric-val">${service.cpu_percent}%</div>
          </div>
          <div class="metric-box">
            <span class="metric-label">Memory %</span>
            <div class="metric-val">${service.memory_percent}%</div>
          </div>
          <div class="metric-box">
            <span class="metric-label">Requests/min</span>
            <div class="metric-val">${service.requests_per_minute}</div>
          </div>
          <div class="metric-box">
            <span class="metric-label">Latency</span>
            <div class="metric-val">${service.latency_ms} ms</div>
          </div>
          <div class="metric-box">
            <span class="metric-label">Health</span>
            <div class="metric-val ${service.healthy ? 'highlight-green' : 'text-danger'}">
              ${service.healthy ? 'Healthy' : 'Unhealthy'}
            </div>
          </div>
        </div>
      </div>
    `).join("");

  } catch (err) {
    container.innerHTML = `<div class="alert-box">Failed to load services: ${escapeHtml(err.message)}</div>`;
  }
}

/**
 * Populates natural language request input with chosen preset scenario text.
 */
function selectScenario(key) {
  if (SCENARIOS[key]) {
    document.getElementById("agent-input").value = SCENARIOS[key];
  }
}

/**
 * Resets simulated cloud environment after explicit user browser confirmation.
 */
async function resetDemoEnvironment() {
  const confirmed = confirm("Reset the simulated cloud environment to its initial state?");
  if (!confirmed) return;

  try {
    const res = await fetch("/demo/reset", { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    await fetchServices();
    
    // Hide previous results
    document.getElementById("results-placeholder").classList.remove("hidden");
    document.getElementById("results-container").classList.add("hidden");
    alert("Simulated cloud environment has been reset to initial state.");
  } catch (err) {
    alert(`Reset failed: ${err.message}`);
  }
}

/**
 * Sends user natural language request to POST /agent/run and renders structured workflow execution results.
 */
async function runAgent() {
  const inputEl = document.getElementById("agent-input");
  const requestText = inputEl.value.trim() || inputEl.placeholder;

  const btn = document.getElementById("btn-run-agent");
  const btnIcon = document.getElementById("run-btn-icon");
  const btnText = document.getElementById("run-btn-text");

  // Show results container immediately with RUNNING status while request is executing
  document.getElementById("results-placeholder").classList.add("hidden");
  document.getElementById("results-container").classList.remove("hidden");
  
  const statusBadge = document.getElementById("res-status-badge");
  statusBadge.textContent = "RUNNING";
  statusBadge.className = "badge badge-warning";
  
  document.getElementById("res-run-id").textContent = "Executing...";
  document.getElementById("res-cost-initial").textContent = "...";
  document.getElementById("res-cost-final").textContent = "...";
  document.getElementById("res-cost-savings").textContent = "...";
  document.getElementById("alert-container").classList.add("hidden");

  document.getElementById("trace-container").innerHTML = `
    <div class="trace-item">
      <span class="trace-phase phase-investigate">RUNNING</span>
      <div class="trace-body">
        <div class="trace-reason">Agent is actively querying cloud tools and Hugging Face model...</div>
      </div>
    </div>
  `;

  // Set loading UI state
  btn.disabled = true;
  btnIcon.textContent = "⏳";
  btnText.textContent = "RUNNING AGENT WORKFLOW...";

  try {
    const res = await fetch("/agent/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: requestText })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Re-fetch services after agent run
    await fetchServices();

    // Display Results
    renderAgentResults(data);

  } catch (err) {
    statusBadge.textContent = "FAILED";
    statusBadge.className = "badge badge-danger";
    alert(`Agent execution failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btnIcon.textContent = "🚀";
    btnText.textContent = "RUN AGENT WORKFLOW";
  }
}

/**
 * Renders the structured CloudAgent result onto the dashboard.
 */
function renderAgentResults(data) {
  document.getElementById("results-placeholder").classList.add("hidden");
  document.getElementById("results-container").classList.remove("hidden");

  // 1. Run Summary
  document.getElementById("res-run-id").textContent = data.run_id || "run-N/A";
  
  const statusBadge = document.getElementById("res-status-badge");
  const statusStr = (data.status || "COMPLETED").toUpperCase();
  statusBadge.textContent = statusStr;
  
  if (statusStr === "COMPLETED" && data.success) {
    statusBadge.className = "badge badge-success";
  } else if (statusStr === "ITERATION_LIMIT") {
    statusBadge.className = "badge badge-warning";
  } else {
    statusBadge.className = "badge badge-danger";
  }

  // Cost Summary
  const costSavingsEl = document.getElementById("res-cost-savings");
  if (data.cost_summary) {
    const cs = data.cost_summary;
    document.getElementById("res-cost-initial").textContent = `$${cs.before_hourly_cost.toFixed(2)}/hr`;
    document.getElementById("res-cost-final").textContent = `$${cs.after_hourly_cost.toFixed(2)}/hr`;
    
    if (cs.has_cost_change && cs.estimated_hourly_savings > 0) {
      costSavingsEl.textContent = `$${cs.estimated_hourly_savings.toFixed(2)}/hr`;
      costSavingsEl.title = "";
    } else if (cs.note) {
      costSavingsEl.textContent = "Cost impact unavailable";
      costSavingsEl.title = cs.note;
    } else {
      costSavingsEl.textContent = "$0.00/hr";
    }
  } else {
    document.getElementById("res-cost-initial").textContent = "N/A";
    document.getElementById("res-cost-final").textContent = "N/A";
    costSavingsEl.textContent = "N/A";
  }

  // 2. Trace Header Update
  const traceEntries = data.execution_trace || [];
  const hasAdaptation = traceEntries.some(e => e.phase === "adapt" || e.phase === "action_failed");
  const traceHeaderTag = document.getElementById("trace-header-tag");
  if (traceHeaderTag) {
    if (hasAdaptation) {
      traceHeaderTag.textContent = "Investigate → Decide → Act → Verify → Adapt → Finish";
    } else {
      traceHeaderTag.textContent = "Investigate → Decide → Act → Verify → Finish";
    }
  }

  // 3. Alert Banner for Safety Rejections or Failures
  const alertContainer = document.getElementById("alert-container");
  const failedAction = (data.actions || []).find(a => a.success === false);
  if (failedAction) {
    alertContainer.classList.remove("hidden");
    alertContainer.innerHTML = `
      <strong>SAFETY REJECTED / ACTION FAILED:</strong>
      <div>Backend rejected tool '${escapeHtml(failedAction.action)}': ${escapeHtml(failedAction.error || 'Operation unsafe')}</div>
    `;
  } else {
    alertContainer.classList.add("hidden");
  }

  // 4. Execution Trace Timeline
  const traceContainer = document.getElementById("trace-container");
  
  if (traceEntries.length === 0) {
    traceContainer.innerHTML = `<p class="text-muted">No trace records generated.</p>`;
  } else {
    traceContainer.innerHTML = traceEntries.map(entry => {
      const phase = (entry.phase || "investigate").toLowerCase();
      let phaseClass = `phase-${phase}`;
      if (phase === "action_failed") phaseClass = "phase-failed";

      let metaText = "";
      if (entry.tool) metaText += `Tool: ${entry.tool}`;
      if (entry.arguments) metaText += ` (${JSON.stringify(entry.arguments)})`;
      if (entry.error) metaText += ` | Error: ${entry.error}`;
      if (entry.info) metaText += ` ${entry.info}`;

      return `
        <div class="trace-item">
          <span class="trace-phase ${phaseClass}">${escapeHtml((entry.phase || "trace").toUpperCase())}</span>
          <div class="trace-body">
            <div class="trace-reason">${escapeHtml(entry.reason || entry.info || "Executing phase step")}</div>
            ${metaText ? `<div class="trace-meta">${escapeHtml(metaText)}</div>` : ""}
          </div>
        </div>
      `;
    }).join("");
  }

  // 5. Before / After Comparison Matrix
  const compContainer = document.getElementById("comparison-container");
  const verifications = data.verification || [];

  if (verifications.length === 0) {
    compContainer.innerHTML = `<p class="text-muted" style="padding:1rem;">No infrastructure changes were required.</p>`;
  } else {
    compContainer.innerHTML = `
      <table class="comp-table">
        <thead>
          <tr>
            <th>Service</th>
            <th>Metric</th>
            <th>BEFORE Action</th>
            <th>AFTER Action</th>
            <th>Verification Status</th>
          </tr>
        </thead>
        <tbody>
          ${verifications.map(v => {
            const before = v.before || {};
            const after = v.after || {};
            const statusLabel = v.verification_success ? "✅ VERIFIED" : "❌ UNCONFIRMED";
            return `
              <tr>
                <td><strong>${escapeHtml(v.service_id)}</strong></td>
                <td>Instances</td>
                <td>${before.instances !== undefined ? before.instances : 'N/A'}</td>
                <td><strong>${after.instances !== undefined ? after.instances : 'N/A'}</strong></td>
                <td><span class="badge ${v.verification_success ? 'badge-success' : 'badge-danger'}">${statusLabel}</span></td>
              </tr>
              <tr>
                <td></td>
                <td>Cost/Hour</td>
                <td>$${(before.cost_per_hour || 0).toFixed(2)}/hr</td>
                <td>$${(after.cost_per_hour || 0).toFixed(2)}/hr</td>
                <td></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  }

  // 6. Final Response Explanation
  document.getElementById("final-response-box").textContent = data.final_response || "No final explanation provided.";
}

function escapeHtml(str) {
  if (typeof str !== "string") return str;
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
