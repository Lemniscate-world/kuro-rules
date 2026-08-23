const state = {
  data: null,
  activeOrg: "all",
  searchTerm: "",
};

function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusLabel(status) {
  switch (status) {
    case "steady":
      return "Steady";
    case "attention":
      return "Attention";
    case "unsynced":
      return "Unsynced";
    case "missing":
      return "Missing";
    default:
      return status;
  }
}

function severityLabel(severity) {
  switch (severity) {
    case "high":
      return "Critical";
    case "medium":
      return "Watch";
    default:
      return "Info";
  }
}

function renderMetrics(summary) {
  const metrics = [
    ["Tracked", summary.trackedProjects],
    ["Live", summary.liveProjects],
    ["Dirty", summary.dirtyProjects],
    ["Orgs", summary.organizationCount],
    ["Memory docs", summary.knowledgeEntries],
    ["Post-mortems", summary.postMortems],
  ];

  document.getElementById("metric-grid").innerHTML = metrics
    .map(
      ([label, value]) => `
        <article class="metric-card">
          <div class="metric-value">${escapeHtml(value)}</div>
          <div class="metric-label">${escapeHtml(label)}</div>
        </article>
      `
    )
    .join("");
}

function renderAlerts(alerts) {
  const container = document.getElementById("alerts");
  if (!alerts.length) {
    container.innerHTML = `
      <article class="alert-card low">
        <div class="alert-badge">Clear</div>
        <h3>No urgent drift detected.</h3>
        <p>The current snapshot did not find missing tracked repos, unsynced memory, or sync gaps worth flagging.</p>
      </article>
    `;
    return;
  }

  container.innerHTML = alerts
    .map(
      (alert) => `
        <article class="alert-card ${escapeHtml(alert.severity)}">
          <div class="alert-badge">${escapeHtml(severityLabel(alert.severity))}</div>
          <h3>${escapeHtml(alert.title)}</h3>
          <p>${escapeHtml(alert.detail)}</p>
        </article>
      `
    )
    .join("");
}

function renderOrgFilters(organizations) {
  const container = document.getElementById("org-filters");
  const chips = [
    { id: "all", label: "All orgs" },
    ...organizations.map((org) => ({ id: org.name, label: `${org.name} (${org.projectCount})` })),
  ];

  container.innerHTML = chips
    .map(
      (chip) => `
        <button class="chip ${state.activeOrg === chip.id ? "active" : ""}" data-org="${escapeHtml(chip.id)}">
          ${escapeHtml(chip.label)}
        </button>
      `
    )
    .join("");

  container.querySelectorAll(".chip").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeOrg = button.dataset.org;
      renderOrgFilters(organizations);
      renderProjects();
    });
  });
}

function projectMatches(project) {
  const term = state.searchTerm.trim().toLowerCase();
  if (state.activeOrg !== "all" && project.organization !== state.activeOrg) {
    return false;
  }
  if (!term) {
    return true;
  }
  const haystack = [
    project.name,
    project.organization,
    project.repository,
    project.branch,
    project.lastCommitMessage,
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(term);
}

function renderProjects() {
  const data = state.data;
  const container = document.getElementById("project-grid");
  const projects = data.trackedProjects.filter((project) => project.exists && projectMatches(project));

  if (!projects.length) {
    container.innerHTML = `
      <article class="project-card empty">
        <h3>No projects match the current filter.</h3>
        <p>Try another organization or a broader search term.</p>
      </article>
    `;
    return;
  }

  container.innerHTML = projects
    .map((project) => {
      const dirty = project.dirtyCount ? `${project.dirtyCount} dirty` : "clean";
      const sync = project.hasAgents ? "rules present" : "rules missing";
      const branch = project.branch || "detached";
      const remote = project.remoteUrl || "No remote";
      const drift =
        project.ahead || project.behind ? `${project.ahead} ahead / ${project.behind} behind` : "upstream aligned";

      return `
        <article class="project-card ${escapeHtml(project.status)}">
          <div class="project-topline">
            <span class="status-pill ${escapeHtml(project.status)}">${escapeHtml(statusLabel(project.status))}</span>
            <span class="org-label">${escapeHtml(project.organization)}</span>
          </div>
          <h3>${escapeHtml(project.name)}</h3>
          <p class="project-subtitle">${escapeHtml(project.repository)}</p>
          <div class="project-facts">
            <span>${escapeHtml(branch)}</span>
            <span>${escapeHtml(dirty)}</span>
            <span>${escapeHtml(sync)}</span>
            <span>${escapeHtml(drift)}</span>
          </div>
          <p class="project-commit">${escapeHtml(project.lastCommitMessage || "No commit metadata found")}</p>
          <div class="project-footer">
            <span>${escapeHtml(formatDate(project.lastCommitAt))}</span>
            <code title="${escapeHtml(remote)}">${escapeHtml(remote)}</code>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderKnowledge(knowledgeBase) {
  const counts = knowledgeBase.counts || {};
  document.getElementById("knowledge-counts").textContent =
    `${counts["post-mortem"] || 0} post-mortems | ${counts["mom-test"] || 0} Mom Test docs | ${counts.note || 0} notes`;

  const container = document.getElementById("knowledge-grid");
  const entries = knowledgeBase.entries || [];

  container.innerHTML = entries
    .map(
      (entry) => `
        <article class="memory-card">
          <div class="memory-topline">
            <span class="memory-kind">${escapeHtml(entry.kind)}</span>
            <span>${escapeHtml(formatDate(entry.updatedAt))}</span>
          </div>
          <h3>${escapeHtml(entry.title)}</h3>
          <p>${escapeHtml(entry.summary)}</p>
          <code>${escapeHtml(entry.path)}</code>
        </article>
      `
    )
    .join("");
}

function renderRules(ruleHighlights) {
  const container = document.getElementById("rule-grid");
  container.innerHTML = ruleHighlights
    .map(
      (rule) => `
        <article class="rule-card">
          <div class="rule-number">Rule ${escapeHtml(rule.number)}</div>
          <h3>${escapeHtml(rule.title)}</h3>
          <p>${escapeHtml(rule.summary)}</p>
          <div class="rule-line">AGENTS.md line ${escapeHtml(rule.lineNumber)}</div>
        </article>
      `
    )
    .join("");
}

function renderSync(syncLog, kuroRulesRepo) {
  const syncCard = document.getElementById("sync-card");
  const latestEntries = (syncLog.entries || []).slice(0, 8);

  syncCard.innerHTML = `
    <div class="sync-topline">
      <span class="status-pill steady">Latest sync</span>
      <span>${escapeHtml(syncLog.lastRun || "Unknown")}</span>
    </div>
    <h3>${escapeHtml(syncLog.repoCount || 0)} repos touched, ${escapeHtml(syncLog.fileCount || 0)} files propagated</h3>
    <div class="sync-list">
      ${latestEntries
        .map(
          (entry) => `
            <div class="sync-item">
              <strong>${escapeHtml(entry.project)}</strong>
              <span>${escapeHtml(entry.files.join(", "))}</span>
            </div>
          `
        )
        .join("")}
    </div>
  `;

  const dirty = kuroRulesRepo.dirtyCount ? `${kuroRulesRepo.dirtyCount} dirty files` : "clean worktree";
  document.getElementById("kuro-card").innerHTML = `
    <div class="sync-topline">
      <span class="status-pill ${escapeHtml(kuroRulesRepo.status)}">${escapeHtml(statusLabel(kuroRulesRepo.status))}</span>
      <span>${escapeHtml(kuroRulesRepo.branch || "detached")}</span>
    </div>
    <h3>${escapeHtml(dirty)}</h3>
    <p>${escapeHtml(kuroRulesRepo.lastCommitMessage || "No commit metadata found")}</p>
    <div class="sync-meta">
      <span>${escapeHtml(formatDate(kuroRulesRepo.lastCommitAt))}</span>
      <code>${escapeHtml(kuroRulesRepo.path)}</code>
    </div>
  `;
}

function bindSearch() {
  const input = document.getElementById("project-search");
  input.addEventListener("input", (event) => {
    state.searchTerm = event.target.value;
    renderProjects();
  });
}

async function loadData() {
  // Source live (API Kuro) puis fallback snapshot statique
  try {
    const live = await fetch(`/api/dashboard?ts=${Date.now()}`);
    if (live.ok) return await live.json();
  } catch (_) {}
  const response = await fetch(`dashboard-data.json?ts=${Date.now()}`);
  return await response.json();
}

async function load() {
  try {
    const data = await loadData();
    state.data = data;

    document.getElementById("generated-at").textContent = `Snapshot ${formatDate(data.generatedAt)}`;
    document.getElementById("workspace-root").textContent = data.workspaceRoot;

    renderMetrics(data.summary);
    renderAlerts(data.alerts || []);
    renderOrgFilters(data.organizations || []);
    renderProjects();
    renderKnowledge(data.knowledgeBase || { entries: [], counts: {} });
    renderRules(data.ruleHighlights || []);
    renderSync(data.syncLog || {}, data.kuroRulesRepo || {});
    if (!window.__searchBound) {
      bindSearch();
      window.__searchBound = true;
    }
    notifyNewAlerts((data.alerts || []).length);
  } catch (error) {
    document.body.innerHTML = `
      <main class="page-shell">
        <section class="panel">
          <div class="section-label">Load error</div>
          <h1>Dashboard snapshot unavailable</h1>
          <p>${escapeHtml(error.message)}</p>
          <p>Run <code>python .\\dashboard\\generate_dashboard.py</code> or <code>.\\run-dashboard.ps1</code> from <code>kuro-rules</code>.</p>
        </section>
      </main>
    `;
  }
}

function notifyNewAlerts(count) {
  const last = window.__lastAlertCount;
  window.__lastAlertCount = count;
  if (last === undefined || count <= last) return;
  if (!("Notification" in window)) return;
  if (Notification.permission === "granted") {
    new Notification("Kuro Desk", { body: `${count - last} nouvelle(s) alerte(s) détectée(s)` });
  } else if (Notification.permission !== "denied") {
    Notification.requestPermission();
  }
}

async function loadRobotPanel() {
  let el = document.getElementById("kuro-robot");
  if (!el) {
    el = document.createElement("section");
    el.id = "kuro-robot";
    el.className = "panel";
    el.style.cssText = "margin:0 0 1rem;padding:.8rem 1rem;border:1px solid var(--border);border-radius:8px;background:var(--bg-raise);font-family:var(--font-mono,monospace);font-size:.72rem";
    document.body.prepend(el);
  }
  try {
    const r = await fetch(`/api/robot?ts=${Date.now()}`);
    const d = await r.json();
    const dot = d.ci_overall === "green" ? "🟢" : d.ci_overall === "red" ? "🔴" : "⚪";
    const engine = d.llm_engine || "déterministe";
    const hb = d.daemon && d.daemon.timestamp ? `daemon ${d.daemon.timestamp.slice(0, 10)}` : "daemon inconnu";
    const acts = (d.actions_tail || []).filter(a => !a.startsWith("scan")).slice(-3);
    el.innerHTML =
      `<div style="margin-bottom:.35rem"><strong>${dot} Robot Kuro</strong> · moteur: ${engine} · ${hb}</div>` +
      (acts.length
        ? `<ul style="margin:0;padding-left:1.1rem;color:var(--muted)">${acts.map(a => `<li>${a.replace(/</g, "&lt;")}</li>`).join("")}</ul>`
        : `<div style="color:var(--muted)">aucune auto-action récente</div>`);
  } catch (_) {
    el.innerHTML = "<em>Robot Kuro indisponible</em>";
  }
}

function finCell(label, value, tone) {
  return `<div style="flex:1 1 92px;border:1px solid var(--border);border-radius:6px;padding:.4rem .5rem">
      <div style="color:var(--muted);font-size:.6rem;text-transform:uppercase;letter-spacing:.05em">${label}</div>
      <div style="font-weight:600;font-size:.95rem;color:${tone}">${escapeHtml(value)}</div>
    </div>`;
}

function finTone(status) {
  if (status === "critical") return "#f85149";
  if (status === "warning" || status === "incomplete") return "#58a6ff";
  if (status === "healthy") return "#3fb950";
  return "var(--muted)";
}

async function loadFinancePanel() {
  let el = document.getElementById("kuro-finance");
  if (!el) {
    el = document.createElement("section");
    el.id = "kuro-finance";
    el.className = "panel";
    el.style.cssText = "margin:0 0 1rem;padding:.8rem 1rem;border:1px solid var(--border);border-radius:8px;background:var(--bg-raise)";
    const robot = document.getElementById("kuro-robot");
    if (robot && robot.parentElement) {
      robot.insertAdjacentElement("afterend", el);
    } else {
      document.body.prepend(el);
    }
  }
  try {
    const [finRes, metRes] = await Promise.all([
      fetch(`/api/finance?ts=${Date.now()}`),
      fetch(`/api/metrics?ts=${Date.now()}`),
    ]);
    const f = await finRes.json();
    const m = await metRes.json();
    if (f.status === "unconfigured") {
      el.innerHTML =
        `<div><strong>Finance &amp; exécution</strong></div>` +
        `<em style="color:var(--muted)">Copiez finances.local.example.json vers finances.local.json (gitigné, R111).</em>`;
      return;
    }
    const trend = f.trend && f.trend.runway_delta_months != null ? f.trend.runway_delta_months : null;
    const arrow = trend == null ? "" : trend >= 0.05 ? " ▲+" + trend.toFixed(1) : trend <= -0.05 ? " ▼" + trend.toFixed(1) : "";
    const ue = f.unit_economics || { configured: false };
    const avg = m.averages || {};
    const pivots = (m.pivot_candidates || [])
      .slice(0, 3)
      .map((p) => `${p.name} · ${p.days_inactive} j`)
      .join(", ");
    el.innerHTML =
      `<div style="display:flex;justify-content:space-between;margin-bottom:.4rem">` +
      `<strong>Finance &amp; exécution</strong>` +
      `<span style="color:var(--muted);font-size:.65rem">100% local · R111 · ${escapeHtml(f.currency || "")}</span></div>` +
      `<div style="display:flex;gap:.5rem;flex-wrap:wrap;font-family:var(--font-mono,monospace);font-size:.72rem">` +
      finCell("Runway", (f.runway_label || "?") + arrow, finTone(f.status)) +
      finCell("Burn/mois", (f.burn_rate_monthly ?? "?"), "inherit") +
      finCell("MRR", (f.mrr_monthly ?? "?"), "inherit") +
      finCell("CAC", ue.configured ? (ue.cac ?? "—") : "—", "inherit") +
      finCell("LTV", ue.configured ? (ue.ltv ?? "—") : "—", "#3fb950") +
      finCell("LTV:CAC", ue.configured ? (ue.ltv_cac_ratio ?? "—") : "—", finTone(ue.configured ? ue.status : null)) +
      finCell("Lead time moy.", avg.lead_time_days != null ? avg.lead_time_days + " j" : "—", "#58a6ff") +
      finCell("Vélocité", (avg.velocity_per_week ?? "—") + " c/sem", "inherit") +
      finCell("CI en échec", avg.ci_failure_rate != null ? Math.round(avg.ci_failure_rate * 100) + "%" : "—",
        avg.ci_failure_rate > 0.15 ? "#f85149" : "inherit") +
      `</div>` +
      (pivots ? `<div style="margin-top:.4rem;color:#f85149;font-size:.7rem">Pivots possibles : ${escapeHtml(pivots)}</div>` : "");
  } catch (_) {
    el.innerHTML =
      `<div><strong>Finance &amp; exécution</strong> <em style="color:var(--muted)">— API Kuro locale indisponible</em></div>`;
  }
}

load();
setInterval(load, 60000);
setInterval(loadRobotPanel, 60000);
setInterval(loadFinancePanel, 60000);
loadRobotPanel();
loadFinancePanel();
