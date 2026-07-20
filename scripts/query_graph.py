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
print(f"Loaded master graph with {len(g):,} triples.\n")

# 2. Aggregation SPARQL Query: Top 10 Countries by Active Project Volume
query_top_countries = """
PREFIX wb: <http://enterprise.org/ontology/wb#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?countryName (COUNT(DISTINCT ?project) AS ?projectCount)
WHERE {
    ?project a wb:Project ;
             wb:locatedIn ?country .
    ?country rdfs:label ?countryName .
}
GROUP BY ?countryName
ORDER BY DESC(?projectCount)
LIMIT 10
"""

results = g.query(query_top_countries)

print("=== Top 10 Countries by Volume of Active Projects ===")
print(f"{'Rank':<5} | {'Country':<40} | {'Active Projects':<15}")
print("-" * 65)

rank = 1
for row in results:
    c_name = str(row.countryName)
    p_count = int(row.projectCount)
    print(f"{rank:<5} | {c_name:<40} | {p_count:<15}")
    rank += 1

print("-" * 65)
print(f"Aggregation complete over {len(g):,} triples.\n")
