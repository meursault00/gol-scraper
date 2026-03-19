"""Configuración global del scraper."""

# Búsqueda
SEARCH_QUERY = "volkswagen gol"
CATEGORY_ID = "MLA1744"  # Autos y Camionetas
STATE_ID = "TUxBUEJVRQ"  # Buenos Aires
PRICE_MIN_USD = 5000
PRICE_MAX_USD = 7000

# Scoring weights
WEIGHTS = {
    "price": 0.30,
    "km": 0.25,
    "year": 0.20,
    "photos": 0.15,
    "doors": 0.10,
}

# Scoring parameters
MAX_KM = 250_000
MIN_YEAR = 2005
MAX_YEAR = 2024
MAX_PHOTOS_TO_ANALYZE = 5

# Rate limiting
REQUEST_DELAY_SECONDS = 2
MAX_RESULTS_PER_SOURCE = 1000

# Database
DB_PATH = "data/listings.db"

# Currency API
DOLAR_API_URL = "https://dolarapi.com/v1/dolares/blue"

# Claude API
PHOTO_ANALYSIS_MODEL = "claude-sonnet-4-20250514"
