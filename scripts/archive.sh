#!/usr/bin/env bash
set -euo pipefail

echo "=== gol-scraper: archive ==="

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="data/archives/${TIMESTAMP}"

mkdir -p "${ARCHIVE_DIR}"

# Snapshot de la base de datos
if [ -f "data/listings.db" ]; then
    echo "Guardando snapshot de la DB..."
    cp "data/listings.db" "${ARCHIVE_DIR}/listings.db"

    # Exportar resumen a CSV si sqlite3 está disponible
    if command -v sqlite3 &>/dev/null; then
        echo "Exportando resumen a CSV..."
        sqlite3 -header -csv "data/listings.db" \
            "SELECT source, title, price_usd, year, km, score_total, url
             FROM listings WHERE is_active = 1
             ORDER BY score_total DESC;" \
            > "${ARCHIVE_DIR}/listings_summary.csv" 2>/dev/null || true
    fi
fi

# Comprimir logs viejos (más de 7 días)
if [ -d "logs" ]; then
    echo "Comprimiendo logs viejos..."
    find logs -name "*.log" -mtime +7 -exec gzip -q {} \; 2>/dev/null || true
fi

# Limpiar __pycache__
echo "Limpiando caches de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "Archivado en: ${ARCHIVE_DIR}"
echo "=== Archive completo ==="
