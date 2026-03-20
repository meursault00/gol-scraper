#!/bin/bash
# Configura cron job para ejecutar el scraper cada 6 horas.
#
# Uso:
#   chmod +x cron_setup.sh
#   ./cron_setup.sh          # instala el cron
#   ./cron_setup.sh remove   # remueve el cron

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
CRON_CMD="cd $SCRIPT_DIR && $PYTHON runner.py >> logs/cron.log 2>&1"
CRON_SCHEDULE="0 */6 * * *"
CRON_LINE="$CRON_SCHEDULE $CRON_CMD"
CRON_MARKER="# gol-scraper"

if [ "$1" = "remove" ]; then
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab -
    echo "Cron job removido."
    exit 0
fi

# Agregar cron evitando duplicados
(crontab -l 2>/dev/null | grep -v "$CRON_MARKER"; echo "$CRON_LINE $CRON_MARKER") | crontab -
echo "Cron job instalado: cada 6 horas"
echo "  $CRON_LINE"
echo ""
echo "Verificar con: crontab -l"
echo "Remover con:   $0 remove"
