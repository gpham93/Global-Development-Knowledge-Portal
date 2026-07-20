import os
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from rdflib import Graph, Namespace, RDF, RDFS

# Initialize Graph and load TTL data
g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
g.bind("wb", WB)

DATA_PATH = "data/world_bank_graph.ttl"
PUBLIC_DIR = "public"

def load_graph():
    if os.path.exists(DATA_PATH):
        print(f"Loading RDF Graph from {DATA_PATH}...")
        g.parse(DATA_PATH, format="turtle")
        print(f"Graph loaded successfully with {len(g)} triples.")
    else:
        print(f"Warning: {DATA_PATH} not found. Run scripts/build_wb_graph.py first.")

class PortalRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/stats":
            self.handle_stats()
        elif self.path == "/api/graph":
            self.handle_graph()
        elif self.path == "/api/sectors":
            self.handle_sectors()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/query":
            self.handle_sparql_query()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_stats(self):
        projects_query = "SELECT (COUNT(DISTINCT ?p) AS ?cnt) WHERE { ?p a wb:Project }"
        countries_query = "SELECT (COUNT(DISTINCT ?c) AS ?cnt) WHERE { ?c a wb:Country }"
        sectors_query = "SELECT (COUNT(DISTINCT ?s) AS ?cnt) WHERE { ?s a wb:Sector }"
        
        proj_cnt = list(g.query(projects_query))[0].cnt.toPython()
        country_cnt = list(g.query(countries_query))[0].cnt.toPython()
        sector_cnt = list(g.query(sectors_query))[0].cnt.toPython()

        data = {
            "triples": len(g),
            "projects": proj_cnt,
            "countries": country_cnt,
            "sectors": sector_cnt
        }
        self.send_json_response(data)

    def handle_graph(self):
        # Query nodes and edges for D3 visualization
        query = """
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
        results = g.query(query)
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

        data = {
            "nodes": list(nodes_dict.values()),
            "links": links
        }
        self.send_json_response(data)

    def handle_sectors(self):
        query = """
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
        results = g.query(query)
        sectors = [{"name": str(row.sectorName), "count": int(row.projectCount)} for row in results]
        self.send_json_response({"sectors": sectors})

    def handle_sparql_query(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            body = json.loads(post_data)
            sparql = body.get("query", "")
            results = g.query(sparql)
            
            vars_list = [str(v) for v in results.vars] if results.vars else []
            rows = []
            for r in results:
                row_dict = {}
                for v in vars_list:
                    val = getattr(r, v, None)
                    row_dict[v] = str(val) if val is not None else ""
                rows.append(row_dict)

            self.send_json_response({"columns": vars_list, "data": rows})
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=400)

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

if __name__ == "__main__":
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    load_graph()
    port = 8080
    server = HTTPServer(("0.0.0.0", port), PortalRequestHandler)
    print(f"Server started on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
