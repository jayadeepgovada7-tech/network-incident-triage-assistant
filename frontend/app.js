const alertsBox = document.getElementById("alerts");
const alertCount = document.getElementById("alert-count");
const feedEl = document.getElementById("feed");
const feedEmpty = document.getElementById("feed-empty");
const btnFibre = document.getElementById("btn-fibre");
const btnUnknown = document.getElementById("btn-unknown");
const btnAuth = document.getElementById("btn-auth");
const btnTwo = document.getElementById("btn-two");
const btnLive = document.getElementById("btn-live");
const btnClear = document.getElementById("btn-clear");
const btnRun = document.getElementById("btn-run");
const themeToggle = document.getElementById("theme-toggle");
const themeLabel = document.getElementById("theme-label");
const scenarioButtons = [btnFibre, btnUnknown, btnAuth, btnTwo, btnLive].filter(Boolean);

let loadedAlerts = [];
let liveTimer = null;
let busy = false;
let inboxVersion = -1;
let autoTriageTimer = null;

if (btnFibre) btnFibre.onclick = () => playScenario("fibre_cut", btnFibre);
if (btnUnknown) btnUnknown.onclick = () => playScenario("unknown_fault", btnUnknown);
if (btnAuth) btnAuth.onclick = () => playScenario("auth_noise", btnAuth);
if (btnTwo) btnTwo.onclick = () => playScenario("two_sites", btnTwo);
if (btnLive) btnLive.onclick = toggleLive;
if (btnClear) btnClear.onclick = clearAll;
if (btnRun) btnRun.onclick = runTriage;
if (themeToggle) themeToggle.onclick = toggleTheme;
if (alertsBox) {
  alertsBox.addEventListener("input", onComposerChange);
  alertsBox.addEventListener("paste", () => setTimeout(onComposerChange, 0));
}

initTheme();
pingStatus();
tickClock();
setInterval(tickClock, 1000);
setInterval(pollInbox, 1000);

function tickClock() {
  const el = document.getElementById("clock");
  if (el) el.textContent = new Date().toLocaleTimeString();
}

function initTheme() {
  applyTheme(localStorage.getItem("ps07-theme") || "dark");
}

function toggleTheme() {
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("ps07-theme", theme);
  if (themeLabel) themeLabel.textContent = theme === "dark" ? "Dark" : "Light";
}

async function pingStatus() {
  try {
    const data = await (await fetch("/api/status")).json();
    const backend = document.getElementById("chip-backend");
    if (backend) {
      backend.classList.add("ok");
      backend.innerHTML = '<i class="dot"></i> backend online';
    }
    const model = document.getElementById("chip-model");
    if (model) model.textContent = "chat " + (data.model || "gemini");
    const books = document.getElementById("chip-runbooks");
    if (books) books.textContent = (data.runbooks || 0) + " runbooks indexed";
  } catch (err) {
    const backend = document.getElementById("chip-backend");
    if (backend) backend.innerHTML = '<i class="dot"></i> backend offline';
  }
}

async function pollInbox() {
  try {
    const box = await (await fetch("/api/inbox")).json();
    if (box.version === inboxVersion) return;
    inboxVersion = box.version;
    if (!box.alerts || !box.alerts.length) return;
    loadedAlerts = box.alerts;
    if (alertsBox) alertsBox.value = formatAlerts(loadedAlerts);
    renderFeed(loadedAlerts, true);
    if (autoTriageTimer) clearTimeout(autoTriageTimer);
    autoTriageTimer = setTimeout(runTriage, 800);
  } catch (err) {
    /* inbox not ready yet */
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatAlerts(alerts) {
  return (alerts || [])
    .map((a) => {
      const t = (a.ts || "").slice(11, 19) || "--:--:--";
      const sev = (a.severity || "alert").toUpperCase();
      const type = (a.type || "unknown").replaceAll("_", " ");
      return "[" + t + "] " + sev + ": " + type + " - " + (a.device || "?") +
        (a.iface ? " " + a.iface : "");
    })
    .join("\n");
}

function setActive(btn) {
  scenarioButtons.forEach((b) => b && b.classList.remove("active"));
  if (btn) btn.classList.add("active");
}

function renderFeed(alerts, animateLast) {
  if (!feedEl) return;
  feedEl.innerHTML = "";
  if (!alerts.length) {
    if (feedEmpty) {
      feedEmpty.style.display = "block";
      feedEl.appendChild(feedEmpty);
    }
    if (alertCount) alertCount.textContent = "0 alerts";
    return;
  }
  if (feedEmpty) feedEmpty.style.display = "none";
  alerts.forEach((a) => {
    const card = document.createElement("div");
    const sev = (a.severity || "info").toLowerCase();
    card.className = "alert-card " + sev;
    const t = (a.ts || "").slice(11, 19) || "--:--:--";
    card.innerHTML =
      '<div class="t">' + esc(t) + "</div><div>" +
      "<strong>" + esc(sev) + "</strong>" +
      esc((a.type || "").replaceAll("_", " ")) +
      '<div class="dev">' + esc(a.device || "") + (a.iface ? " " + esc(a.iface) : "") + "</div></div>";
    feedEl.appendChild(card);
  });
  feedEl.scrollTop = feedEl.scrollHeight;
  if (alertCount) alertCount.textContent = alerts.length + " alerts";
}

function looksLikeJson(raw) {
  const t = raw.trim();
  return t.startsWith("{") || t.startsWith("[{") || t.startsWith("[\n{") || t.startsWith("[ {");
}

function looksLikeLog(raw) {
  return /\[\d{1,2}:\d{2}:\d{2}\]/.test(raw);
}

function parseLogLines(raw) {
  const physical = raw.split(/\r?\n/);
  const logical = [];
  physical.forEach((line) => {
    const t = line.trim();
    if (!t) return;
    if (/^\[\d{1,2}:\d{2}:\d{2}\]/.test(t) || !logical.length) logical.push(t);
    else logical[logical.length - 1] += (logical[logical.length - 1].endsWith("-") ? "" : " ") + t;
  });

  const alerts = [];
  logical.forEach((text, i) => {
    const m = text.match(/^\[(\d{1,2}:\d{2}:\d{2})\]\s*([A-Za-z]+)\s*:\s*(.+)$/);
    if (!m) return;
    const time = m[1].length === 7 ? "0" + m[1] : m[1];
    const rest = m[3].trim();
    const dash = rest.match(/^(.*?)\s+[—–-]\s+(.+)$/);
    const typePart = dash ? dash[1].trim() : rest;
    const tokens = (dash ? dash[2].trim() : "").split(/\s+/).filter(Boolean);
    alerts.push({
      alert_id: "PASTE-" + String(i + 1).padStart(2, "0"),
      ts: "2026-03-22T" + time + "Z",
      device: tokens[0] || "UNKNOWN",
      type: typePart.toLowerCase().replace(/\s+/g, "_"),
      severity: m[2].toLowerCase(),
      message: text,
      iface: tokens.slice(1).join(" ") || null,
      peer: null
    });
  });
  return alerts;
}

function parseAlertsFromBox() {
  const raw = (alertsBox && alertsBox.value || "").trim();
  if (!raw) return loadedAlerts.slice();

  if (looksLikeLog(raw) && !looksLikeJson(raw)) {
    const fromLog = parseLogLines(raw);
    if (fromLog.length) return fromLog;
  }

  if (looksLikeJson(raw)) {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    return parsed.fibre_cut || parsed.unknown_fault || parsed.auth_noise ||
      parsed.two_sites || parsed.alerts || [];
  }

  return loadedAlerts.slice();
}

function onComposerChange() {
  try {
    const alerts = parseAlertsFromBox();
    loadedAlerts = alerts;
    renderFeed(alerts, true);
  } catch (err) {
    /* keep last good feed while typing */
  }
}

async function playScenario(name, btn) {
  stopLive();
  setActive(btn);
  const samples = await (await fetch("/api/samples")).json();
  const alerts = samples[name] || [];
  loadedAlerts = [];
  if (alertsBox) alertsBox.value = "";
  renderFeed([]);
  for (const alert of alerts) {
    loadedAlerts.push(alert);
    if (alertsBox) alertsBox.value = formatAlerts(loadedAlerts);
    renderFeed(loadedAlerts, true);
    await sleep(220);
  }
  await runTriage();
}

async function toggleLive() {
  if (liveTimer) {
    stopLive();
    return;
  }
  setActive(btnLive);
  if (btnLive) btnLive.textContent = "Stop live";
  const samples = await (await fetch("/api/samples")).json();
  const pool = []
    .concat(samples.fibre_cut || [])
    .concat(samples.unknown_fault || [])
    .concat(samples.auth_noise || [])
    .concat(samples.two_sites || []);
  let i = 0;
  loadedAlerts = [];
  if (alertsBox) alertsBox.value = "";
  renderFeed([]);
  liveTimer = setInterval(async () => {
    if (busy || !pool.length) return;
    loadedAlerts.push(pool[i % pool.length]);
    i += 1;
    if (alertsBox) alertsBox.value = formatAlerts(loadedAlerts);
    renderFeed(loadedAlerts, true);
    if (loadedAlerts.length % 4 === 0) await runTriage();
  }, 900);
}

function stopLive() {
  if (liveTimer) clearInterval(liveTimer);
  liveTimer = null;
  if (btnLive) {
    btnLive.textContent = "Live play";
    btnLive.classList.remove("active");
  }
}

function resetResultChrome() {
  const banner = document.getElementById("banner");
  if (banner) {
    banner.className = "banner idle";
    banner.textContent = "Waiting for a run";
  }
  const inc = document.getElementById("incident-list");
  const noise = document.getElementById("noise-list");
  if (inc) inc.innerHTML = "";
  if (noise) noise.innerHTML = "";
  const ie = document.getElementById("incident-empty");
  const ne = document.getElementById("noise-empty");
  if (ie) ie.style.display = "block";
  if (ne) ne.style.display = "block";
  const pv = document.getElementById("priority-value");
  const ps = document.getElementById("priority-sub");
  if (pv) pv.textContent = "—";
  if (ps) ps.textContent = "";
  const actions = document.getElementById("actions");
  if (actions) actions.innerHTML = "";
  const ge = document.getElementById("guide-empty");
  const hb = document.getElementById("human-block");
  const he = document.getElementById("human-empty");
  if (ge) ge.style.display = "block";
  if (hb) hb.innerHTML = "";
  if (he) he.style.display = "block";
  const statusRow = document.getElementById("status-row");
  if (statusRow) statusRow.querySelectorAll(".meta").forEach((n) => n.remove());
  ["step-1", "step-2", "step-3", "step-4"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("active", "done");
  });
}

function clearAll() {
  stopLive();
  fetch("/api/inbox", { method: "DELETE" });
  inboxVersion = -1;
  loadedAlerts = [];
  if (alertsBox) alertsBox.value = "";
  renderFeed([]);
  setActive(null);
  const elapsed = document.getElementById("elapsed");
  if (elapsed) elapsed.textContent = "idle";
  resetResultChrome();
}

function setStep(n, state) {
  const el = document.getElementById("step-" + n);
  if (!el) return;
  el.classList.remove("active", "done");
  if (state) el.classList.add(state);
}

async function runTriage() {
  let alerts;
  try {
    alerts = parseAlertsFromBox();
    loadedAlerts = alerts;
    renderFeed(alerts, false);
  } catch (err) {
    const banner = document.getElementById("banner");
    if (banner) {
      banner.className = "banner bad";
      banner.textContent = "Could not read log. Use [HH:MM:SS] SEVERITY: type - DEVICE";
    }
    return;
  }

  if (!alerts.length) {
    const banner = document.getElementById("banner");
    if (banner) {
      banner.className = "banner idle";
      banner.textContent = "No alerts";
    }
    return;
  }

  busy = true;
  if (btnRun) btnRun.disabled = true;
  const banner = document.getElementById("banner");
  if (banner) {
    banner.className = "banner busy";
    banner.textContent = "Working… grouping live alerts";
  }
  const elapsed = document.getElementById("elapsed");
  if (elapsed) elapsed.textContent = "running";
  setStep(1, "active");
  await sleep(180);
  setStep(1, "done");
  setStep(2, "active");

  const t0 = performance.now();
  try {
    const result = await (
      await fetch("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alerts: alerts })
      })
    ).json();
    setStep(2, "done");
    setStep(3, "active");
    await sleep(140);
    setStep(3, "done");
    setStep(4, "active");
    if (elapsed) elapsed.textContent = ((performance.now() - t0) / 1000).toFixed(1) + "s";
    await render(result);
    setStep(4, "done");
  } catch (err) {
    if (banner) {
      banner.className = "banner bad";
      banner.textContent = "Triage failed";
    }
  } finally {
    busy = false;
    if (btnRun) btnRun.disabled = false;
  }
}

function collectSteps(incidents, noise) {
  const steps = [];
  const seen = new Set();
  function add(list) {
    (list || []).forEach((a) => {
      if (!a || !a.step) return;
      const key = (a.source_runbook || "") + "|" + a.step;
      if (seen.has(key)) return;
      seen.add(key);
      steps.push({ step: a.step, source_runbook: a.source_runbook || "" });
    });
  }
  incidents.forEach((inc) => {
    add(inc.guided_steps);
    add(inc.note && inc.note.recommended_actions);
    (inc.runbooks || []).forEach((b) => add(b.steps));
  });
  noise.forEach((n) => { if (n.resolution === "guide") add(n.guided_steps); });
  return steps;
}

async function render(result) {
  const incidents = result.incidents || [];
  const noise = result.noise || [];
  const primary = incidents[0];
  const note = (primary && primary.note) || {};
  const solveSteps = collectSteps(incidents, noise);
  const humanBits = [];
  incidents.forEach((inc) => {
    const res = inc.resolution || {};
    if (res.mode === "human" || res.mode === "split") {
      humanBits.push(res.human_summary || "Left for engineer.");
    }
  });
  noise.forEach((n) => {
    if (n.resolution === "human") {
      humanBits.push(n.device + " " + n.type + " — no runbook, engineer to solve.");
    }
  });

  const banner = document.getElementById("banner");
  const statusRow = document.getElementById("status-row");
  if (statusRow) statusRow.querySelectorAll(".meta").forEach((n) => n.remove());

  if (!incidents.length && !noise.length) {
    if (banner) {
      banner.className = "banner idle";
      banner.textContent = "No alerts";
    }
    return;
  }

  if (banner) {
    if (solveSteps.length && !humanBits.length) {
      banner.className = "banner ok";
      banner.textContent = "✓ Matched runbook — follow these steps";
    } else if (!solveSteps.length && humanBits.length) {
      banner.className = "banner bad";
      banner.textContent = "No runbook — left for engineer";
    } else if (solveSteps.length && humanBits.length) {
      banner.className = "banner bad";
      banner.textContent = "Partial match — steps below, rest left for engineer";
    } else {
      banner.className = "banner idle";
      banner.textContent = "Triage complete";
    }
  }

  if (statusRow) {
    (primary && primary.runbooks ? primary.runbooks : []).forEach((b) => {
      const chip = document.createElement("span");
      chip.className = "meta";
      chip.textContent = "runbook " + b.id;
      statusRow.appendChild(chip);
    });
    const llm = document.createElement("span");
    llm.className = "meta";
    llm.textContent = note.llm_used ? "model used" : "runbook steps";
    statusRow.appendChild(llm);
  }

  const incList = document.getElementById("incident-list");
  if (incList) {
    incList.innerHTML = "";
    const ie = document.getElementById("incident-empty");
    if (ie) ie.style.display = incidents.length ? "none" : "block";
    for (const inc of incidents) {
      for (const a of inc.alerts || []) {
        const li = document.createElement("li");
        li.innerHTML =
          "<div><strong>" + esc(inc.id) + " · " + esc((a.severity || "").toUpperCase()) + "</strong> " +
          esc((a.type || "").replaceAll("_", " ")) + "</div>" +
          '<div class="tag">' + esc(a.device) + (a.iface ? " " + esc(a.iface) : "") + "</div>";
        incList.appendChild(li);
        await sleep(40);
      }
    }
  }

  const noiseList = document.getElementById("noise-list");
  if (noiseList) {
    noiseList.innerHTML = "";
    const ne = document.getElementById("noise-empty");
    if (ne) ne.style.display = noise.length ? "none" : "block";
    noise.forEach((n) => {
      const li = document.createElement("li");
      li.innerHTML =
        '<div class="tag">' + esc(n.device) + " " + esc(n.type) + "</div>" +
        '<div class="muted">' + esc(n.why_noise || n.message || "left as noise") + "</div>";
      noiseList.appendChild(li);
    });
  }

  const pri = (primary && primary.priority) || "—";
  const pv = document.getElementById("priority-value");
  const psub = document.getElementById("priority-sub");
  if (pv) pv.textContent = incidents.length ? labelPriority(pri) : "None";
  if (psub) {
    psub.textContent = primary
      ? pri + " · score " + primary.impact_score
      : noise.length ? "Leftover noise only" : "";
  }

  const actions = document.getElementById("actions");
  const ge = document.getElementById("guide-empty");
  if (actions) {
    actions.innerHTML = "";
    if (ge) ge.style.display = solveSteps.length ? "none" : "block";
    for (const a of solveSteps) {
      const li = document.createElement("li");
      li.innerHTML = esc(a.step) + ' <span class="cite">(' + esc(a.source_runbook) + ")</span>";
      actions.appendChild(li);
      await sleep(50);
    }
  }

  const humanBlock = document.getElementById("human-block");
  const he = document.getElementById("human-empty");
  if (humanBlock) {
    humanBlock.innerHTML = "";
    if (he) he.style.display = humanBits.length ? "none" : "block";
    humanBits.forEach((text) => {
      const div = document.createElement("div");
      div.className = "human-item";
      div.textContent = text;
      humanBlock.appendChild(div);
    });
  }
}

function labelPriority(p) {
  if (p === "P1") return "Critical";
  if (p === "P2") return "High Priority";
  if (p === "P3") return "Medium";
  if (p === "P4") return "Low";
  return p || "—";
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}