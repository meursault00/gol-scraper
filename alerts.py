"""Alertas via Telegram para listings con score alto."""

import logging

import requests

import config

logger = logging.getLogger(__name__)


def send_alerts(listings: list[dict]):
    """Envía alertas por Telegram para listings nuevos con score > threshold.

    Solo alerta listings que fueron vistos por primera vez en esta corrida
    (run_count == 1) para evitar spam.
    """
    if not config.ENABLE_ALERTS:
        return

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Alertas habilitadas pero faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
        return

    new_high_score = [
        l for l in listings
        if (l.get("score") or 0) >= config.ALERT_SCORE_THRESHOLD
        and l.get("run_count") == 1
    ]

    if not new_high_score:
        return

    logger.info(f"Enviando {len(new_high_score)} alertas por Telegram")

    for listing in new_high_score:
        message = _format_message(listing)
        _send_telegram(message)


def _format_message(listing: dict) -> str:
    """Formatea un listing para enviar por Telegram."""
    score_pct = round((listing.get("score") or 0) * 100)
    price = listing.get("price_usd")
    price_str = f"USD ${price:,.0f}" if price else "Sin precio USD"
    year = listing.get("year") or "?"
    km = listing.get("km")
    km_str = f"{km:,} km" if km else "? km"
    location = listing.get("location") or "?"
    source = listing.get("source", "?").upper()

    lines = [
        f"🚗 *Score: {score_pct}%*",
        f"*{listing.get('title', 'Sin título')}*",
        f"💰 {price_str}",
        f"📅 {year} · 🛣 {km_str}",
        f"📍 {location} · 📦 {source}",
        f"🔗 [Ver publicación]({listing.get('url', '')})",
    ]
    return "\n".join(lines)


def _send_telegram(message: str):
    """Envía un mensaje por Telegram."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if not resp.ok:
            logger.warning(f"Error enviando alerta Telegram: {resp.status_code} {resp.text}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error de red enviando alerta Telegram: {e}")
