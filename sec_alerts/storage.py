"""Storage and deduplication for seen alerts."""

import sqlite3
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Storage:
    """Manages SQLite database for tracking seen alerts."""

    def __init__(self, db_path: str = "data/alerts.sqlite"):
        """Initialize storage with database path."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                id TEXT PRIMARY KEY,
                seen_at TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
        logger.debug(f"Initialized database at {self.db_path}")

    def _generate_id(self, source: str, url: str, title: str = "", published: Optional[datetime] = None) -> str:
        """Generate a stable ID for an alert item."""
        # Use source + url as primary identifier, with title + published as fallback
        if url:
            key = f"{source}:{url}"
        else:
            pub_str = published.isoformat() if published else ""
            key = f"{source}:{title}:{pub_str}"
        return hashlib.sha256(key.encode()).hexdigest()

    def is_seen(self, item_id: str) -> bool:
        """Check if an item has been seen before."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM seen_items WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def mark_seen(self, item_id: str, source: str, title: str, url: str):
        """Mark an item as seen."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO seen_items (id, seen_at, source, title, url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, datetime.utcnow().isoformat(), source, title, url),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Marked item as seen: {item_id[:16]}...")

    def get_seen_count(self) -> int:
        """Get total count of seen items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM seen_items")
        count = cursor.fetchone()[0]
        conn.close()
        return count

