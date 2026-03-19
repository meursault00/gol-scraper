"""Orquestador principal del pipeline de scraping."""

import logging
import os
import sys
from datetime import datetime

import db
import export
from scrapers.mercadolibre import MercadoLibreScraper
from scoring.calculator import calculate_score

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Iniciando scrape run ===")

    # 1. Inicializar DB
    db.init_db()

    # 2. Scrapear
    scrapers = [MercadoLibreScraper()]
    all_listings = []

    for scraper in scrapers:
        try:
            listings = scraper.scrape()
            for listing in listings:
                listing["source"] = scraper.source_name
            all_listings.extend(listings)
            logger.info(f"{scraper.source_name}: {len(listings)} listings")
        except Exception as e:
            logger.error(f"{scraper.source_name} falló: {e}", exc_info=True)

    if not all_listings:
        logger.warning("No se scrapearon listings, saliendo.")
        return

    # 3. Deduplicar y guardar
    seen_ids = set()
    with db.get_connection() as conn:
        for listing in all_listings:
            lid = db.upsert_listing(conn, listing)
            seen_ids.add(lid)

        # 4. Marcar listings desaparecidos
        for scraper in scrapers:
            deactivated = db.increment_missed_runs(conn, scraper.source_name, seen_ids)
            if deactivated:
                logger.info(f"Desactivados {deactivated} listings de {scraper.source_name}")

        # 5. Scoring
        active = db.get_all_active(conn)
        scores = []
        for listing in active:
            result = calculate_score(listing)
            scores.append({
                "id": listing["id"],
                "score": result["score"],
                "score_details": result["details"],
            })
        db.update_scores(conn, scores)

        # 6. Exportar
        final = db.get_all_active(conn)

    export.export_csv(final)
    export.export_json(final)

    logger.info(f"=== Run completo: {len(final)} listings activos ===")


if __name__ == "__main__":
    main()
