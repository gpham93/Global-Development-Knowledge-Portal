import os
import requests
import urllib.parse
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS

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

# Define Object Properties
g.add((WB.locatedIn, RDF.type, RDF.Property))
g.add((WB.hasSector, RDF.type, RDF.Property))

# 2. Paginated Extraction from World Bank API
print("Starting paginated extraction of Active projects from World Bank API...")

rows_per_batch = 500
offset = 0
batch_num = 1
total_projects = None
processed_projects = 0

while True:
    url = f"https://search.worldbank.org/api/v2/projects?format=json&status=Active&rows={rows_per_batch}&os={offset}"
    print(f"Fetching batch {batch_num} (rows {offset + 1} - {offset + rows_per_batch})...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching batch {batch_num} at offset {offset}: {e}")
        break

    if total_projects is None:
        try:
            total_projects = int(data.get("total", 0))
            print(f"Total Active Projects reported by API: {total_projects}")
        except (ValueError, TypeError):
            total_projects = 0

    projects_data = data.get("projects", {})
    if not isinstance(projects_data, dict) or not projects_data:
        print("No more project data returned in this batch.")
        break

    batch_project_count = 0
    for proj_id, proj_data in projects_data.items():
        if proj_id == "facets" or not isinstance(proj_data, dict):
            continue

        status = str(proj_data.get("status", "")).strip()
        status_display = str(proj_data.get("projectstatusdisplay", "")).strip()

        # Strict active check
        if status and status.lower() != "active" and status_display.lower() != "active":
            continue

        name = proj_data.get("project_name", "Unknown Project")
        country = proj_data.get("countryshortname") or proj_data.get("countryname") or "Unknown Country"

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
                sector_name = sector_dict.get("Name", "")
            elif isinstance(sector_dict, str):
                sector_name = sector_dict
            else:
                sector_name = ""

            sector_name = sector_name.strip()
            if not sector_name or sector_name.lower() == "unknown sector":
                continue

            sector_uri = URIRef(WB + f"Sector_{urllib.parse.quote(sector_name.replace(' ', '_'))}")
            g.add((sector_uri, RDF.type, WB.Sector))
            g.add((sector_uri, RDFS.label, Literal(sector_name)))

            # Link Project to Sector
            g.add((project_uri, WB.hasSector, sector_uri))

        batch_project_count += 1

    processed_projects += batch_project_count
    print(f"Batch {batch_num} complete. Added {batch_project_count} active projects to graph.")

    offset += rows_per_batch
    batch_num += 1

    if total_projects and offset >= total_projects:
        break

# 3. Serialize Master Graph
output_path = "data/world_bank_graph.ttl"
print(f"Serializing master graph to {output_path}...")
g.serialize(output_path, format="turtle")
print(f"\nSuccessfully generated master semantic graph with {len(g):,} triples across {processed_projects:,} active projects at {output_path}")
