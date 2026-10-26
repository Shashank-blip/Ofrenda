const statusEl = document.querySelector("#status");
const noticeEl = document.querySelector("#notice");
const shelfEl = document.querySelector("#shelf");
const formEl = document.querySelector("#altar-form");
const pathEl = document.querySelector("#path");
const sampleBtn = document.querySelector("#sample");

const speeches = new Map();
let graves = [];
let active = null;
let busy = false;

function esc(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function quietRatio(days) {
  return Math.max(0, Math.min(days / (365.25 * 8), 1));
}

function setNotice(text) {
  noticeEl.hidden = !text;
  noticeEl.textContent = text || "";
}

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    statusEl.classList.toggle("lit", Boolean(health.model_ready));
    if (!health.ollama) {
      statusEl.textContent = "Ollama is not running. The altar can still show git.";
    } else if (!health.model_ready) {
      statusEl.textContent = `Ollama is up. ${health.model} is not pulled yet.`;
    } else {
      statusEl.textContent = `Gemma is lit · ${health.model}`;
    }
  } catch {
    statusEl.classList.remove("lit");
    statusEl.textContent = "The altar page could not reach its own server.";
  }
}

function speechHtml(path) {
  const speech = speeches.get(path);
  if (!speech) return "";
  if (speech.pending) {
    return `<div class="speech"><p class="waiting">Listening to the record…</p></div>`;
  }
  if (!speech.lit || speech.refused) {
    const reason = speech.reason || "The model did not answer from the record.";
    return `<div class="speech"><p class="waiting">${esc(reason)} The inscription above is the last commit subject.</p></div>`;
  }
  const cites = (speech.citations || [])
    .map((item) => `<li><time>${esc(item.date)}</time> ${esc(item.sha)} ${esc(item.subject)}</li>`)
    .join("");
  return `
    <div class="speech">
      <p class="epitaph">${esc(speech.epitaph)}</p>
      <p class="remembrance">${esc(speech.remembrance)}</p>
      <ul class="record">${cites}</ul>
      <div class="offering"><span>Offering</span>${esc(speech.offering)}</div>
      <p class="spoken-by">Spoken by ${esc(speech.model)}, on this machine.</p>
    </div>`;
}

function render() {
  shelfEl.innerHTML = graves.map((grave) => {
    const open = grave.path === active;
    const ratio = quietRatio(grave.quiet_days).toFixed(3);
    const label = open && speeches.has(grave.path) && !speeches.get(grave.path).pending
      ? "Asked"
      : "Ask this repo to speak";
    return `
      <article class="niche${open ? " open" : ""}" style="--quiet:${ratio}">
        <div class="flame" aria-hidden="true"><i></i></div>
        <h2>${esc(grave.name)}</h2>
        <p class="years">${esc(grave.lifespan)} · ${esc(String(grave.commit_count))} commits</p>
        <p class="quiet">${esc(grave.quiet_label)}</p>
        <p class="inscription">${esc(grave.last_subject)}</p>
        <button type="button" class="ask" data-path="${esc(grave.path)}">${label}</button>
        ${open ? speechHtml(grave.path) : ""}
      </article>`;
  }).join("");
}

async function showAltar(url, options) {
  setNotice("");
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    graves = [];
    active = null;
    render();
    setNotice(payload.detail || "That folder could not be read.");
    return;
  }
  graves = payload.graves || [];
  active = null;
  render();
  if (!graves.length) {
    setNotice("No git repositories in that folder. Choose a repository, or a folder that contains some.");
  } else if (payload.truncated) {
    setNotice("Showing 24 niches. The rest of the folder is still dark.");
  }
}

async function ask(path) {
  if (busy) return;
  active = path;
  if (speeches.has(path) && !speeches.get(path).pending) {
    render();
    return;
  }
  busy = true;
  speeches.set(path, { pending: true });
  render();
  shelfEl.querySelectorAll("button").forEach((button) => {
    button.disabled = true;
  });
  try {
    const response = await fetch("/api/remembrance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const payload = await response.json();
    if (!response.ok) {
      speeches.set(path, { lit: false, refused: true, reason: payload.detail || "The record could not be read." });
    } else {
      speeches.set(path, payload);
    }
  } catch {
    speeches.set(path, { lit: false, refused: true, reason: "The request stopped before Gemma answered." });
  } finally {
    busy = false;
    render();
  }
}

shelfEl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-path]");
  if (!button) return;
  ask(button.dataset.path);
});

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const path = pathEl.value.trim();
  if (!path) {
    setNotice("Type a folder path, or sit with the sample.");
    return;
  }
  showAltar("/api/altar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
});

sampleBtn.addEventListener("click", () => {
  showAltar("/api/sample");
});

refreshHealth();
