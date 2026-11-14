import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/review_registry.sqlite")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_registry():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def register_review(review_id: str, topic: str):
    init_registry()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO reviews (review_id, topic, created_at)
            VALUES (?, ?, ?)
            """,
            (review_id, topic, datetime.now(timezone.utc).isoformat())
        )


def get_registered_reviews():
    init_registry()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC"
        ).fetchall()

    return [dict(row) for row in rows]