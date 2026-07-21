import http.server
import socketserver
import json
import os
import urllib.parse
from rdflib import Graph, Namespace

PORT = 8080

print("Loading Master Knowledge Graph into rdflib in memory...")
g = Graph()

DATA_PATH = "data/master_knowledge_graph.ttl"
if not os.path.exists(DATA_PATH):
    DATA_PATH = "data/world_bank_graph.ttl"

if os.path.exists(DATA_PATH):
    g.parse(DATA_PATH, format="turtle")
    print(f"Loaded {len(g):,} RDF triples from {DATA_PATH}.")
else:
    print("Warning: No graph turtle file found.")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="public", **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            stats_path = "data/stats.json"
            if os.path.exists(stats_path):
                with open(stats_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                resp = {"triples": len(g), "projects": 0, "countries": 0, "sectors": 0}
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if parsed.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            health_path = "data/api_health.json"
            if os.path.exists(health_path):
                with open(health_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                resp = {"status": "HEALTHY", "http_code": 200, "triple_count": len(g)}
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if parsed.path == "/api/graph":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            graph_path = "data/graph.json"
            if os.path.exists(graph_path):
                with open(graph_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"nodes": [], "links": []}).encode("utf-8"))
            return

        if parsed.path == "/api/sectors":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            sectors_path = "data/sectors.json"
            if os.path.exists(sectors_path):
                with open(sectors_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"sectors": []}).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/query":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                payload = json.loads(body)
                query_str = payload.get("query", "")
                
                results = g.query(query_str)
                columns = [str(var) for var in results.vars] if results.vars else []
                
                rows = []
                for row in results:
                    row_dict = {}
                    for col in columns:
                        val = getattr(row, col, None)
                        row_dict[col] = str(val) if val is not None else ""
                    rows.append(row_dict)
                    
                resp = {
                    "columns": columns,
                    "data": rows
                }
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode("utf-8"))
                
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_error(444, "Not Found")

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    print(f"Serving Knowledge Graph Portal on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
