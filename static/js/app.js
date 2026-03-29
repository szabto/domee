const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let lastCheckResult = null;

// --- API ---

async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// --- Safe DOM helpers ---

function createEl(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") el.className = v;
    else if (k === "textContent") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
    else el.setAttribute(k, v);
  }
  for (const child of children) {
    if (typeof child === "string") el.appendChild(document.createTextNode(child));
    else el.appendChild(child);
  }
  return el;
}

function clearEl(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

// --- Domains ---

async function loadDomains() {
  const domains = await api("GET", "/domains");
  renderDomains(domains);
}

function renderDomains(domains) {
  const list = $("#domain-list");
  const empty = $("#empty-state");
  const header = $("#list-header");

  clearEl(list);

  if (domains.length === 0) {
    empty.style.display = "flex";
    header.style.display = "none";
    return;
  }

  empty.style.display = "none";
  header.style.display = "grid";

  for (const d of domains) {
    const dot = createEl("span", { className: "dot" });
    const statusText = d.status === "available" ? "Available" : "Registered";
    const statusEl = createEl("span", { className: `domain-status ${d.status}` }, [
      dot,
      ` ${statusText}`,
    ]);

    const deleteSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    deleteSvg.setAttribute("width", "16");
    deleteSvg.setAttribute("height", "16");
    deleteSvg.setAttribute("viewBox", "0 0 16 16");
    deleteSvg.setAttribute("fill", "none");
    deleteSvg.setAttribute("stroke", "currentColor");
    deleteSvg.setAttribute("stroke-width", "1.5");
    const path1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path1.setAttribute("d", "M4 4l8 8");
    const path2 = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path2.setAttribute("d", "M12 4l-8 8");
    deleteSvg.appendChild(path1);
    deleteSvg.appendChild(path2);

    const deleteBtn = createEl("button", {
      className: "btn-delete",
      title: "Remove",
      onClick: () => deleteDomain(d.id),
    }, [deleteSvg]);

    const lastChecked = d.last_checked ? formatLastChecked(d.last_checked) : "\u2014";

    const item = createEl("div", { className: "domain-item", "data-id": String(d.id) }, [
      createEl("span", { className: "domain-name", textContent: d.name }),
      createEl("span", { className: "domain-expiry", textContent: d.expiry_date || "\u2014" }),
      createEl("span", { className: "domain-last-checked", textContent: lastChecked }),
      statusEl,
      deleteBtn,
    ]);

    list.appendChild(item);
  }
}

async function deleteDomain(id) {
  await api("DELETE", `/domains/${id}`);
  await loadDomains();
}

async function addDomain(name) {
  try {
    await api("POST", "/domains", { name });
    lastCheckResult = null;
    hideCheckResult();
    $("#search-input").value = "";
    await loadDomains();
  } catch (e) {
    showToast(e.message);
  }
}

// --- Check ---

async function checkDomain() {
  const input = $("#search-input");
  const name = input.value.trim();
  if (!name) return;

  setLoading(true);
  hideCheckResult();

  try {
    const result = await api("POST", "/check", { name });
    lastCheckResult = result;
    showCheckResult(result);
  } catch (e) {
    showToast(e.message);
  } finally {
    setLoading(false);
  }
}

function showCheckResult(result) {
  const el = $("#check-result");
  const addBtn = $("#btn-add");

  clearEl(el);
  el.className = `check-result visible ${result.available ? "available" : "registered"}`;

  const dot = createEl("span", {
    className: "dot",
    style: "width:6px;height:6px;border-radius:50%;background:currentColor",
  });

  const text = result.available
    ? `${result.name} is available!`
    : `${result.name} is taken`;

  el.appendChild(dot);
  el.appendChild(createEl("span", { textContent: text }));

  if (result.expiry_date) {
    el.appendChild(
      createEl("span", { className: "expiry-info", textContent: `Expires ${result.expiry_date}` })
    );
  }

  addBtn.classList.add("visible");
}

function hideCheckResult() {
  const el = $("#check-result");
  el.className = "check-result";
  clearEl(el);
  $("#btn-add").classList.remove("visible");
}

function setLoading(loading) {
  const input = $("#search-input");
  const btn = $("#btn-check");
  if (loading) {
    input.classList.add("loading");
    btn.disabled = true;
    clearEl(btn);
    btn.appendChild(createEl("div", { className: "spinner" }));
  } else {
    input.classList.remove("loading");
    btn.disabled = false;
    btn.textContent = "Check";
  }
}

// --- Settings ---

async function loadSettings() {
  const settings = await api("GET", "/settings");
  $("#s-polling").value = settings.polling_interval || "60";
  $("#s-email").value = settings.notification_email || "";
  $("#s-smtp-host").value = settings.smtp_host || "";
  $("#s-smtp-port").value = settings.smtp_port || "587";
  $("#s-smtp-user").value = settings.smtp_username || "";
  $("#s-smtp-pass").value = settings.smtp_password || "";
  $("#s-smtp-from").value = settings.smtp_from_email || "";
  $("#s-smtp-tls").checked = settings.smtp_use_tls !== "false";
}

async function saveSettings() {
  const data = {
    polling_interval: $("#s-polling").value,
    notification_email: $("#s-email").value,
    smtp_host: $("#s-smtp-host").value,
    smtp_port: $("#s-smtp-port").value,
    smtp_username: $("#s-smtp-user").value,
    smtp_password: $("#s-smtp-pass").value,
    smtp_from_email: $("#s-smtp-from").value,
    smtp_use_tls: $("#s-smtp-tls").checked ? "true" : "false",
  };

  await api("PUT", "/settings", data);
  closeSettings();
  showToast("Settings saved");
}

function openSettings() {
  loadSettings();
  $("#settings-modal").classList.add("visible");
}

function closeSettings() {
  $("#settings-modal").classList.remove("visible");
}

// --- Formatting ---

function formatLastChecked(isoStr) {
  try {
    const date = new Date(isoStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return "\u2014";
  }
}

// --- Toast ---

function showToast(message) {
  const el = $("#check-result");
  clearEl(el);
  el.className = "check-result visible registered";
  el.appendChild(createEl("span", { textContent: message }));
  const currentMsg = message;
  setTimeout(() => {
    if (el.textContent === currentMsg) hideCheckResult();
  }, 3000);
}

// --- Events ---

document.addEventListener("DOMContentLoaded", () => {
  loadDomains();

  $("#search-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") checkDomain();
  });

  $("#btn-check").addEventListener("click", checkDomain);

  $("#btn-add").addEventListener("click", () => {
    const name = $("#search-input").value.trim();
    if (name) addDomain(name);
  });

  $("#btn-settings").addEventListener("click", openSettings);
  $("#btn-close-settings").addEventListener("click", closeSettings);
  $("#btn-save-settings").addEventListener("click", saveSettings);

  $("#settings-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeSettings();
  });

  $("#btn-poll").addEventListener("click", async () => {
    const btn = $("#btn-poll");
    btn.disabled = true;
    clearEl(btn);
    btn.appendChild(createEl("div", { className: "spinner" }));
    try {
      await api("POST", "/poll");
      await loadDomains();
      showToast("Poll complete");
    } catch (e) {
      showToast(e.message);
    } finally {
      btn.disabled = false;
      clearEl(btn);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("width", "18");
      svg.setAttribute("height", "18");
      svg.setAttribute("viewBox", "0 0 18 18");
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "currentColor");
      svg.setAttribute("stroke-width", "1.5");
      const p1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p1.setAttribute("d", "M3 9a6 6 0 1 1 1.05 3.36");
      const p2 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p2.setAttribute("d", "M3 15V12h3");
      svg.appendChild(p1);
      svg.appendChild(p2);
      btn.appendChild(svg);
    }
  });
});
