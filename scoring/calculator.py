"""Fórmulas de scoring para publicaciones."""

import config


def calculate_score(listing: dict) -> dict:
    """Calcula score ponderado para un listing.

    Returns:
        {"score": float 0-1, "details": {"price": float, "km": float, ...}}
    """
    details = {}
    weights = dict(config.WEIGHTS)

    if not config.ENABLE_PHOTO_ANALYSIS:
        weights.pop("photos", None)
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

    details["price"] = _score_price(listing.get("price_usd"))
    details["km"] = _score_km(listing.get("km"))
    details["year"] = _score_year(listing.get("year"))
    details["doors"] = _score_doors(listing.get("doors"))

    total = sum(weights.get(k, 0) * details[k] for k in details)
    return {"score": round(total, 4), "details": details}


def _score_price(price_usd):
    """Menor precio dentro del rango = mejor score."""
    if price_usd is None:
        return 0.5
    price_range = config.PRICE_MAX_USD - config.PRICE_MIN_USD
    if price_range == 0:
        return 1.0
    clamped = max(config.PRICE_MIN_USD, min(config.PRICE_MAX_USD, price_usd))
    return 1.0 - (clamped - config.PRICE_MIN_USD) / price_range


def _score_km(km):
    """Menos km = mejor score."""
    if km is None:
        return 0.5
    clamped = max(0, min(config.MAX_KM, km))
    return 1.0 - (clamped / config.MAX_KM)


def _score_year(year):
    """Más nuevo = mejor score."""
    if year is None:
        return 0.5
    year_range = config.MAX_YEAR - config.MIN_YEAR
    if year_range == 0:
        return 1.0
    clamped = max(config.MIN_YEAR, min(config.MAX_YEAR, year))
    return (clamped - config.MIN_YEAR) / year_range


def _score_doors(doors):
    """5 puertas preferido."""
    if doors is None:
        return 0.5
    if doors >= 5:
        return 1.0
    if doors == 4:
        return 0.7
    if doors == 3:
        return 0.4
    return 0.3
