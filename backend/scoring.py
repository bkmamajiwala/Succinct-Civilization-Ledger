from collections import defaultdict

import numpy as np
from sklearn.linear_model import LinearRegression


DOMAIN_WEIGHTS = {
    "Economic": 0.30,
    "Military": 0.25,
    "Governance": 0.20,
    "Scientific": 0.15,
    "Social": 0.10,
}


def compute_weighted_score(entries):
    weighted_assets = 0.0
    weighted_liabilities = 0.0
    raw_assets = 0.0
    raw_liabilities = 0.0
    domain_breakdown = defaultdict(lambda: {"assets": 0.0, "liabilities": 0.0, "weighted": 0.0})

    for entry in entries:
        value = float(entry["value"])
        weight = DOMAIN_WEIGHTS.get(entry["domain"], 0.1)
        signed = value if entry["entry_type"] == "Asset" else -value
        domain_breakdown[entry["domain"]]["weighted"] += signed * weight
        if entry["entry_type"] == "Asset":
            raw_assets += value
            weighted_assets += value * weight
            domain_breakdown[entry["domain"]]["assets"] += value
        else:
            raw_liabilities += value
            weighted_liabilities += value * weight
            domain_breakdown[entry["domain"]]["liabilities"] += value

    stability = raw_assets - raw_liabilities
    weighted_score = weighted_assets - weighted_liabilities
    return {
        "formula": "Civilization Stability = Total Assets - Total Liabilities",
        "total_assets": round(raw_assets, 2),
        "total_liabilities": round(raw_liabilities, 2),
        "stability": round(stability, 2),
        "weighted_assets": round(weighted_assets, 2),
        "weighted_liabilities": round(weighted_liabilities, 2),
        "ai_weighted_score": round(weighted_score, 2),
        "weights": DOMAIN_WEIGHTS,
        "domain_breakdown": dict(domain_breakdown),
    }


def learn_weights_from_examples(examples):
    """Learn domain weights from labeled stability examples using regression."""
    if len(examples) < 2:
        return {"error": "Provide at least two examples with domain totals and target_score."}
    domains = list(DOMAIN_WEIGHTS)
    x, y = [], []
    for item in examples:
        x.append([float(item.get(domain, 0)) for domain in domains])
        y.append(float(item["target_score"]))
    model = LinearRegression(positive=True)
    model.fit(np.array(x), np.array(y))
    total = model.coef_.sum() or 1
    learned = {domain: round(float(weight / total), 3) for domain, weight in zip(domains, model.coef_)}
    return {"learned_weights": learned, "intercept": round(float(model.intercept_), 3)}
