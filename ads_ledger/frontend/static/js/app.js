const api = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

const formJson = form => Object.fromEntries(new FormData(form).entries());
const asPretty = data => JSON.stringify(data, null, 2);

async function loadCivilizations() {
  const civs = await api("/api/civilizations");
  document.querySelectorAll("select[name='civilization_id'], #scoreCivilization, #searchCivilization").forEach(select => {
    const keepAll = select.id === "searchCivilization";
    select.innerHTML = keepAll ? `<option value="">All civilizations</option>` : "";
    civs.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      select.appendChild(opt);
    });
  });
  const list = document.querySelector("#civilizationList");
  if (list) {
    list.innerHTML = civs.map(c => `<div class="item"><strong>${c.name}</strong><span>${c.region || "Unknown region"}</span><p>${c.start_year ?? "?"} to ${c.end_year ?? "?"}</p></div>`).join("");
  }
  return civs;
}

async function loadLedger() {
  const entries = await api("/api/ledger");
  const target = document.querySelector("#ledgerList");
  if (!target) return entries;
  target.innerHTML = `<table><thead><tr><th>Civilization</th><th>Year</th><th>Type</th><th>Domain</th><th>Value</th><th>Description</th></tr></thead><tbody>${
    entries.map(e => `<tr><td>${e.civilization_name}</td><td>${e.year}</td><td><span class="tag ${e.entry_type === "Liability" ? "liability" : ""}">${e.entry_type}</span></td><td>${e.domain}</td><td>${e.value}</td><td>${e.description}</td></tr>`).join("")
  }</tbody></table>`;
  return entries;
}

async function loadDashboard() {
  const target = document.querySelector("#dashboardMetrics");
  if (!target) return;
  const [civs, entries, stats] = await Promise.all([api("/api/civilizations"), api("/api/ledger"), api("/api/compression/stats")]);
  target.innerHTML = `
    <div class="panel"><strong>${civs.length}</strong><span>Civilizations</span></div>
    <div class="panel"><strong>${entries.length}</strong><span>Ledger entries</span></div>
    <div class="panel"><strong>${stats.text_characters}</strong><span>Indexed text characters</span></div>`;
}

async function loadCompression() {
  const stats = document.querySelector("#compressionStats");
  if (stats) stats.textContent = asPretty(await api("/api/compression/stats"));
}

document.addEventListener("submit", async event => {
  if (event.target.id === "civilizationForm") {
    event.preventDefault();
    await api("/api/civilizations", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(formJson(event.target)),
    });
    event.target.reset();
    await loadCivilizations();
  }
  if (event.target.id === "ledgerForm") {
    event.preventDefault();
    await api("/api/ledger", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(formJson(event.target)),
    });
    event.target.reset();
    await loadLedger();
  }
  if (event.target.id === "uploadForm") {
    event.preventDefault();
    const result = await api("/api/import", {method: "POST", body: new FormData(event.target)});
    document.querySelector("#importOutput").textContent = asPretty(result);
    await loadCivilizations();
  }
  if (event.target.id === "externalForm") {
    event.preventDefault();
    const payload = formJson(event.target);
    let result;
    if (payload.source === "seshat") {
      result = await api("/api/data/simulate-seshat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({civilization_id: payload.civilization_id}),
      });
    } else {
      const url = payload.source === "wikipedia" ? "/api/data/wikipedia" : "/api/data/dbpedia";
      result = await api(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          civilization_id: payload.civilization_id,
          title: payload.title,
          resource: payload.title,
        }),
      });
    }
    document.querySelector("#importOutput").textContent = asPretty(result);
  }
});

document.addEventListener("click", async event => {
  if (event.target.id === "scoreButton") {
    const civId = document.querySelector("#scoreCivilization").value;
    document.querySelector("#scoreOutput").textContent = asPretty(await api(`/api/score/${civId}`));
  }
  if (event.target.id === "searchButton") {
    const q = encodeURIComponent(document.querySelector("#searchQuery").value);
    const mode = document.querySelector("#searchMode").value;
    const civ = document.querySelector("#searchCivilization").value;
    const url = `/api/search?q=${q}&mode=${mode}${civ ? `&civilization_id=${civ}` : ""}`;
    const rows = await api(url);
    document.querySelector("#searchResults").innerHTML = rows.map(e => `
      <div class="item">
        <strong>${e.civilization_name} · ${e.year}</strong>
        <span class="tag ${e.entry_type === "Liability" ? "liability" : ""}">${e.entry_type}</span><span class="tag">${e.domain}</span>
        <p>${e.snippet || e.description}</p>
      </div>`).join("") || `<div class="item">No results.</div>`;
  }
  if (event.target.id === "rangeButton") {
    const low = document.querySelector("#rangeLow").value;
    const high = document.querySelector("#rangeHigh").value;
    document.querySelector("#rangeOutput").textContent = asPretty(await api(`/api/compression/range?low=${low}&high=${high}`));
  }
});

loadCivilizations().then(() => Promise.all([loadLedger(), loadDashboard(), loadCompression()])).catch(console.error);
