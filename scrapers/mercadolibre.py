"""Scraper de MercadoLibre via scraping web (polycard data)."""

import json
import logging
import re
import time
from typing import Optional

import requests

import config
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# URL de búsqueda web de ML autos
_SEARCH_URL = (
    "https://autos.mercadolibre.com.ar/volkswagen/gol/"
    "_PriceRange_{min}USD-{max}USD_NoIndex_True"
)


class MercadoLibreScraper(BaseScraper):

    ITEMS_PER_PAGE = 48
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-419,es;q=0.9",
    }

    @property
    def source_name(self) -> str:
        return "mercadolibre"

    def scrape(self) -> list[dict]:
        """Scrapea la web de ML extrayendo datos de polycards."""
        all_listings = []
        page = 1

        while True:
            url = self._build_url(page)
            cards = self._fetch_page(url)

            if cards is None or not cards:
                if page == 1:
                    logger.warning("MercadoLibre: no se encontraron listings")
                break

            for card in cards:
                parsed = self._parse_polycard(card)
                if parsed:
                    all_listings.append(parsed)

            if len(cards) < self.ITEMS_PER_PAGE:
                break

            page += 1
            if len(all_listings) >= config.MAX_RESULTS_PER_SOURCE:
                break

            time.sleep(config.REQUEST_DELAY_SECONDS)

        logger.info(f"MercadoLibre: {len(all_listings)} listings scrapeados")
        return all_listings

    def _build_url(self, page: int) -> str:
        base = _SEARCH_URL.format(
            min=config.PRICE_MIN_USD,
            max=config.PRICE_MAX_USD,
        )
        if page > 1:
            offset = (page - 1) * self.ITEMS_PER_PAGE + 1
            base += f"_Desde_{offset}"
        return base

    def _fetch_page(self, url: str) -> Optional[list[dict]]:
        """Descarga la página y extrae polycards."""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            return self._extract_polycards(resp.text)
        except requests.exceptions.HTTPError:
            if resp.status_code == 429:
                logger.warning("Rate limited por ML, esperando 30s...")
                time.sleep(30)
                try:
                    resp = requests.get(url, headers=self.HEADERS, timeout=15)
                    resp.raise_for_status()
                    return self._extract_polycards(resp.text)
                except Exception:
                    pass
            logger.error(f"HTTP error {resp.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request fallido: {e}")
            return None

    def _extract_polycards(self, html: str) -> list[dict]:
        """Extrae datos de polycards embebidos en el HTML de búsqueda de ML.

        ML renderiza los resultados como componentes 'polycard' con metadata
        y componentes (title, price, attributes_list, location) en JSON inline.
        """
        cards = []

        # Buscar bloques de polycard con metadata
        for match in re.finditer(
            r'"polycard"\s*:\s*\{',
            html,
        ):
            start = match.start() + len('"polycard":')
            block = _extract_balanced(html, start, "{", "}")
            if not block:
                continue
            try:
                card = json.loads(block)
                if card.get("metadata", {}).get("id"):
                    cards.append(card)
            except json.JSONDecodeError:
                continue

        return cards

    def _parse_polycard(self, card: dict) -> Optional[dict]:
        """Parsea un polycard de ML a formato estandarizado."""
        try:
            meta = card.get("metadata", {})
            external_id = meta.get("id", "")
            url_path = meta.get("url", "")
            url = f"https://{url_path}" if url_path and not url_path.startswith("http") else url_path

            # Extraer componentes
            components = {c["type"]: c for c in card.get("components", []) if "type" in c}

            # Título
            title_comp = components.get("title", {})
            title = title_comp.get("title", {}).get("text", "")

            # Precio
            price_comp = components.get("price", {})
            current = price_comp.get("price", {}).get("current_price", {})
            price_value = current.get("value")
            currency = current.get("currency", "ARS")

            price_usd = price_value if currency == "USD" else None
            price_ars = price_value if currency == "ARS" else None

            # Atributos (año, km)
            attrs_comp = components.get("attributes_list", {})
            attrs_texts = attrs_comp.get("attributes_list", {}).get("texts", [])
            year = None
            km = None
            for text in attrs_texts:
                if re.match(r"^\d{4}$", text.strip()):
                    year = int(text.strip())
                elif "km" in text.lower():
                    km = _parse_int(text)

            # Ubicación
            loc_comp = components.get("location", {})
            location = loc_comp.get("location", {}).get("text", "")

            # Thumbnail
            pics = card.get("pictures", {}).get("pictures", [])
            thumbnail = None
            if pics:
                pic_id = pics[0].get("id", "")
                if pic_id:
                    thumbnail = f"https://http2.mlstatic.com/D_NQ_NP_{pic_id}-O.webp"

            if not external_id or not url:
                return None

            return {
                "external_id": external_id,
                "title": title,
                "price_usd": price_usd,
                "price_ars": price_ars,
                "year": year,
                "km": km,
                "doors": None,
                "location": location,
                "url": url,
                "thumbnail_url": thumbnail,
                "photos": [],
            }
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parseando polycard: {e}")
            return None


def _parse_int(value: Optional[str] = None) -> Optional[int]:
    """Extrae entero de strings como '120.000 Km' o '2014'."""
    if not value:
        return None
    digits = "".join(c for c in str(value) if c.isdigit())
    return int(digits) if digits else None


def _extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Optional[str]:
    """Extrae un bloque balanceado de open_ch/close_ch desde start."""
    idx = text.find(open_ch, start)
    if idx == -1 or idx > start + 10:
        return None
    start = idx

    depth = 0
    in_string = False
    escape = False
    for i in range(start, min(start + 200_000, len(text))):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None
