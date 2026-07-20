import requests
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS
import urllib.parse
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# 1. Initialize Graph and Namespaces
g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
g.bind("wb", WB)

# Define Ontology Classes
g.add((WB.Project, RDF.type, RDFS.Class))
g.add((WB.Country, RDF.type, RDFS.Class))
g.add((WB.Sector, RDF.type, RDFS.Class))

# Define Object Properties (The Multi-Hop Edges)
g.add((WB.locatedIn, RDF.type, RDF.Property))
g.add((WB.hasSector, RDF.type, RDF.Property))

# 2. Fetch Live Data from World Bank API
print("Fetching live project data from the World Bank API...")
# We request recent projects in JSON format
url = "https://search.worldbank.org/api/v2/projects?format=json&rows=250"
response = requests.get(url)
data = response.json()

# The API nests the actual project records under the 'projects' key
projects_data = data.get("projects", {})

# 3. Parse and Map to RDF Triples
for proj_id, proj_data in projects_data.items():
    # Skip the API's 'facets' metadata block
    if proj_id == "facets": 
        continue 
        
    # Extract metadata safely
    name = proj_data.get("project_name", "Unknown Project")
    country = proj_data.get("countryshortname", "Unknown Country")
    
    # Create URIs
    project_uri = URIRef(WB + f"Project_{proj_id}")
    country_uri = URIRef(WB + f"Country_{urllib.parse.quote(country.replace(' ', '_'))}")
    
    # Assert Project and Country Nodes
    g.add((project_uri, RDF.type, WB.Project))
    g.add((project_uri, RDFS.label, Literal(name)))
    
    g.add((country_uri, RDF.type, WB.Country))
    g.add((country_uri, RDFS.label, Literal(country)))
    
    # Link Project to Country (Hop 1)
    g.add((project_uri, WB.locatedIn, country_uri))
    
    # Extract and Link Sectors (Hop 2)
    sectors = proj_data.get("sector") or []
    if isinstance(sectors, dict):
        sectors = list(sectors.values())
    elif not isinstance(sectors, list):
        sectors = []
        
    for sector_dict in sectors:
        if isinstance(sector_dict, dict):
            sector_name = sector_dict.get("Name", "Unknown Sector")
        elif isinstance(sector_dict, str):
            sector_name = sector_dict
        else:
            sector_name = "Unknown Sector"
            
        if not sector_name:
            continue

        sector_uri = URIRef(WB + f"Sector_{urllib.parse.quote(sector_name.replace(' ', '_'))}")
        
        g.add((sector_uri, RDF.type, WB.Sector))
        g.add((sector_uri, RDFS.label, Literal(sector_name)))
        
        # Link Project to Sector
        g.add((project_uri, WB.hasSector, sector_uri))

# 4. Serialize the Graph
output_path = "data/world_bank_graph.ttl"
g.serialize(output_path, format="turtle")
print(f"Successfully generated semantic graph with {len(g)} triples at {output_path}")
