# gol-scraper

Scraper periódico de autos usados **VW Gol / Gol Trend** en el rango **USD 5.000–7.000**, dentro del **Área Metropolitana de Buenos Aires (AMBA)**.

Los resultados se rankean con un sistema de scoring que combina precio, kilometraje, año, puertas y análisis de fotos con IA (Claude API). Se visualizan en un frontend estático o archivo descargable.

## Stack

- **Python 3.11+** — scraping + scoring
- **SQLite** — persistencia
- **Claude API** — análisis de fotos
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
| Fotos (IA) | 0.15 | Calidad visual indica cuidado |
| Puertas | 0.10 | 5 puertas > 3 puertas |

## Estructura del proyecto

```
gol-scraper/
├── conductor.json          # Configuración de Conductor (orquestador)
├── config.py               # Constantes, pesos, rangos de precio
├── db.py                   # Conexión SQLite, queries
├── runner.py               # Orquestador principal
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
├── scripts/
│   ├── setup.sh            # Setup del workspace
│   ├── run.sh              # Ejecución del pipeline
│   └── archive.sh          # Pre-archive: snapshot DB, cleanup
├── data/
│   └── listings.db         # SQLite (gitignored)
└── logs/                   # Logs de ejecución (gitignored)
```

## Uso

### Setup

```bash
./scripts/setup.sh
```

### Ejecución

```bash
./scripts/run.sh
```

### Archive (pre-archive de workspace)

```bash
./scripts/archive.sh
```

### Ejecución manual

```bash
python runner.py
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
                               Análisis fotos (Claude API)
                                      │
                                      ▼
                               Score total → Export → Frontend
```

## Conductor

Este proyecto usa [Conductor](https://github.com/conductor-is/conductor) para orquestar agentes en paralelo. Los workspaces están definidos en `conductor.json`.

| Agente | Tarea | Dependencias |
|--------|-------|-------------|
| scraper-mercadolibre | Scraping MercadoLibre | config, db |
| scraper-kavak | Scraping Kavak | config, db |
| scoring | Scoring + análisis fotos | db |
| frontend | Generación del frontend | db, export |
