#!/usr/bin/env bash
set -euo pipefail

echo "=== gol-scraper: run ==="

# Activar virtualenv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: virtualenv no encontrado. Corré ./scripts/setup.sh primero."
    exit 1
fi

# Crear directorios si no existen
mkdir -p data logs

# Ejecutar pipeline
echo "Ejecutando pipeline..."
python runner.py 2>&1 | tee -a "logs/run_$(date +%Y%m%d_%H%M%S).log"

echo "=== Ejecución completa ==="
