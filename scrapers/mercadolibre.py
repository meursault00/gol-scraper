"""Scraper de MercadoLibre via API pública REST."""

import logging
import time
from typing import Optional

import requests

import config
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class MercadoLibreScraper(BaseScraper):

    BASE_URL = "https://api.mercadolibre.com/sites/MLA/search"
    PAGE_SIZE = 50
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    @property
    def source_name(self) -> str:
        return "mercadolibre"

    def scrape(self) -> list[dict]:
        """Pagina por la API de búsqueda de ML y retorna listings estandarizados."""
        all_listings = []
        offset = 0
        total = None

        while True:
            params = self._build_params(offset)
            data = self._fetch_page(params)

            if data is None:
                break

            if total is None:
                total = min(data["paging"]["total"], config.MAX_RESULTS_PER_SOURCE)
                logger.info(f"MercadoLibre: {data['paging']['total']} resultados (cap {total})")

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                parsed = self._parse_item(item)
                if parsed:
                    all_listings.append(parsed)

            offset += self.PAGE_SIZE
            if offset >= total:
                break

            time.sleep(config.REQUEST_DELAY_SECONDS)

        logger.info(f"MercadoLibre: {len(all_listings)} listings scrapeados")
        return all_listings

    def _build_params(self, offset: int) -> dict:
        return {
            "q": config.SEARCH_QUERY,
            "category": config.CATEGORY_ID,
            "state": config.STATE_ID,
            "price": f"{config.PRICE_MIN_USD}-{config.PRICE_MAX_USD}",
            "CURRENCY": "USD",
            "offset": offset,
            "limit": self.PAGE_SIZE,
        }

    def _fetch_page(self, params: dict, retry: bool = True) -> Optional[dict]:
        """Hace request HTTP con manejo de errores."""
        try:
            resp = requests.get(self.BASE_URL, params=params, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError:
            if resp.status_code == 429 and retry:
                logger.warning("Rate limited por ML, esperando 30s...")
                time.sleep(30)
                return self._fetch_page(params, retry=False)
            logger.error(f"HTTP error {resp.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request fallido: {e}")
            return None

    def _parse_item(self, item: dict) -> Optional[dict]:
        """Parsea un resultado de búsqueda ML a formato estandarizado."""
        try:
            attrs = {a["id"]: a.get("value_name") for a in item.get("attributes", [])}

            price_usd = item["price"] if item.get("currency_id") == "USD" else None
            price_ars = item["price"] if item.get("currency_id") == "ARS" else None

            address = item.get("address", {})
            city = address.get("city_name", "")
            state = address.get("state_name", "")
            location = ", ".join(filter(None, [city, state]))

            return {
                "external_id": item["id"],
                "title": item["title"],
                "price_usd": price_usd,
                "price_ars": price_ars,
                "year": _parse_int(attrs.get("VEHICLE_YEAR")),
                "km": _parse_int(attrs.get("KILOMETERS")),
                "doors": _parse_int(attrs.get("DOORS")),
                "location": location,
                "url": item["permalink"],
                "thumbnail_url": item.get("thumbnail"),
                "photos": [],
            }
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parseando item {item.get('id', '?')}: {e}")
            return None


def _parse_int(value: Optional[str] = None) -> Optional[int]:
    """Extrae entero de strings como '120000 km' o '2014'."""
    if not value:
        return None
    digits = "".join(c for c in value if c.isdigit())
    return int(digits) if digits else None
