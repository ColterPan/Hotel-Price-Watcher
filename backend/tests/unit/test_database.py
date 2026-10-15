import sqlite3

from hotel_watcher.db.database import connect


def test_old_database_gets_new_columns_and_keeps_rows(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        """
        CREATE TABLE watches (
            id INTEGER PRIMARY KEY, hotel_key TEXT NOT NULL, hotel_name TEXT NOT NULL,
            location_name TEXT, latitude REAL, longitude REAL, image_url TEXT, hotel_url TEXT,
            check_in TEXT NOT NULL, check_out TEXT NOT NULL, adults INTEGER NOT NULL,
            target_price TEXT, currency TEXT NOT NULL DEFAULT 'USD', active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL, last_checked_at TEXT, last_status TEXT, last_price TEXT, last_site TEXT
        );
        INSERT INTO watches (hotel_key, hotel_name, check_in, check_out, adults, created_at)
        VALUES ('g1-d11', 'Old Hotel', '2030-01-01', '2030-01-02', 2, '2026-01-01T00:00:00+00:00');
        """
    )
    old.close()

    conn = connect(str(path))
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(watches)")}
    assert "needs_baseline" in columns
    assert conn.execute("SELECT hotel_name FROM watches").fetchone()[0] == "Old Hotel"
    conn.close()


def test_connect_twice_is_safe(tmp_path):
    path = str(tmp_path / "twice.db")
    connect(path).close()
    connect(path).close()
