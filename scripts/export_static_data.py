import json
import os
from rdflib import Graph, Namespace, RDF, RDFS

g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
RISK = Namespace("http://enterprise.org/ontology/risk#")

g.bind("wb", WB)
g.bind("risk", RISK)

DATA_PATH = "data/master_knowledge_graph.ttl"
if not os.path.exists(DATA_PATH):
    DATA_PATH = "data/world_bank_graph.ttl"

OUTPUT_DIR = "public/data"
ROOT_DATA_DIR = "data"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ROOT_DATA_DIR, exist_ok=True)

if not os.path.exists(DATA_PATH):
    print(f"Error: {DATA_PATH} not found.")
    exit(1)

print(f"Exporting master static data from {DATA_PATH}...")
g.parse(DATA_PATH, format="turtle")

# 1. Stats
projects_query = "SELECT (COUNT(DISTINCT ?p) AS ?cnt) WHERE { ?p a wb:Project }"
countries_query = "SELECT (COUNT(DISTINCT ?c) AS ?cnt) WHERE { ?c a wb:Country }"
sectors_query = "SELECT (COUNT(DISTINCT ?s) AS ?cnt) WHERE { ?s a wb:Sector }"
assets_query = "SELECT (COUNT(DISTINCT ?a) AS ?cnt) WHERE { ?a a risk:Asset }"
threats_query = "SELECT (COUNT(DISTINCT ?t) AS ?cnt) WHERE { ?t a risk:ThreatEvent }"

proj_cnt = list(g.query(projects_query))[0].cnt.toPython()
country_cnt = list(g.query(countries_query))[0].cnt.toPython()
sector_cnt = list(g.query(sectors_query))[0].cnt.toPython()
asset_cnt = list(g.query(assets_query))[0].cnt.toPython()
threat_cnt = list(g.query(threats_query))[0].cnt.toPython()

stats_data = {
    "triples": len(g),
    "projects": proj_cnt,
    "countries": country_cnt,
    "sectors": sector_cnt,
    "assets": asset_cnt,
    "threats": threat_cnt
}

# 2. All Triples Export for In-Browser SPARQL Engine
all_triples = []
labels = {}

for s, p, o in g:
    s_str = str(s)
    p_str = str(p)
    o_str = str(o)
    
    if p == RDFS.label:
        labels[s_str] = o_str
        
    all_triples.append({
        "s": s_str,
        "p": p_str,
        "o": o_str
    })

# 3. Graph Nodes & Links for D3 Visualizer (Includes WB Projects + Risk Layer)
graph_query = """
PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX risk: <http://enterprise.org/ontology/risk#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?subjectName ?type ?object ?objectName ?pred
WHERE {
    {
        ?subject a wb:Project ; rdfs:label ?subjectName ; wb:locatedIn ?object .
        ?object rdfs:label ?objectName .
        BIND("Project" AS ?type)
        BIND("locatedIn" AS ?pred)
    }
    UNION
    {
        ?subject a risk:Asset ; rdfs:label ?subjectName ; risk:reliesOn ?object .
        ?object rdfs:label ?objectName .
        BIND("Asset" AS ?type)
        BIND("reliesOn" AS ?pred)
    }
    UNION
    {
        ?subject a risk:ThreatEvent ; rdfs:label ?subjectName ; risk:impacts ?object .
        ?object rdfs:label ?objectName .
        BIND("ThreatEvent" AS ?type)
        BIND("impacts" AS ?pred)
    }
}
LIMIT 450
"""
results = g.query(graph_query)
nodes_dict = {}
links = []

for row in results:
    s_uri = str(row.subject)
    s_name = str(row.subjectName)
    s_type = str(row.type)
    o_uri = str(row.object)
    o_name = str(row.objectName)
    pred = str(row.pred)

    if s_uri not in nodes_dict:
        nodes_dict[s_uri] = {"id": s_uri, "name": s_name, "type": s_type}
    if o_uri not in nodes_dict:
        o_type = "Country" if "Country" in o_uri else "TransitRoute" if "Route" in o_uri else "Sector"
        nodes_dict[o_uri] = {"id": o_uri, "name": o_name, "type": o_type}

    links.append({"source": s_uri, "target": o_uri, "label": pred})

graph_data = {
    "nodes": list(nodes_dict.values()),
    "links": links
}

# 4. Multi-Hop Risk Traversal SPARQL Query Results
risk_query = """
PREFIX wb: <http://enterprise.org/ontology/wb#>
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
ORDER BY DESC(?severity) ?assetName
"""
risk_results = g.query(risk_query)
risk_data = {
    "columns": ["assetName", "entityName", "routeName", "threatLabel", "severity"],
    "data": [
        {
            "assetName": str(r.assetName),
            "entityName": str(r.entityName),
            "routeName": str(r.routeName),
            "threatLabel": str(r.threatLabel),
            "severity": str(r.severity)
        }
        for r in risk_results
    ]
}

# 5. Sectors Aggregations
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
LIMIT 24
"""
sector_results = g.query(sectors_query)
sectors_data = {"sectors": [{"name": str(row.sectorName), "count": int(row.projectCount)} for row in sector_results]}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

triples_payload = {
    "stats": stats_data,
    "labels": labels,
    "triples": all_triples
}

save_json(os.path.join(OUTPUT_DIR, "stats.json"), stats_data)
save_json(os.path.join(OUTPUT_DIR, "graph.json"), graph_data)
save_json(os.path.join(OUTPUT_DIR, "sectors.json"), sectors_data)
save_json(os.path.join(OUTPUT_DIR, "all_triples.json"), triples_payload)
save_json(os.path.join(OUTPUT_DIR, "risk_exposures.json"), risk_data)
save_json(os.path.join(OUTPUT_DIR, "water_projects.json"), risk_data) # fallback preset default

save_json(os.path.join(ROOT_DATA_DIR, "stats.json"), stats_data)
save_json(os.path.join(ROOT_DATA_DIR, "graph.json"), graph_data)
save_json(os.path.join(ROOT_DATA_DIR, "sectors.json"), sectors_data)
save_json(os.path.join(ROOT_DATA_DIR, "all_triples.json"), triples_payload)
save_json(os.path.join(ROOT_DATA_DIR, "risk_exposures.json"), risk_data)
save_json(os.path.join(ROOT_DATA_DIR, "water_projects.json"), risk_data)

print(f"Exported Master Graph with {len(all_triples):,} triples and Geopolitical Risk Data!")
