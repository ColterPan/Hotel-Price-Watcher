"""SQLite connection setup.

Raw sqlite3 plus a repository of explicit functions, no ORM: a handful of small
tables, and plain SQL is easy to test against an in-memory database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from hotel_watcher.logging_config import get_logger

logger = get_logger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

#: Columns added after the first release. schema.sql creates them for a new
#: database; this adds them to an existing one so its history is kept.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "watches": {"needs_baseline": "INTEGER NOT NULL DEFAULT 0"},
}

#: The background watcher and a user's request can write at the same moment.
#: Waiting this long for the lock beats failing with "database is locked".
_BUSY_TIMEOUT_MS = 5000


def _apply_migrations(conn: sqlite3.Connection) -> None:
    for table, columns in _ADDED_COLUMNS.items():
        present = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for column, definition in columns.items():
            if column not in present:
                logger.info("migrating: adding %s.%s", table, column)
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def connect(database_path: str) -> sqlite3.Connection:
    """Open `database_path` (or ":memory:") with the schema applied."""
    if database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    # FastAPI runs sync dependencies on a thread pool, so a connection may be
    # used from a different thread than the one that opened it. Each request
    # gets its own connection, so this is safe here.
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    if database_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    _apply_migrations(conn)
    conn.commit()
    return conn
