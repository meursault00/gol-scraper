"""Análisis de fotos con Claude API."""

import base64
import logging
from typing import Optional

import anthropic
import requests

import config

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analiza esta foto de un auto usado (Volkswagen Gol) y evalúa su estado general.
Responde SOLO con un JSON con esta estructura exacta:
{
  "condition_score": <float 0.0 a 1.0>,
  "issues": ["lista de problemas detectados"],
  "highlights": ["aspectos positivos"]
}

Criterios de evaluación:
- Estado de la pintura (rayaduras, abolladuras, óxido)
- Estado de los neumáticos
- Estado del interior (tapizado, tablero)
- Limpieza general
- Si la foto es de mala calidad o no muestra el auto claramente, usa 0.5 como score."""

client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global client
    if client is None:
        client = anthropic.Anthropic()
    return client


def analyze_photos(photo_urls: list[str]) -> Optional[dict]:
    """Analiza hasta MAX_PHOTOS_TO_ANALYZE fotos y retorna score promedio.

    Returns:
        {"photo_score": float, "issues": [...], "highlights": [...]}
        o None si no se pudo analizar.
    """
    if not photo_urls:
        return None

    urls = photo_urls[:config.MAX_PHOTOS_TO_ANALYZE]
    results = []

    for url in urls:
        result = _analyze_single_photo(url)
        if result:
            results.append(result)

    if not results:
        return None

    avg_score = sum(r["condition_score"] for r in results) / len(results)
    all_issues = []
    all_highlights = []
    for r in results:
        all_issues.extend(r.get("issues", []))
        all_highlights.extend(r.get("highlights", []))

    return {
        "photo_score": round(avg_score, 4),
        "issues": list(set(all_issues)),
        "highlights": list(set(all_highlights)),
    }


def _analyze_single_photo(url: str) -> Optional[dict]:
    """Analiza una sola foto usando Claude Vision."""
    try:
        image_data = _fetch_image(url)
        if not image_data:
            return None

        media_type = _guess_media_type(url)

        api = _get_client()
        message = api.messages.create(
            model=config.PHOTO_ANALYSIS_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image_data).decode(),
                            },
                        },
                        {"type": "text", "text": ANALYSIS_PROMPT},
                    ],
                }
            ],
        )

        return _parse_response(message.content[0].text)

    except anthropic.APIError as e:
        logger.warning(f"Error de API Claude analizando foto: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error analizando foto {url}: {e}")
        return None


def _fetch_image(url: str) -> Optional[bytes]:
    """Descarga una imagen y retorna los bytes."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error descargando imagen {url}: {e}")
        return None


def _guess_media_type(url: str) -> str:
    """Infiere el media type de la URL."""
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".png"):
        return "image/png"
    if url_lower.endswith(".webp"):
        return "image/webp"
    if url_lower.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def _parse_response(text: str) -> Optional[dict]:
    """Parsea la respuesta de Claude a un dict."""
    import json
    import re

    # Buscar JSON en la respuesta
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        score = data.get("condition_score", 0.5)
        if not isinstance(score, (int, float)) or not (0 <= score <= 1):
            score = 0.5
        data["condition_score"] = score
        return data
    except json.JSONDecodeError:
        return None
