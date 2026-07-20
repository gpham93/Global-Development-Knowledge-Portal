# Global Development Knowledge Graph Portal

A semantic intelligence web portal and RDF Knowledge Graph pipeline for Global Development Management, pulling live data from the **World Bank Projects API** into a strict RDF/OWL ontology.

![Portal Preview](https://img.shields.io/badge/RDF-OWL-blue?style=flat-square) ![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🌟 Overview & Architecture

This repository ingests active World Bank infrastructure projects, maps them into RDF triples, and provides an interactive visual web portal for multi-hop graph exploration and SPARQL querying.

### Ontology Design (`http://enterprise.org/ontology/wb#`)
- **Classes**:
  - `wb:Project`
  - `wb:Country`
  - `wb:Sector`
- **Object Properties**:
  - `wb:locatedIn` (Project → Country)
  - `wb:hasSector` (Project → Sector)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- `rdflib` & `requests`

```bash
pip install rdflib requests
```

### 1. Ingest Data & Build Knowledge Graph
Run the ingestion engine to pull live World Bank project data and serialize it into Turtle (`data/world_bank_graph.ttl`):

```bash
python3 scripts/build_wb_graph.py
```

### 2. Execute SPARQL Queries (CLI)
Run the analytics query engine to discover countries with projects in specific development sectors:

```bash
python3 scripts/query_graph.py
```

### 3. Launch the Local Interactive Portal
Start the live SPARQL API server and web visualizer:

```bash
python3 server.py
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser.

---

## 🌐 GitHub Pages Deployment Guide

To host this repository and interactive portal on **GitHub Pages**:

1. **Initialize Git & Commit Files**:
   ```bash
   git init
   git add .
   git commit -m "Initialize Global Development Knowledge Graph portal"
   ```

2. **Connect to Your GitHub Repository**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

3. **Enable GitHub Pages**:
   - Go to your repository settings on GitHub: **Settings → Pages**.
   - Under **Build and deployment**:
     - **Source**: Select `Deploy from a branch`.
     - **Branch**: Select `main` and folder `/ (root)`.
   - Click **Save**.

Your live portal will be published at:  
`https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

---

## 📜 License
MIT License
