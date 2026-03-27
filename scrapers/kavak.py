"""Scraper de Kavak via scraping de página con datos embebidos."""

import logging
import re
import json
import time
from typing import Optional

import requests

import config
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class KavakScraper(BaseScraper):

    BASE_URL = "https://www.kavak.com/ar/usados/volkswagen-gol"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9",
    }

    @property
    def source_name(self) -> str:
        return "kavak"

    def scrape(self) -> list[dict]:
        """Scrapea listings de Kavak parseando datos embebidos en el HTML."""
        all_listings = []
        page = 1

        while True:
            url = self.BASE_URL if page == 1 else f"{self.BASE_URL}?page={page}"
            data = self._fetch_page(url)

            if data is None:
                break

            cars = data.get("cars", [])
            if not cars:
                break

            for car in cars:
                parsed = self._parse_item(car)
                if parsed:
                    all_listings.append(parsed)

            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break

            page += 1
            if len(all_listings) >= config.MAX_RESULTS_PER_SOURCE:
                break

            time.sleep(config.REQUEST_DELAY_SECONDS)

        logger.info(f"Kavak: {len(all_listings)} listings scrapeados")
        return all_listings

    def _fetch_page(self, url: str) -> Optional[dict]:
        """Descarga la página y extrae datos JSON embebidos."""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            return self._extract_data(resp.text)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request fallido para Kavak: {e}")
            return None

    def _extract_data(self, html: str) -> Optional[dict]:
        """Extrae datos de listings del HTML de Kavak.

        Kavak usa Next.js streaming (self.__next_f.push()) en vez del
        clásico __NEXT_DATA__. Los datos de autos vienen embebidos en
        esos chunks como JSON serializado.
        """
        # Método 1: Buscar __NEXT_DATA__ clásico
        match = re.search(
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if match:
            try:
                next_data = json.loads(match.group(1))
                page_props = next_data.get("props", {}).get("pageProps", {})
                catalog = page_props.get("catalog", page_props)
                cars = catalog.get("cars", [])
                if cars:
                    return {"cars": cars, "totalPages": catalog.get("totalPages", 1)}
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"__NEXT_DATA__ no usable: {e}")

        # Método 2: Next.js streaming — extraer chunks de self.__next_f.push()
        cars = self._extract_from_streaming(html)
        if cars:
            return {"cars": cars, "totalPages": 1}

        # Método 3: Buscar "cars":[ directamente en el HTML
        match = re.search(r'"cars"\s*:\s*(\[(?:\{.*?\}(?:\s*,\s*\{.*?\})*)\])', html, re.DOTALL)
        if match:
            try:
                cars = json.loads(match.group(1))
                if cars:
                    return {"cars": cars, "totalPages": 1}
            except json.JSONDecodeError:
                pass

        logger.warning("No se encontraron datos de listings en la página de Kavak")
        return None

    def _extract_from_streaming(self, html: str) -> list[dict]:
        """Extrae listings del formato RSC (React Server Components) de Next.js.

        Los datos vienen con comillas escapadas (\\") dentro de strings JS.
        Primero desescapamos y luego buscamos el array "cars".
        """
        # El JSON está escaped: \\" → ", \\/ → /
        unescaped = html.replace('\\"', '"').replace("\\\\", "\\")

        match = re.search(r'"cars"\s*:\s*\[', unescaped)
        if not match:
            return []

        start = match.start() + match.group().index("[")
        cars_json = self._extract_balanced(unescaped, start, "[", "]")
        if not cars_json:
            return []

        try:
            cars = json.loads(cars_json)
            if isinstance(cars, list):
                return [c for c in cars if isinstance(c, dict) and c.get("id")]
        except json.JSONDecodeError:
            logger.debug("Error parseando cars JSON del streaming")

        return []

    @staticmethod
    def _extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Optional[str]:
        """Extrae un bloque balanceado de open_ch/close_ch desde start."""
        if start >= len(text) or text[start] != open_ch:
            # Buscar el primer open_ch desde start
            idx = text.find(open_ch, start)
            if idx == -1:
                return None
            start = idx

        depth = 0
        in_string = False
        escape = False
        for i in range(start, min(start + 500_000, len(text))):
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

    def _parse_item(self, item: dict) -> Optional[dict]:
        """Parsea un item de Kavak a formato estandarizado."""
        try:
            analytics = item.get("analytics", {})

            # Extraer precio (viene como string "10.700.000" en ARS)
            price_ars = _parse_price(item.get("mainPrice"))

            # Extraer km del subtitle (ej: "53.667 km | Manual")
            km = _parse_km(item.get("subtitle", ""))

            # Extraer año
            year = analytics.get("car_year")
            if isinstance(year, str):
                year = _parse_int(year)

            # ID externo
            external_id = str(
                analytics.get("car_id")
                or item.get("id")
                or item.get("url", "")
            )

            # URL completa
            url = item.get("url", "")
            if url and not url.startswith("http"):
                url = f"https://www.kavak.com{url}"

            # Imagen
            thumbnail = item.get("image", "")

            title = item.get("title", "")
            if not title and analytics:
                make = analytics.get("car_make", "")
                model = analytics.get("car_model", "")
                title = f"{make} {model}".strip()

            if not external_id or not url:
                return None

            return {
                "external_id": external_id,
                "title": title,
                "price_usd": None,
                "price_ars": price_ars,
                "year": year,
                "km": km,
                "doors": None,
                "location": analytics.get("car_location"),
                "url": url,
                "thumbnail_url": thumbnail,
                "photos": [],
            }
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parseando item Kavak: {e}")
            return None


def _parse_price(price_str: Optional[str]) -> Optional[float]:
    """Parsea precio de string como '10.700.000' a float."""
    if not price_str:
        return None
    digits = price_str.replace(".", "").replace(",", ".")
    digits = "".join(c for c in digits if c.isdigit() or c == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _parse_km(subtitle: str) -> Optional[int]:
    """Extrae km de un subtitle como '53.667 km | Manual'."""
    match = re.search(r"([\d.]+)\s*km", subtitle, re.IGNORECASE)
    if match:
        km_str = match.group(1).replace(".", "")
        try:
            return int(km_str)
        except ValueError:
            return None
    return None


def _parse_int(value: Optional[str] = None) -> Optional[int]:
    """Extrae entero de un string."""
    if not value:
        return None
    digits = "".join(c for c in str(value) if c.isdigit())
    return int(digits) if digits else None
