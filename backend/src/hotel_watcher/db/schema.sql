-- Applied on every start. Every statement must be idempotent.

CREATE TABLE IF NOT EXISTS watches (
    id              INTEGER PRIMARY KEY,
    hotel_key       TEXT    NOT NULL,
    hotel_name      TEXT    NOT NULL,
    location_name   TEXT,
    latitude        REAL,
    longitude       REAL,
    image_url       TEXT,
    hotel_url       TEXT,
    check_in        TEXT    NOT NULL,
    check_out       TEXT    NOT NULL,
    adults          INTEGER NOT NULL,
    target_price    TEXT,               -- Decimal as text, in `currency`
    currency        TEXT    NOT NULL DEFAULT 'USD',
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    last_checked_at TEXT,
    last_status     TEXT,
    last_price      TEXT,
    last_site       TEXT
);

-- One watch per exact stay. Re-adding a removed one reactivates the old row.
CREATE UNIQUE INDEX IF NOT EXISTS idx_watches_stay
    ON watches (hotel_key, check_in, check_out, adults);

CREATE TABLE IF NOT EXISTS price_observations (
    id          INTEGER PRIMARY KEY,
    hotel_key   TEXT    NOT NULL,
    check_in    TEXT    NOT NULL,
    check_out   TEXT    NOT NULL,
    adults      INTEGER NOT NULL,
    nightly     TEXT    NOT NULL,       -- cheapest nightly price seen, Decimal as text
    currency    TEXT    NOT NULL,
    site        TEXT,
    watch_id    INTEGER REFERENCES watches (id),
    observed_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_stay
    ON price_observations (hotel_key, check_in, check_out, adults, observed_at);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY,
    watch_id     INTEGER NOT NULL REFERENCES watches (id),
    kind         TEXT    NOT NULL,      -- 'new_low' or 'target_hit'
    price        TEXT    NOT NULL,
    previous_low TEXT,
    currency     TEXT    NOT NULL,
    site         TEXT,
    message      TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    read_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts (read_at, created_at);

CREATE TABLE IF NOT EXISTS provider_usage (
    provider TEXT    NOT NULL,
    month    TEXT    NOT NULL,          -- 'YYYY-MM'
    calls    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (provider, month)
);
