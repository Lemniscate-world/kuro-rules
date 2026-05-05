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

async function load() {
  try {
    const response = await fetch(`dashboard-data.json?ts=${Date.now()}`);
    const data = await response.json();
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
    bindSearch();
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

load();
