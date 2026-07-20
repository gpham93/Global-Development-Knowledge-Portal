import json
import os
from rdflib import Graph, Namespace, RDF, RDFS

g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
g.bind("wb", WB)

DATA_PATH = "data/world_bank_graph.ttl"
OUTPUT_DIR = "public/data"
ROOT_DATA_DIR = "data"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ROOT_DATA_DIR, exist_ok=True)

if not os.path.exists(DATA_PATH):
    print(f"Error: {DATA_PATH} not found.")
    exit(1)

print(f"Loading RDF Graph from {DATA_PATH}...")
g.parse(DATA_PATH, format="turtle")

# 1. Stats
projects_query = "SELECT (COUNT(DISTINCT ?p) AS ?cnt) WHERE { ?p a wb:Project }"
countries_query = "SELECT (COUNT(DISTINCT ?c) AS ?cnt) WHERE { ?c a wb:Country }"
sectors_query = "SELECT (COUNT(DISTINCT ?s) AS ?cnt) WHERE { ?s a wb:Sector }"

proj_cnt = list(g.query(projects_query))[0].cnt.toPython()
country_cnt = list(g.query(countries_query))[0].cnt.toPython()
sector_cnt = list(g.query(sectors_query))[0].cnt.toPython()

stats_data = {
    "triples": len(g),
    "projects": proj_cnt,
    "countries": country_cnt,
    "sectors": sector_cnt
}

# 2. Graph Nodes & Links
graph_query = """
PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?project ?projectName ?country ?countryName ?sector ?sectorName
WHERE {
    ?project a wb:Project ;
             rdfs:label ?projectName ;
             wb:locatedIn ?country ;
             wb:hasSector ?sector .
    ?country rdfs:label ?countryName .
    ?sector rdfs:label ?sectorName .
}
"""
results = g.query(graph_query)
nodes_dict = {}
links = []

for row in results:
    p_uri = str(row.project)
    p_name = str(row.projectName)
    c_uri = str(row.country)
    c_name = str(row.countryName)
    s_uri = str(row.sector)
    s_name = str(row.sectorName)

    if p_uri not in nodes_dict:
        nodes_dict[p_uri] = {"id": p_uri, "name": p_name, "type": "Project"}
    if c_uri not in nodes_dict:
        nodes_dict[c_uri] = {"id": c_uri, "name": c_name, "type": "Country"}
    if s_uri not in nodes_dict:
        nodes_dict[s_uri] = {"id": s_uri, "name": s_name, "type": "Sector"}

    links.append({"source": p_uri, "target": c_uri, "label": "locatedIn"})
    links.append({"source": p_uri, "target": s_uri, "label": "hasSector"})

graph_data = {
    "nodes": list(nodes_dict.values()),
    "links": links
}

# 3. Sectors List
sectors_query = """
PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sectorName (COUNT(DISTINCT ?project) AS ?projectCount)
WHERE {
    ?project a wb:Project ; wb:hasSector ?sector .
    ?sector rdfs:label ?sectorName .
}
GROUP BY ?sectorName
ORDER BY DESC(?projectCount)
"""
sector_results = g.query(sectors_query)
sectors_data = {"sectors": [{"name": str(row.sectorName), "count": int(row.projectCount)} for row in sector_results]}

# 4. Water & Sanitation Query Results
water_query = """
PREFIX wb: <http://enterprise.org/ontology/wb#>
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
"""
water_results = g.query(water_query)
water_data = {
    "columns": ["countryName", "projectName", "sectorName"],
    "data": [{"countryName": str(r.countryName), "projectName": str(r.projectName), "sectorName": str(r.sectorName)} for r in water_results]
}

# Write output files
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

save_json(os.path.join(OUTPUT_DIR, "stats.json"), stats_data)
save_json(os.path.join(OUTPUT_DIR, "graph.json"), graph_data)
save_json(os.path.join(OUTPUT_DIR, "sectors.json"), sectors_data)
save_json(os.path.join(OUTPUT_DIR, "water_projects.json"), water_data)

# Also save copy in root data directory
save_json(os.path.join(ROOT_DATA_DIR, "graph.json"), graph_data)
save_json(os.path.join(ROOT_DATA_DIR, "stats.json"), stats_data)
save_json(os.path.join(ROOT_DATA_DIR, "sectors.json"), sectors_data)
save_json(os.path.join(ROOT_DATA_DIR, "water_projects.json"), water_data)

print("Static data files exported successfully for GitHub Pages hosting!")
