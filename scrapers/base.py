"""Clase abstracta base para scrapers."""

from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """Base para todos los scrapers de autos."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identificador de la fuente, ej. 'mercadolibre'."""

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Scrapea listings y retorna dicts estandarizados.

        Cada dict debe contener:
            - external_id: str
            - title: str
            - price_usd: float | None
            - price_ars: float | None
            - year: int | None
            - km: int | None
            - doors: int | None
            - location: str | None
            - url: str
            - thumbnail_url: str | None
            - photos: list[str]
        """
