import os
from rdflib import Graph, Namespace, RDF, RDFS

# 1. Initialize Graph and Namespaces
g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
RISK = Namespace("http://enterprise.org/ontology/risk#")

g.bind("wb", WB)
g.bind("risk", RISK)

input_path = "data/master_knowledge_graph.ttl"
if not os.path.exists(input_path):
    input_path = "data/world_bank_graph.ttl"

if not os.path.exists(input_path):
    print(f"Error: Graph file '{input_path}' not found. Please run scripts/build_risk_graph.py first.")
    exit(1)

print(f"Loading Master Knowledge Graph from {input_path}...")
g.parse(input_path, format="turtle")
print(f"Loaded master graph with {len(g):,} triples.\n")

# 2. Executive Multi-Hop SPARQL Risk Query
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

results = g.query(risk_query)

print("=== EXECUTIVE GEOPOLITICAL RISK TRAVERSAL QUERY ===")
print("Question: Which enterprise assets rely on transit routes or jurisdictions impacted by active threat events?\n")

print(f"{'Asset Name':<38} | {'Operating Entity':<28} | {'Transit Route':<30} | {'Threat Event':<45} | {'Severity':<10}")
print("-" * 158)

count = 0
for row in results:
    count += 1
    a_name = str(row.assetName)
    e_name = str(row.entityName)
    r_name = str(row.routeName)
    t_name = str(row.threatLabel)
    sev = str(row.severity)
    
    if len(a_name) > 35: a_name = a_name[:32] + "..."
    if len(e_name) > 25: e_name = e_name[:22] + "..."
    if len(r_name) > 27: r_name = r_name[:24] + "..."
    if len(t_name) > 42: t_name = t_name[:39] + "..."
    
    print(f"{a_name:<38} | {e_name:<28} | {r_name:<30} | {t_name:<45} | {sev:<10}")

print("-" * 158)
print(f"Total High-Risk Asset Exposures Identified: {count}\n")
