#!/usr/bin/env bash
set -e

echo "=== GLOBAL DEVELOPMENT & RISK KNOWLEDGE GRAPH BUILD PIPELINE ==="

echo "[1/5] Ingesting World Bank Projects..."
python3 scripts/build_wb_graph.py

echo ""
echo "[2/5] Ingesting Geopolitical Threat Feed & Enterprise Asset Layer..."
python3 scripts/build_risk_graph.py

echo ""
echo "[3/5] Running World Bank Analytics Aggregation Query..."
python3 scripts/query_graph.py

echo ""
echo "[4/5] Running Executive Multi-Hop Geopolitical Risk Query..."
python3 scripts/query_risk_graph.py

echo ""
echo "[5/5] Exporting Static Graph Assets for GitHub Pages Portal..."
python3 scripts/export_static_data.py

echo ""
echo "=== BUILD & PIPELINE AUTOMATION COMPLETE ==="
