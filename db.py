"""Conexión y operaciones SQLite."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    price_usd REAL,
    price_ars REAL,
    year INTEGER,
    km INTEGER,
    doors INTEGER,
    location TEXT,
    url TEXT NOT NULL,
    thumbnail_url TEXT,
    photos TEXT,
    score REAL,
    score_details TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    run_count INTEGER DEFAULT 1,
    missed_runs INTEGER DEFAULT 0,
    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_score ON listings(score DESC);
CREATE INDEX IF NOT EXISTS idx_listings_active ON listings(is_active);
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);
"""


def make_id(source: str, external_id: str) -> str:
    """Genera ID determinístico desde source + external_id."""
    return hashlib.sha256(f"{source}:{external_id}".encode()).hexdigest()[:16]


@contextmanager
def get_connection():
    """Context manager que entrega una conexión SQLite con row_factory=Row."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crea tablas e índices si no existen."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def upsert_listing(conn, listing: dict) -> str:
    """Inserta o actualiza un listing. Retorna el ID."""
    now = datetime.now(timezone.utc).isoformat()
    lid = make_id(listing["source"], listing["external_id"])
    photos_json = json.dumps(listing.get("photos", []))

    conn.execute(
        """
        INSERT INTO listings (
            id, source, external_id, title, price_usd, price_ars,
            year, km, doors, location, url, thumbnail_url, photos,
            first_seen_at, last_seen_at, is_active, run_count, missed_runs
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 0)
        ON CONFLICT(source, external_id) DO UPDATE SET
            title = excluded.title,
            price_usd = excluded.price_usd,
            price_ars = excluded.price_ars,
            year = excluded.year,
            km = excluded.km,
            doors = excluded.doors,
            location = excluded.location,
            url = excluded.url,
            thumbnail_url = excluded.thumbnail_url,
            photos = excluded.photos,
            last_seen_at = excluded.last_seen_at,
            is_active = 1,
            run_count = run_count + 1,
            missed_runs = 0
        """,
        (
            lid, listing["source"], listing["external_id"], listing["title"],
            listing.get("price_usd"), listing.get("price_ars"),
            listing.get("year"), listing.get("km"), listing.get("doors"),
            listing.get("location"), listing["url"], listing.get("thumbnail_url"),
            photos_json, now, now,
        ),
    )
    return lid


def get_all_active(conn) -> list[dict]:
    """Retorna todos los listings activos ordenados por score DESC."""
    rows = conn.execute(
        "SELECT * FROM listings WHERE is_active = 1 ORDER BY score DESC NULLS LAST"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def increment_missed_runs(conn, source: str, seen_ids: set) -> int:
    """Incrementa missed_runs para listings activos no vistos. Desactiva tras 3 misses."""
    rows = conn.execute(
        "SELECT id FROM listings WHERE source = ? AND is_active = 1",
        (source,),
    ).fetchall()

    deactivated = 0
    for row in rows:
        if row["id"] not in seen_ids:
            conn.execute(
                """UPDATE listings
                   SET missed_runs = missed_runs + 1,
                       is_active = CASE WHEN missed_runs + 1 >= 3 THEN 0 ELSE is_active END
                   WHERE id = ?""",
                (row["id"],),
            )
            if conn.execute(
                "SELECT is_active FROM listings WHERE id = ?", (row["id"],)
            ).fetchone()["is_active"] == 0:
                deactivated += 1

    return deactivated


def update_photo_analysis(conn, listing_id: str, analysis: dict):
    """Guarda el resultado del análisis de fotos en score_details."""
    row = conn.execute(
        "SELECT score_details FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()
    existing = json.loads(row["score_details"]) if row and row["score_details"] else {}
    existing["photo_analysis"] = analysis
    conn.execute(
        "UPDATE listings SET score_details = ? WHERE id = ?",
        (json.dumps(existing), listing_id),
    )


def update_scores(conn, scores: list[dict]):
    """Actualiza score y score_details en batch."""
    for s in scores:
        conn.execute(
            "UPDATE listings SET score = ?, score_details = ? WHERE id = ?",
            (s["score"], json.dumps(s["score_details"]), s["id"]),
        )


def _row_to_dict(row) -> dict:
    """Convierte sqlite3.Row a dict, deserializando campos JSON."""
    d = dict(row)
    if d.get("photos"):
        d["photos"] = json.loads(d["photos"])
    if d.get("score_details"):
        d["score_details"] = json.loads(d["score_details"])
    return d
