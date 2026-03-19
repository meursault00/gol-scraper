"""Exportar resultados a JSON, CSV y HTML."""

import csv
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "score", "title", "price_usd", "year", "km", "doors",
    "location", "url", "source", "first_seen_at", "last_seen_at",
]


def export_csv(listings: list[dict], path: str = "data/results.csv") -> str:
    """Exporta listings a CSV. Retorna el path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for listing in listings:
            writer.writerow(listing)
    logger.info(f"Exportados {len(listings)} listings a {path}")
    return path


def export_json(listings: list[dict], path: str = "data/results.json") -> str:
    """Exporta listings a JSON. Retorna el path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(listings),
        "listings": listings,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Exportados {len(listings)} listings a {path}")
    return path
