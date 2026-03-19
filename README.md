# gol-scraper

Scraper periódico de autos usados **VW Gol / Gol Trend** en el rango **USD 5.000–7.000**, dentro del **Área Metropolitana de Buenos Aires (AMBA)**.

Los resultados se rankean con un sistema de scoring que combina precio, kilometraje, año, puertas y (opcionalmente) análisis de fotos con IA. Se visualizan en un frontend estático o archivo descargable.

## Stack

- **Python 3.11+** — scraping + scoring
- **SQLite** — persistencia
- **Claude API** — análisis de fotos (feature flag, desactivado por defecto)
- **HTML/JS estático** — frontend

## Fuentes de datos

| Fuente | Método | Prioridad |
|--------|--------|-----------|
| MercadoLibre | API pública REST | Alta |
| Kavak | API interna (SPA) | Alta |
| DeAutos | Scraping HTML | Media |
| AutoCosmos | Scraping HTML | Baja |

## Scoring

| Factor | Peso | Criterio |
|--------|------|----------|
| Precio | 0.30 | Más barato → mejor |
| Kilometraje | 0.25 | Menos km → mejor |
| Año | 0.20 | Más nuevo → mejor |
| Fotos (IA) | 0.15 | Calidad visual indica cuidado (requiere feature flag) |
| Puertas | 0.10 | 5 puertas > 3 puertas |

## Estructura del proyecto

```
gol-scraper/
├── conductor.json          # Scripts de Conductor (setup, run, archive)
├── config.py               # Constantes, pesos, feature flags
├── db.py                   # Conexión SQLite, queries
├── runner.py               # Entry point principal
├── export.py               # Exportar a JSON/CSV/HTML
├── scrapers/
│   ├── __init__.py
│   ├── base.py             # Clase abstracta BaseScraper
│   ├── mercadolibre.py     # Scraper MercadoLibre API
│   └── kavak.py            # Scraper Kavak
├── scoring/
│   ├── __init__.py
│   ├── calculator.py       # Fórmulas de scoring
│   └── photo_analyzer.py   # Análisis con Claude API
├── converter/
│   └── currency.py         # Conversión ARS → USD
├── frontend/
│   └── index.html          # Frontend estático
├── data/
│   └── listings.db         # SQLite (gitignored)
└── logs/                   # Logs de ejecución (gitignored)
```

## Conductor

Este proyecto usa [Conductor](https://conductor.build) para gestionar workspaces de desarrollo. Los scripts están definidos en `conductor.json`:

| Script | Acción |
|--------|--------|
| **setup** | Crea virtualenv, instala deps, symlink `.env` |
| **run** | Ejecuta el pipeline (`python runner.py`) |
| **archive** | Limpia virtualenv y caches de Python |

## Feature flags

| Flag | Default | Descripción |
|------|---------|-------------|
| `ENABLE_PHOTO_ANALYSIS` | `False` | Análisis de fotos con Claude API |

Para activarlo, cambiar en `config.py`:
```python
ENABLE_PHOTO_ANALYSIS = True
```

## Pipeline

```
[Trigger]
    ├──► Scrape MercadoLibre ──┐
    │                          ├──► Deduplicar + SQLite
    └──► Scrape Kavak ─────────┘
                                      │
                                      ▼
                               Tipo de cambio USD/ARS
                                      │
                                      ▼
                               Scores numéricos
                                      │
                                      ▼
                               Análisis fotos (si habilitado)
                                      │
                                      ▼
                               Score total → Export → Frontend
```
