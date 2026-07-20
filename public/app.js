document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  fetchStats();
  initGraph();
  initSparql();
  fetchSectors();
});

// Helper to detect if running on GitHub Pages or static host
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

// Helper to fetch with fallback
async function fetchWithFallback(apiEndpoint, fallbackPath) {
  if (isStaticHost()) {
    const fallbackRes = await fetch(fallbackPath);
    return await fallbackRes.json();
  }
  try {
    const res = await fetch(apiEndpoint);
    if (res.ok) return await res.json();
  } catch (e) {
    // API failed, try static file
  }
  const fallbackRes = await fetch(fallbackPath);
  return await fallbackRes.json();
}

// 2. Fetch Metrics
async function fetchStats() {
  try {
    const data = await fetchWithFallback("/api/stats", "data/stats.json");
    document.getElementById("metric-triples").textContent = data.triples.toLocaleString();
    document.getElementById("metric-projects").textContent = data.projects.toLocaleString();
    document.getElementById("metric-countries").textContent = data.countries.toLocaleString();
    document.getElementById("metric-sectors").textContent = data.sectors.toLocaleString();
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

    vizContainer.innerHTML = ""; // Clear existing

    const svg = d3.select("#graph-viz")
      .append("svg")
      .attr("width", "100%")
      .attr("height", "100%")
      .attr("viewBox", [0, 0, width, height]);

    const g = svg.append("g");

    // Zoom setup
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => g.attr("transform", event.transform));

    svg.call(zoom);

    document.getElementById("btn-reset-zoom").addEventListener("click", () => {
      svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    });

    // Force Simulation
    const simulation = d3.forceSimulation(graphData.nodes)
      .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(90))
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(25));

    window.simulation = simulation;

    // Draw Links
    const link = g.append("g")
      .selectAll("line")
      .data(graphData.links)
      .join("line")
      .attr("stroke", "#23314f")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1.5);

    // Node colors
    const colorMap = {
      Project: "#38bdf8",
      Country: "#34d399",
      Sector: "#fbbf24"
    };

    // Draw Nodes
    const node = g.append("g")
      .selectAll("circle")
      .data(graphData.nodes)
      .join("circle")
      .attr("r", d => d.type === 'Project' ? 8 : d.type === 'Country' ? 12 : 10)
      .attr("fill", d => colorMap[d.type] || "#94a3b8")
      .attr("stroke", "#0b0f19")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .style("filter", d => `drop-shadow(0 0 6px ${colorMap[d.type]})`)
      .call(drag(simulation));

    // Node Labels
    const label = g.append("g")
      .selectAll("text")
      .data(graphData.nodes)
      .join("text")
      .text(d => d.name.length > 25 ? d.name.slice(0, 22) + "..." : d.name)
      .attr("font-size", "10px")
      .attr("fill", "#cbd5e1")
      .attr("dx", 12)
      .attr("dy", 4);

    // Node Click -> Inspector
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

    // Search Filter
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

// Drag functionality for D3
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

// Inspect Node Details
function inspectNode(node) {
  const inspectorBody = document.getElementById("inspector-body");
  
  // Find outgoing & incoming links
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
          <span class="rel-label">wb:${l.label}</span>
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
          <span class="rel-label">wb:${l.label}</span>
        </li>
      `;
    });
    html += `</ul></div>`;
  }

  inspectorBody.innerHTML = html;
}

// 4. SPARQL Workbench
const PRESET_QUERIES = {
  countries: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?countryName (COUNT(DISTINCT ?project) AS ?projectCount)
WHERE {
    ?project a wb:Project ; wb:locatedIn ?country .
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
ORDER BY ?countryName ?projectName`,

  sectors: `PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sectorName (COUNT(DISTINCT ?project) AS ?projectCount)
WHERE {
    ?project a wb:Project ; wb:hasSector ?sector .
    ?sector rdfs:label ?sectorName .
}
GROUP BY ?sectorName
ORDER BY DESC(?projectCount)
LIMIT 15`,

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

  input.value = PRESET_QUERIES.countries;
  executeSparql(input.value);

  presetSelect.addEventListener("change", (e) => {
    const key = e.target.value;
    if (PRESET_QUERIES[key]) {
      input.value = PRESET_QUERIES[key];
      executeSparql(input.value);
    }
  });

  runBtn.addEventListener("click", () => executeSparql(input.value));
}

async function executeSparql(queryStr) {
  const headEl = document.getElementById("results-head");
  const bodyEl = document.getElementById("results-body");
  const countEl = document.getElementById("results-count");

  bodyEl.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 2rem;">Executing SPARQL query...</td></tr>`;

  // On GitHub Pages or static host, load compiled aggregation results
  if (isStaticHost()) {
    try {
      const staticData = await fetch("data/water_projects.json").then(r => r.json());
      renderResults(staticData);
      return;
    } catch (err) {
      console.error("Static data fetch failed:", err);
    }
  }

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryStr })
    });
    if (res.ok) {
      const result = await res.json();
      renderResults(result);
      return;
    }
  } catch (e) {
    // API endpoint unavailable
  }

  // Fallback to static result
  try {
    const staticData = await fetch("data/water_projects.json").then(r => r.json());
    renderResults(staticData);
  } catch (err) {
    headEl.innerHTML = `<th>Notice</th>`;
    bodyEl.innerHTML = `<tr><td>Live SPARQL execution requires running <code>server.py</code> locally. Viewing static cached query results.</td></tr>`;
    countEl.textContent = "Static Mode";
  }
}

function renderResults(result) {
  const headEl = document.getElementById("results-head");
  const bodyEl = document.getElementById("results-body");
  const countEl = document.getElementById("results-count");

  if (result.error) {
    headEl.innerHTML = `<th>Error</th>`;
    bodyEl.innerHTML = `<tr><td style="color: #ef4444;">${result.error}</td></tr>`;
    countEl.textContent = "Error";
    return;
  }

  countEl.textContent = `${result.data.length} records`;

  if (result.columns.length === 0) {
    headEl.innerHTML = `<th>Status</th>`;
    bodyEl.innerHTML = `<tr><td>Query executed successfully (no variables returned).</td></tr>`;
    return;
  }

  headEl.innerHTML = result.columns.map(c => `<th>?${c}</th>`).join("");

  if (result.data.length === 0) {
    bodyEl.innerHTML = `<tr><td colspan="${result.columns.length}" style="text-align:center; padding:2rem; color: var(--text-muted);">No matching RDF triples found.</td></tr>`;
    return;
  }

  bodyEl.innerHTML = result.data.map(row => {
    const cells = result.columns.map(c => `<td>${escapeHtml(String(row[c] || ""))}</td>`).join("");
    return `<tr>${cells}</tr>`;
  }).join("");
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
