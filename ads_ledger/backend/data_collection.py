import requests


def fetch_wikipedia_summary(title):
    """Fetch summary text from Wikipedia REST API and return text ready for ledger conversion."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("extract", "")


def fetch_dbpedia_summary(resource):
    """Fetch abstract text from DBpedia for a resource such as Roman_Empire."""
    sparql = """
    SELECT ?abstract WHERE {
      dbr:%s dbo:abstract ?abstract .
      FILTER (lang(?abstract) = 'en')
    } LIMIT 1
    """ % resource.replace(" ", "_")
    response = requests.get(
        "https://dbpedia.org/sparql",
        params={"query": sparql, "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    bindings = response.json()["results"]["bindings"]
    return bindings[0]["abstract"]["value"] if bindings else ""


def simulate_seshat_rows():
    """Seshat-style rows: polity, year, variable, value, evidence."""
    return [
        {
            "year": -300,
            "variable": "territorial_integration",
            "value": 78,
            "evidence": "Administrative provinces and road systems supported imperial cohesion.",
        },
        {
            "year": -260,
            "variable": "warfare_intensity",
            "value": 64,
            "evidence": "Large army mobilization increased coercive capacity but created social strain.",
        },
        {
            "year": -240,
            "variable": "moralizing_governance",
            "value": 84,
            "evidence": "Public ethical governance inscriptions encouraged welfare and restraint.",
        },
    ]


def entries_from_historical_rows(civilization_id, rows, source):
    mapping = {
        "territorial_integration": ("Asset", "Governance"),
        "warfare_intensity": ("Liability", "Military"),
        "moralizing_governance": ("Asset", "Governance"),
    }
    entries = []
    for row in rows:
        entry_type, domain = mapping.get(row["variable"], ("Asset", "Social"))
        entries.append(
            {
                "civilization_id": civilization_id,
                "year": int(row["year"]),
                "entry_type": entry_type,
                "domain": domain,
                "value": float(row["value"]),
                "description": row["evidence"],
                "source": source,
            }
        )
    return entries
