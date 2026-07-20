import os
from rdflib import Graph, Namespace, RDF, RDFS

# 1. Initialize Graph and Namespaces
g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
g.bind("wb", WB)

input_path = "data/world_bank_graph.ttl"

if not os.path.exists(input_path):
    print(f"Error: Graph file '{input_path}' not found. Please run scripts/build_wb_graph.py first.")
    exit(1)

print(f"Loading Knowledge Graph from {input_path}...")
g.parse(input_path, format="turtle")
print(f"Loaded graph with {len(g)} triples.\n")

# 2. SPARQL Query to find countries with active projects in Water, sanitation and flood protection related sectors
query = """
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

results = g.query(query)

print("=== Business Question ===")
print("Which countries have active projects operating in the 'Water, sanitation and flood protection' sector?\n")

print(f"{'Country':<30} | {'Project Name':<50} | {'Sector Name':<35}")
print("-" * 120)

count = 0
for row in results:
    count += 1
    c_name = str(row.countryName)
    p_name = str(row.projectName)
    s_name = str(row.sectorName)
    if len(p_name) > 47:
        p_name = p_name[:44] + "..."
    if len(s_name) > 33:
        s_name = s_name[:30] + "..."
    print(f"{c_name:<30} | {p_name:<50} | {s_name:<35}")

print("-" * 120)
print(f"Total matching records found: {count}\n")
