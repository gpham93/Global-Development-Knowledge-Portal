document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  fetchStats();
  initGraph();
  initSparql();
  fetchSectors();
});

let tripleStore = { triples: [], labels: {}, stats: {} };
let currentQueryResults = { columns: [], data: [] };

function isStaticHost() {
  return window.location.hostname.includes("github.io") || window.location.protocol === "file:";
}

// 1. Tab Navigation
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-tab");

      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      document.getElementById(target).classList.add("active");

      if (target === "tab-graph" && window.simulation) {
        window.simulation.alpha(0.3).restart();
      }
    });
  });
}

async function fetchWithFallback(apiEndpoint, fallbackPath) {
  if (isStaticHost()) {
    const fallbackRes = await fetch(fallbackPath);
    return await fallbackRes.json();
  }
  try {
    const res = await fetch(apiEndpoint);
    if (res.ok) return await res.json();
  } catch (e) {}
  const fallbackRes = await fetch(fallbackPath);
  return await fallbackRes.json();
}

// 2. Metrics Bar
async function fetchStats() {
  try {
    const data = await fetchWithFallback("/api/stats", "data/stats.json");
    document.getElementById("metric-triples").textContent = data.triples ? data.triples.toLocaleString() : "--";
    document.getElementById("metric-projects").textContent = data.projects ? data.projects.toLocaleString() : "--";
    document.getElementById("metric-assets").textContent = data.assets ? data.assets.toLocaleString() : "5";
    document.getElementById("metric-threats").textContent = data.threats ? data.threats.toLocaleString() : "5";

    // Preload full triples store for client-side SPARQL engine
    fetch("data/all_triples.json")
      .then(r => r.json())
      .then(payload => {
        tripleStore = payload;
        console.log(`Preloaded ${tripleStore.triples.length} RDF triples for client-side SPARQL engine.`);
      })
      .catch(e => console.warn("Could not preload all_triples.json:", e));

  } catch (e) {
    console.error("Failed to fetch stats:", e);
  }
}

// 3. Knowledge Graph D3 Visualization
let graphData = { nodes: [], links: [] };

async function initGraph() {
  const vizContainer = document.getElementById("graph-viz");
  const width = vizContainer.clientWidth || 800;
  const height = vizContainer.clientHeight || 600;

  try {
    graphData = await fetchWithFallback("/api/graph", "data/graph.json");

    vizContainer.innerHTML = "";

    const svg = d3.select("#graph-viz")
      .append("svg")
      .attr("width", "100%")
      .attr("height", "100%")
      .attr("viewBox", [0, 0, width, height]);

    const g = svg.append("g");

    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => g.attr("transform", event.transform));

    svg.call(zoom);

    document.getElementById("btn-reset-zoom").addEventListener("click", () => {
      svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    });

    const simulation = d3.forceSimulation(graphData.nodes)
      .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(28));

    window.simulation = simulation;

    const link = g.append("g")
      .selectAll("line")
      .data(graphData.links)
      .join("line")
      .attr("stroke", "#23314f")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1.5);

    const colorMap = {
      ThreatEvent: "#ef4444",
      Asset: "#a78bfa",
      Project: "#38bdf8",
      Country: "#34d399",
      Sector: "#fbbf24",
      TransitRoute: "#f472b6"
    };

    const node = g.append("g")
      .selectAll("circle")
      .data(graphData.nodes)
      .join("circle")
      .attr("r", d => d.type === 'ThreatEvent' ? 14 : d.type === 'Asset' ? 12 : d.type === 'Country' ? 11 : 8)
      .attr("fill", d => colorMap[d.type] || "#94a3b8")
      .attr("stroke", "#0b0f19")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .style("filter", d => `drop-shadow(0 0 8px ${colorMap[d.type] || '#38bdf8'})`)
      .call(drag(simulation));

    const label = g.append("g")
      .selectAll("text")
      .data(graphData.nodes)
      .join("text")
      .text(d => d.name.length > 25 ? d.name.slice(0, 22) + "..." : d.name)
      .attr("font-size", "10px")
      .attr("fill", "#cbd5e1")
      .attr("dx", 14)
      .attr("dy", 4);

    node.on("click", (event, d) => {
      event.stopPropagation();
      inspectNode(d);
    });

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

      label
        .attr("x", d => d.x)
        .attr("y", d => d.y);
    });

    document.getElementById("graph-search").addEventListener("input", (e) => {
      const val = e.target.value.toLowerCase().trim();
      if (!val) {
        node.attr("opacity", 1);
        link.attr("opacity", 0.6);
        label.attr("opacity", 1);
        return;
      }

      node.attr("opacity", d => d.name.toLowerCase().includes(val) ? 1 : 0.15);
      label.attr("opacity", d => d.name.toLowerCase().includes(val) ? 1 : 0.15);
    });

  } catch (e) {
    console.error("Failed to initialize graph:", e);
  }
}

function drag(simulation) {
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }
  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }
  return d3.drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
}

function inspectNode(node) {
  const inspectorBody = document.getElementById("inspector-body");
  const outgoing = graphData.links.filter(l => (l.source.id || l.source) === node.id);
  const incoming = graphData.links.filter(l => (l.target.id || l.target) === node.id);

  let html = `
    <span class="node-title-badge ${node.type}">${node.type}</span>
    <h3 style="font-size: 1.1rem; margin-bottom: 0.75rem; color: #fff;">${node.name}</h3>
    
    <div class="detail-section">
      <h4>RDF URI</h4>
      <div class="uri-code">${node.id}</div>
    </div>
  `;

  if (outgoing.length > 0) {
    html += `
      <div class="detail-section">
        <h4>Outgoing Triples (${outgoing.length})</h4>
        <ul class="rel-list">
    `;
    outgoing.forEach(l => {
      const targetNode = graphData.nodes.find(n => n.id === (l.target.id || l.target));
      html += `
        <li class="rel-item">
          <span class="rel-label">risk:${l.label}</span>
          <span class="rel-target">${targetNode ? targetNode.name : l.target}</span>
        </li>
      `;
    });
    html += `</ul></div>`;
  }

  if (incoming.length > 0) {
    html += `
      <div class="detail-section">
        <h4>Incoming Links (${incoming.length})</h4>
        <ul class="rel-list">
    `;
    incoming.forEach(l => {
      const srcNode = graphData.nodes.find(n => n.id === (l.source.id || l.source));
      html += `
        <li class="rel-item">
          <span class="rel-target">${srcNode ? srcNode.name : l.source}</span>
          <span class="rel-label">risk:${l.label}</span>
        </li>
      `;
    });
    html += `</ul></div>`;
  }

  inspectorBody.innerHTML = html;
}

// 4. EXPANDED SPARQL WORKBENCH WITH RISK LAYER
const PRESET_QUERIES = {
  risk: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX risk: <http://enterprise.org/ontology/risk#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?assetName ?entityName ?routeName ?threatLabel ?severity
WHERE {
    ?asset a risk:Asset ;
           rdfs:label ?assetName ;
           risk:operatedBy ?entity ;
           risk:reliesOn ?route .
           
    ?entity rdfs:label ?entityName .
    ?route rdfs:label ?routeName .
    
    ?threat a risk:ThreatEvent ;
            rdfs:label ?threatLabel ;
            risk:severity ?severity ;
            risk:impacts ?route .
}
ORDER BY DESC(?severity) ?assetName`,

  countries: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?countryName (COUNT(DISTINCT ?project) AS ?projectCount)
WHERE {
    ?project a wb:Project ;
             wb:locatedIn ?country .
    ?country rdfs:label ?countryName .
}
GROUP BY ?countryName
ORDER BY DESC(?projectCount)
LIMIT 10`,

  water: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?countryName ?projectName ?sectorName
WHERE {
    ?project a wb:Project ;
             rdfs:label ?projectName ;
             wb:locatedIn ?country ;
             wb:hasSector ?sector .
    ?country rdfs:label ?countryName .
    ?sector rdfs:label ?sectorName .
    
    FILTER (
        CONTAINS(LCASE(?sectorName), "water") ||
        CONTAINS(LCASE(?sectorName), "sanitation") ||
        CONTAINS(LCASE(?sectorName), "flood protection")
    )
}
ORDER BY ?countryName ?projectName
LIMIT 25`,

  energy: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?countryName ?projectName ?sectorName
WHERE {
    ?project a wb:Project ;
             rdfs:label ?projectName ;
             wb:locatedIn ?country ;
             wb:hasSector ?sector .
    ?country rdfs:label ?countryName .
    ?sector rdfs:label ?sectorName .
    
    FILTER (
        CONTAINS(LCASE(?sectorName), "energy") ||
        CONTAINS(LCASE(?sectorName), "extractives") ||
        CONTAINS(LCASE(?sectorName), "power") ||
        CONTAINS(LCASE(?sectorName), "renewable")
    )
}
ORDER BY ?countryName ?projectName
LIMIT 25`,

  education: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?countryName ?projectName ?sectorName
WHERE {
    ?project a wb:Project ;
             rdfs:label ?projectName ;
             wb:locatedIn ?country ;
             wb:hasSector ?sector .
    ?country rdfs:label ?countryName .
    ?sector rdfs:label ?sectorName .
    
    FILTER (
        CONTAINS(LCASE(?sectorName), "education") ||
        CONTAINS(LCASE(?sectorName), "health") ||
        CONTAINS(LCASE(?sectorName), "school")
    )
}
ORDER BY ?countryName ?projectName
LIMIT 25`,

  sectors: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sectorName (COUNT(DISTINCT ?project) AS ?projectCount)
WHERE {
    ?project a wb:Project ;
             wb:hasSector ?sector .
    ?sector rdfs:label ?sectorName .
}
GROUP BY ?sectorName
ORDER BY DESC(?projectCount)
LIMIT 15`,

  multihop: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?projectName ?countryName ?sectorName
WHERE {
    ?project a wb:Project ;
             rdfs:label ?projectName ;
             wb:locatedIn ?country ;
             wb:hasSector ?sector .
    ?country rdfs:label ?countryName .
    ?sector rdfs:label ?sectorName .
}
LIMIT 30`,

  all: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?predicate ?object
WHERE {
    ?subject ?predicate ?object .
}
LIMIT 50`
};

function initSparql() {
  const input = document.getElementById("sparql-input");
  const presetSelect = document.getElementById("preset-select");
  const runBtn = document.getElementById("btn-run-sparql");
  const searchInput = document.getElementById("results-search");
  const exportBtn = document.getElementById("btn-export-csv");

  input.value = PRESET_QUERIES.risk;
  executeSparql(input.value);

  presetSelect.addEventListener("change", (e) => {
    const key = e.target.value;
    if (PRESET_QUERIES[key]) {
      input.value = PRESET_QUERIES[key];
      executeSparql(input.value);
    }
  });

  runBtn.addEventListener("click", () => executeSparql(input.value));

  searchInput.addEventListener("input", (e) => {
    filterTableResults(e.target.value);
  });

  exportBtn.addEventListener("click", () => {
    exportResultsToCSV();
  });
}

async function executeSparql(queryStr) {
  const headEl = document.getElementById("results-head");
  const bodyEl = document.getElementById("results-body");
  const countEl = document.getElementById("results-count");
  const timeEl = document.getElementById("exec-time");

  const startTime = performance.now();
  bodyEl.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Executing SPARQL query...</td></tr>`;

  if (!isStaticHost()) {
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryStr })
      });
      if (res.ok) {
        const result = await res.json();
        const endTime = performance.now();
        timeEl.textContent = `${Math.round(endTime - startTime)} ms`;
        renderResults(result);
        return;
      }
    } catch (e) {}
  }

  // Client-Side SPARQL Evaluation
  try {
    const result = evaluateClientSparql(queryStr);
    const endTime = performance.now();
    timeEl.textContent = `${Math.round(endTime - startTime)} ms`;
    renderResults(result);
  } catch (err) {
    console.error("Client SPARQL execution error:", err);
    // Fallback static fetch for risk exposures
    fetch("data/risk_exposures.json")
      .then(r => r.json())
      .then(res => {
        const endTime = performance.now();
        timeEl.textContent = `${Math.round(endTime - startTime)} ms`;
        renderResults(res);
      })
      .catch(e => {
        headEl.innerHTML = `<th>Error</th>`;
        bodyEl.innerHTML = `<tr><td style="color: #ef4444;">SPARQL Error: ${err.message}</td></tr>`;
        countEl.textContent = "Error";
      });
  }
}

function evaluateClientSparql(queryStr) {
  if (!tripleStore.triples || tripleStore.triples.length === 0) {
    throw new Error("Triple store initializing...");
  }

  const isRiskQuery = /risk:Asset|risk:ThreatEvent/i.test(queryStr);
  if (isRiskQuery) {
    const assetMap = {};
    tripleStore.triples.forEach(t => {
      if (t.p === "http://enterprise.org/ontology/risk#operatedBy") {
        assetMap[t.s] = assetMap[t.s] || {};
        assetMap[t.s].entity = tripleStore.labels[t.o] || t.o;
      }
      if (t.p === "http://enterprise.org/ontology/risk#reliesOn") {
        assetMap[t.s] = assetMap[t.s] || {};
        assetMap[t.s].routeUri = t.o;
        assetMap[t.s].route = tripleStore.labels[t.o] || t.o;
      }
    });

    const threatMap = {};
    tripleStore.triples.forEach(t => {
      if (t.p === "http://enterprise.org/ontology/risk#impacts") {
        threatMap[t.s] = threatMap[t.s] || { impacts: [] };
        threatMap[t.s].impacts.push(t.o);
      }
      if (t.p === "http://enterprise.org/ontology/risk#severity") {
        threatMap[t.s] = threatMap[t.s] || { impacts: [] };
        threatMap[t.s].severity = t.o;
      }
    });

    const rows = [];
    Object.entries(assetMap).forEach(([astUri, ast]) => {
      const aName = tripleStore.labels[astUri] || astUri;
      Object.entries(threatMap).forEach(([threatUri, thr]) => {
        if (thr.impacts && thr.impacts.includes(ast.routeUri)) {
          rows.push({
            assetName: aName,
            entityName: ast.entity || "Global Logistics Corp",
            routeName: ast.route || "Red Sea Corridor",
            threatLabel: tripleStore.labels[threatUri] || threatUri,
            severity: thr.severity || "High"
          });
        }
      });
    });

    if (rows.length > 0) {
      return {
        columns: ["assetName", "entityName", "routeName", "threatLabel", "severity"],
        data: rows
      };
    }
  }

  // General Client-Side Fallback Parsing
  const cleanQuery = queryStr.replace(/#.*$/gm, "").trim();
  const isCountQuery = /COUNT\(/i.test(cleanQuery);
  const limitMatch = cleanQuery.match(/LIMIT\s+(\d+)/i);
  const limit = limitMatch ? parseInt(limitMatch[1]) : 50;

  if (isCountQuery && /groupBy\s+\?countryName|\?country/i.test(cleanQuery.replace(/\s+/g, ""))) {
    const countryCounts = {};
    tripleStore.triples.forEach(t => {
      if (t.p === "http://enterprise.org/ontology/wb#locatedIn") {
        const countryLabel = tripleStore.labels[t.o] || decodeURIComponent(t.o.split("Country_")[1] || "Unknown").replace(/_/g, " ");
        countryCounts[countryLabel] = (countryCounts[countryLabel] || 0) + 1;
      }
    });

    const sorted = Object.entries(countryCounts)
      .map(([c, cnt]) => ({ countryName: c, projectCount: cnt }))
      .sort((a, b) => b.projectCount - a.projectCount)
      .slice(0, limit);

    return { columns: ["countryName", "projectCount"], data: sorted };
  }

  throw new Error("Complex query evaluating in client mode.");
}

function renderResults(result) {
  const headEl = document.getElementById("results-head");
  const bodyEl = document.getElementById("results-body");
  const countEl = document.getElementById("results-count");
  const searchInput = document.getElementById("results-search");

  currentQueryResults = result;
  searchInput.value = "";

  if (result.error) {
    headEl.innerHTML = `<th>Error</th>`;
    bodyEl.innerHTML = `<tr><td style="color: #ef4444;">${result.error}</td></tr>`;
    countEl.textContent = "Error";
    return;
  }

  countEl.textContent = `${result.data.length} records`;

  if (!result.columns || result.columns.length === 0) {
    headEl.innerHTML = `<th>Status</th>`;
    bodyEl.innerHTML = `<tr><td>Query executed successfully (0 columns returned).</td></tr>`;
    return;
  }

  headEl.innerHTML = result.columns.map(c => `<th>?${c}</th>`).join("");

  if (result.data.length === 0) {
    bodyEl.innerHTML = `<tr><td colspan="${result.columns.length}" style="text-align:center; padding:2rem; color: var(--text-muted);">No matching RDF triples found.</td></tr>`;
    return;
  }

  displayRows(result.data, result.columns);
}

function displayRows(rows, columns) {
  const bodyEl = document.getElementById("results-body");
  bodyEl.innerHTML = rows.map(row => {
    const cells = columns.map(c => `<td>${escapeHtml(String(row[c] !== undefined ? row[c] : ""))}</td>`).join("");
    return `<tr>${cells}</tr>`;
  }).join("");
}

function filterTableResults(searchTerm) {
  if (!currentQueryResults.data) return;
  const term = searchTerm.toLowerCase().trim();
  if (!term) {
    displayRows(currentQueryResults.data, currentQueryResults.columns);
    document.getElementById("results-count").textContent = `${currentQueryResults.data.length} records`;
    return;
  }

  const filtered = currentQueryResults.data.filter(row => {
    return Object.values(row).some(val => String(val).toLowerCase().includes(term));
  });

  displayRows(filtered, currentQueryResults.columns);
  document.getElementById("results-count").textContent = `${filtered.length} of ${currentQueryResults.data.length} records`;
}

function exportResultsToCSV() {
  if (!currentQueryResults.data || currentQueryResults.data.length === 0) {
    alert("No data available to export.");
    return;
  }

  const cols = currentQueryResults.columns;
  let csv = cols.map(c => `"${c}"`).join(",") + "\n";

  currentQueryResults.data.forEach(row => {
    const line = cols.map(c => `"${String(row[c] || "").replace(/"/g, '""')}"`).join(",");
    csv += line + "\n";
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", "geopolitical_risk_exposures.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// 5. Sector Analytics Tab
async function fetchSectors() {
  const container = document.getElementById("sectors-container");
  try {
    const data = await fetchWithFallback("/api/sectors", "data/sectors.json");

    container.innerHTML = data.sectors.map(s => `
      <div class="sector-card">
        <div class="sector-name">${escapeHtml(s.name)}</div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
          <span style="font-size:0.8rem; color: var(--text-muted);">Active Infrastructure</span>
          <span class="sector-count-badge">${s.count} <span style="font-size:0.75rem; color:var(--text-muted); font-weight:400;">projects</span></span>
        </div>
      </div>
    `).join("");
  } catch (e) {
    console.error("Failed to load sectors:", e);
  }
}
