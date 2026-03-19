"""Orquestador principal del pipeline de scraping."""

import logging
import os
import sys
from datetime import datetime

import config
import db
import export
from converter.currency import convert_listings
from scrapers.mercadolibre import MercadoLibreScraper
from scrapers.kavak import KavakScraper
from scoring.calculator import calculate_score
from scoring.photo_analyzer import analyze_photos

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
    scrapers = [MercadoLibreScraper(), KavakScraper()]
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

    # 3. Convertir precios ARS → USD
    convert_listings(all_listings)

    # 4. Deduplicar y guardar
    seen_ids = set()
    with db.get_connection() as conn:
        for listing in all_listings:
            lid = db.upsert_listing(conn, listing)
            seen_ids.add(lid)

        # 5. Marcar listings desaparecidos
        for scraper in scrapers:
            deactivated = db.increment_missed_runs(conn, scraper.source_name, seen_ids)
            if deactivated:
                logger.info(f"Desactivados {deactivated} listings de {scraper.source_name}")

        # 6. Análisis de fotos (si está habilitado)
        if config.ENABLE_PHOTO_ANALYSIS:
            active = db.get_all_active(conn)
            analyzed = 0
            for listing in active:
                photos = listing.get("photos", [])
                if photos:
                    result = analyze_photos(photos)
                    if result:
                        db.update_photo_analysis(conn, listing["id"], result)
                        analyzed += 1
            if analyzed:
                logger.info(f"Analizadas fotos de {analyzed} listings")

        # 7. Scoring
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

        # 8. Exportar
        final = db.get_all_active(conn)

    export.export_csv(final)
    export.export_json(final)

    logger.info(f"=== Run completo: {len(final)} listings activos ===")


if __name__ == "__main__":
    main()
