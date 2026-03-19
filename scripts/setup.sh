#!/usr/bin/env bash
set -euo pipefail

echo "=== gol-scraper: setup ==="

# Crear virtualenv si no existe
if [ ! -d ".venv" ]; then
    echo "Creando virtualenv..."
    python3 -m venv .venv
fi

# Activar virtualenv
source .venv/bin/activate

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

# Crear directorios necesarios
mkdir -p data logs

echo "=== Setup completo ==="
echo "Activá el virtualenv con: source .venv/bin/activate"
