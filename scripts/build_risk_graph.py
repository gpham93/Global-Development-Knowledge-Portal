import json
import os
import urllib.parse
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# 1. Initialize Graph and Namespaces
g = Graph()
WB = Namespace("http://enterprise.org/ontology/wb#")
RISK = Namespace("http://enterprise.org/ontology/risk#")

g.bind("wb", WB)
g.bind("risk", RISK)

# Load existing World Bank Graph if available to create unified Master Graph
MASTER_GRAPH_PATH = "data/master_knowledge_graph.ttl"
WB_GRAPH_PATH = "data/world_bank_graph.ttl"

if os.path.exists(WB_GRAPH_PATH):
    print(f"Loading existing World Bank graph from {WB_GRAPH_PATH}...")
    try:
        g.parse(WB_GRAPH_PATH, format="turtle")
        print(f"Loaded base graph with {len(g):,} triples.")
    except Exception as e:
        print(f"Warning: Could not parse existing WB graph: {e}")

# Define Risk Ontology Classes
g.add((RISK.Asset, RDF.type, RDFS.Class))
g.add((RISK.TransitRoute, RDF.type, RDFS.Class))
g.add((RISK.ThreatEvent, RDF.type, RDFS.Class))
g.add((RISK.CorporateEntity, RDF.type, RDFS.Class))

# Define Risk Object Properties
g.add((RISK.reliesOn, RDF.type, RDF.Property))
g.add((RISK.operatedBy, RDF.type, RDF.Property))
g.add((RISK.impacts, RDF.type, RDF.Property))
g.add((RISK.locatedIn, RDF.type, RDF.Property))

# Data Properties
g.add((RISK.eventDate, RDF.type, RDF.Property))
g.add((RISK.eventType, RDF.type, RDF.Property))
g.add((RISK.severity, RDF.type, RDF.Property))
g.add((RISK.location, RDF.type, RDF.Property))

print("Populating Enterprise Assets, Operating Entities, and Transit Routes...")

# 2. Define Corporate Entities & Enterprise Assets
CORPORATE_ENTITIES = [
    {"id": "ENT_01", "name": "Global Logistics Corp"},
    {"id": "ENT_02", "name": "Apex Supply Chains"},
    {"id": "ENT_03", "name": "Levant Infrastructure Group"},
    {"id": "ENT_04", "name": "Red Sea Energy & Maritime Co."},
    {"id": "ENT_05", "name": "Indo-Pacific Commodities Ltd."}
]

TRANSIT_ROUTES = [
    {"id": "TR_RED_SEA", "name": "Red Sea Shipping Lane", "region": "Middle East / North Africa"},
    {"id": "TR_BLACK_SEA", "name": "Black Sea Maritime Route", "region": "Eastern Europe"},
    {"id": "TR_MALACCA", "name": "Strait of Malacca Corridor", "region": "Southeast Asia"},
    {"id": "TR_SUEZ", "name": "Suez Canal Transit", "region": "Egypt / Middle East"},
    {"id": "TR_HORMUZ", "name": "Strait of Hormuz Route", "region": "Persian Gulf"}
]

ENTERPRISE_ASSETS = [
    {
        "id": "AST_001",
        "name": "Bab-el-Mandeb Oil & Container Terminal",
        "entity_id": "ENT_01",
        "route_id": "TR_RED_SEA",
        "country": "Yemen"
    },
    {
        "id": "AST_002",
        "name": "Odesa Black Sea Grain Hub",
        "entity_id": "ENT_03",
        "route_id": "TR_BLACK_SEA",
        "country": "Ukraine"
    },
    {
        "id": "AST_003",
        "name": "Singapore Strait Transshipment Facility",
        "entity_id": "ENT_02",
        "route_id": "TR_MALACCA",
        "country": "Singapore"
    },
    {
        "id": "AST_004",
        "name": "Port Said Logistics Gateway",
        "entity_id": "ENT_04",
        "route_id": "TR_SUEZ",
        "country": "Egypt"
    },
    {
        "id": "AST_005",
        "name": "Fujairah LNG Bunkering Hub",
        "entity_id": "ENT_05",
        "route_id": "TR_HORMUZ",
        "country": "United Arab Emirates"
    }
]

# Assert Corporate Entities
for ent in CORPORATE_ENTITIES:
    ent_uri = URIRef(RISK + f"Entity_{ent['id']}")
    g.add((ent_uri, RDF.type, RISK.CorporateEntity))
    g.add((ent_uri, RDFS.label, Literal(ent["name"])))

# Assert Transit Routes
for tr in TRANSIT_ROUTES:
    tr_uri = URIRef(RISK + f"Route_{tr['id']}")
    g.add((tr_uri, RDF.type, RISK.TransitRoute))
    g.add((tr_uri, RDFS.label, Literal(tr["name"])))

# Assert Enterprise Assets & Relationships
for ast in ENTERPRISE_ASSETS:
    ast_uri = URIRef(RISK + f"Asset_{ast['id']}")
    ent_uri = URIRef(RISK + f"Entity_{ast['entity_id']}")
    tr_uri = URIRef(RISK + f"Route_{ast['route_id']}")
    country_uri = URIRef(WB + f"Country_{urllib.parse.quote(ast['country'].replace(' ', '_'))}")

    g.add((ast_uri, RDF.type, RISK.Asset))
    g.add((ast_uri, RDFS.label, Literal(ast["name"])))
    g.add((ast_uri, RISK.operatedBy, ent_uri))
    g.add((ast_uri, RISK.reliesOn, tr_uri))
    g.add((ast_uri, RISK.locatedIn, country_uri))

# 3. Geopolitical Threat Event Feed (ACLED Format Ingestion)
GEOPOLITICAL_EVENTS_FEED = [
    {
        "event_id": "EVT_2026_001",
        "event_type": "Maritime Armed Conflict / Drone Strike",
        "event_date": "2026-07-15",
        "severity": "High",
        "location": "Red Sea Shipping Lane",
        "impacted_route": "TR_RED_SEA",
        "impacted_country": "Yemen",
        "label": "Red Sea Anti-Ship Missile & Maritime Drone Attack"
    },
    {
        "event_id": "EVT_2026_002",
        "event_type": "Military Blockade & Naval Mining",
        "event_date": "2026-07-18",
        "severity": "Critical",
        "location": "Black Sea Maritime Corridor",
        "impacted_route": "TR_BLACK_SEA",
        "impacted_country": "Ukraine",
        "label": "Black Sea Port Blockade & Floating Mine Hazard Alert"
    },
    {
        "event_id": "EVT_2026_003",
        "event_type": "Naval Tanker Interception",
        "event_date": "2026-07-10",
        "severity": "High",
        "location": "Strait of Hormuz",
        "impacted_route": "TR_HORMUZ",
        "impacted_country": "United Arab Emirates",
        "label": "Strait of Hormuz Military Confrontation & Tanker Detainment"
    },
    {
        "event_id": "EVT_2026_004",
        "event_type": "Infrastructure Cyber Disruption",
        "event_date": "2026-07-12",
        "severity": "Medium",
        "location": "Suez Canal Corridor",
        "impacted_route": "TR_SUEZ",
        "impacted_country": "Egypt",
        "label": "Suez Canal Traffic Control Cyber Incident"
    },
    {
        "event_id": "EVT_2026_005",
        "event_type": "Piracy & Boarding Incident",
        "event_date": "2026-07-14",
        "severity": "Medium",
        "location": "Strait of Malacca",
        "impacted_route": "TR_MALACCA",
        "impacted_country": "Singapore",
        "label": "Strait of Malacca Coastal Armed Boarding Event"
    }
]

print("Ingesting Geopolitical Threat Event Feed into RDF Graph...")
processed_events = 0

for event_entry in GEOPOLITICAL_EVENTS_FEED:
    try:
        event_id = event_entry.get("event_id")
        if not event_id:
            print("Warning: Missing event_id in event record, skipping.")
            continue

        label = event_entry.get("label", "Geopolitical Threat Event")
        event_type = event_entry.get("event_type", "Unknown Threat")
        event_date = event_entry.get("event_date", "2026-01-01")
        severity = event_entry.get("severity", "Medium")
        location = event_entry.get("location", "Unknown Location")
        impacted_route = event_entry.get("impacted_route")
        impacted_country = event_entry.get("impacted_country")

        event_uri = URIRef(RISK + f"Threat_{event_id}")
        g.add((event_uri, RDF.type, RISK.ThreatEvent))
        g.add((event_uri, RDFS.label, Literal(label)))
        g.add((event_uri, RISK.eventType, Literal(event_type)))
        g.add((event_uri, RISK.eventDate, Literal(event_date)))
        g.add((event_uri, RISK.severity, Literal(severity)))
        g.add((event_uri, RISK.location, Literal(location)))

        # Link ThreatEvent to impacted TransitRoute
        if impacted_route:
            tr_uri = URIRef(RISK + f"Route_{impacted_route}")
            g.add((event_uri, RISK.impacts, tr_uri))

        # Link ThreatEvent to Country
        if impacted_country:
            c_uri = URIRef(WB + f"Country_{urllib.parse.quote(impacted_country.replace(' ', '_'))}")
            g.add((event_uri, RISK.impacts, c_uri))
            g.add((event_uri, RISK.locatedIn, c_uri))

        processed_events += 1

    except Exception as e:
        print(f"Warning: Exception while processing threat event entry '{event_entry}': {e}")

# 4. Serialize Master Graph
print(f"Serializing unified master graph to {MASTER_GRAPH_PATH} and {WB_GRAPH_PATH}...")
g.serialize(MASTER_GRAPH_PATH, format="turtle")
g.serialize(WB_GRAPH_PATH, format="turtle")

print(f"Successfully generated Geopolitical Risk Layer with {processed_events} threat events. Master graph contains {len(g):,} total triples.")
