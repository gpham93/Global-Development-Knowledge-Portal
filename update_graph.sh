#!/usr/bin/env bash
set -e

echo "=== GLOBAL DEVELOPMENT KNOWLEDGE GRAPH AUTOMATION ==="
echo "[1/4] Paginated Extraction of Active World Bank Projects..."
python3 scripts/build_wb_graph.py

echo ""
echo "[2/4] Executing Scaled SPARQL Aggregation Queries..."
python3 scripts/query_graph.py

echo ""
echo "[3/4] Exporting Static Data for GitHub Pages Portal..."
python3 scripts/export_static_data.py

echo ""
echo "[4/4] Building Website / Quarto Render..."
if command -v quarto &> /dev/null; then
    echo "Rendering site with Quarto..."
    quarto render
else
    echo "Quarto CLI not detected. Static HTML assets and datasets ready in repository root."
fi

echo ""
echo "=== BUILD AUTOMATION COMPLETE ==="
