"""Conversión ARS → USD usando cotización blue/MEP."""

import logging
import time
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

_cache: dict = {"rate": None, "fetched_at": 0.0}
CACHE_TTL_SECONDS = 3600  # 1 hora


def get_blue_rate() -> Optional[float]:
    """Obtiene cotización del dólar blue (venta) desde dolarapi.com.

    Cachea el resultado por 1 hora para no saturar la API.
    """
    now = time.time()
    if _cache["rate"] and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["rate"]

    try:
        resp = requests.get(config.DOLAR_API_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        rate = data.get("venta")
        if rate and float(rate) > 0:
            _cache["rate"] = float(rate)
            _cache["fetched_at"] = now
            logger.info(f"Cotización dólar blue: ${_cache['rate']}")
            return _cache["rate"]

        logger.warning(f"Respuesta inesperada de dolarapi: {data}")
        return _cache["rate"]  # retorna cache viejo si existe

    except requests.exceptions.RequestException as e:
        logger.error(f"Error obteniendo cotización: {e}")
        return _cache["rate"]


def ars_to_usd(amount_ars: float) -> Optional[float]:
    """Convierte un monto en ARS a USD usando cotización blue."""
    rate = get_blue_rate()
    if rate is None or rate == 0:
        return None
    return round(amount_ars / rate, 2)


def convert_listings(listings: list[dict]) -> list[dict]:
    """Convierte price_ars a price_usd en listings que no tienen precio en USD."""
    converted = 0
    for listing in listings:
        if listing.get("price_usd") is None and listing.get("price_ars"):
            usd = ars_to_usd(listing["price_ars"])
            if usd is not None:
                listing["price_usd"] = usd
                converted += 1

    if converted:
        logger.info(f"Convertidos {converted} precios ARS → USD")
    return listings
