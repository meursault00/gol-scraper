# Guía de implementación

## Fase 1: MVP (scraping + scoring básico)

- [ ] **1.1** Implementar `config.py` con constantes (rangos de precio, pesos de scoring, URLs base)
- [ ] **1.2** Implementar `db.py` con schema SQLite y funciones CRUD
- [ ] **1.3** Implementar `scrapers/base.py` con clase abstracta `BaseScraper`
- [ ] **1.4** Implementar `scrapers/mercadolibre.py` usando API pública REST
  - Endpoint: `GET https://api.mercadolibre.com/sites/MLA/search`
  - Paginación con `offset` (máx 1000 resultados)
  - Filtrar por `currency_id`, `state`, `category`
- [ ] **1.5** Implementar `scoring/calculator.py` con scoring numérico (precio, km, año, puertas)
- [ ] **1.6** Implementar `export.py` para generar CSV/JSON
- [ ] **1.7** Implementar `runner.py` como entry point del pipeline

## Fase 2: Enriquecer

- [ ] **2.1** Implementar `scrapers/kavak.py` (interceptar API interna del SPA)
- [ ] **2.2** Implementar `converter/currency.py` con conversión ARS → USD vía dolarapi.com
- [ ] **2.3** Implementar `scoring/photo_analyzer.py` con Claude API (análisis de fotos)
- [ ] **2.4** Implementar `frontend/index.html` con tabla ordenable, filtros, thumbnails

## Fase 3: Automatizar

- [ ] **3.1** Configurar cron job cada 6 horas
- [ ] **3.2** Deduplicación y tracking de cambios (marcar `is_active = 0` después de 3 corridas)
- [ ] **3.3** Alertas (email o Telegram) para publicaciones con score > 0.8

## Fase 4: Extras (opcional)

- [ ] **4.1** Agregar más fuentes (DeAutos, AutoCosmos)
- [ ] **4.2** Frontend Streamlit interactivo
- [ ] **4.3** Historial de precios por publicación
- [ ] **4.4** Comparador side-by-side
- [ ] **4.5** Mapa de ubicaciones con distancia a Tigre

## Notas técnicas

### Rate limiting
- MercadoLibre: ~30 req/min sin auth
- Agregar delays de 1-3 segundos entre requests
- Respetar `robots.txt`

### Deduplicación
- ID primario = hash de `source + external_id`
- Al re-scrapear, actualizar `last_seen_at`
- Marcar `is_active = 0` si desaparece por 3 corridas consecutivas

### Costo del análisis de fotos
- ~1500 tokens por publicación (5 imágenes)
- ~100 publicaciones ≈ 150k tokens → < USD 1
- Solo analizar publicaciones nuevas o actualizadas
