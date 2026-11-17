-- Every value carries where it came from (source) and which independent collection produced it (collection).
-- Raw observations are never overwritten by reconciliation; reconciled values live in contest_final.

CREATE TABLE IF NOT EXISTS seats (
    seat_id      TEXT PRIMARY KEY,           -- e.g. 'OH-3'
    state        TEXT NOT NULL,
    senate_class INTEGER NOT NULL CHECK (senate_class IN (1, 2, 3))
) STRICT;

CREATE TABLE IF NOT EXISTS collections (
    collection  TEXT PRIMARY KEY,            -- 'medsl', 'passA', 'passB', 'passC', ...
    description TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS sources (
    source_id    TEXT PRIMARY KEY,
    kind         TEXT NOT NULL CHECK (kind IN ('dataset', 'web', 'document', 'derived')),
    publisher    TEXT NOT NULL,
    title        TEXT NOT NULL,
    url          TEXT,
    retrieved_at TEXT,                       -- ISO 8601, UTC
    sha256       TEXT,                       -- of the raw bytes, when we downloaded them
    raw_path     TEXT,                       -- relative to data/raw
    notes        TEXT NOT NULL DEFAULT ''
) STRICT;

CREATE TABLE IF NOT EXISTS contests (
    contest_id   TEXT PRIMARY KEY,           -- e.g. '2026-sen-OH-3-special-gen', '2024-pres-OH-gen'
    office       TEXT NOT NULL CHECK (office IN ('sen', 'pres', 'house', 'gov')),
    state        TEXT NOT NULL,
    year         INTEGER NOT NULL,
    stage        TEXT NOT NULL CHECK (stage IN ('gen', 'runoff', 'pri')),
    special      INTEGER NOT NULL DEFAULT 0 CHECK (special IN (0, 1)),
    district     TEXT,                       -- House only
    seat_id      TEXT REFERENCES seats (seat_id),   -- Senate only
    seat_method  TEXT CHECK (seat_method IN ('calendar', 'override')),
    notes        TEXT NOT NULL DEFAULT '',
    CHECK ((office = 'sen') = (seat_id IS NOT NULL))
) STRICT;
CREATE INDEX IF NOT EXISTS contests_seat ON contests (seat_id, year);

CREATE TABLE IF NOT EXISTS results (
    id               INTEGER PRIMARY KEY,
    contest_id       TEXT NOT NULL REFERENCES contests (contest_id),
    collection       TEXT NOT NULL REFERENCES collections (collection),
    source_id        TEXT NOT NULL REFERENCES sources (source_id),
    candidate        TEXT NOT NULL,
    party            TEXT NOT NULL DEFAULT '',      -- as the source lists it
    party_simplified TEXT NOT NULL DEFAULT '',      -- DEMOCRAT / REPUBLICAN / LIBERTARIAN / OTHER / INDEPENDENT
    writein          INTEGER NOT NULL DEFAULT 0,
    votes            INTEGER NOT NULL CHECK (votes >= 0),
    round            INTEGER NOT NULL DEFAULT 1,    -- ranked-choice round; 1 = first choices
    status           TEXT NOT NULL DEFAULT 'official' CHECK (status IN ('official', 'certified', 'unofficial')),
    as_of            TEXT NOT NULL DEFAULT '',
    UNIQUE (contest_id, collection, candidate, party, round)
) STRICT;

CREATE TABLE IF NOT EXISTS totals (
    contest_id  TEXT NOT NULL REFERENCES contests (contest_id),
    collection  TEXT NOT NULL REFERENCES collections (collection),
    source_id   TEXT NOT NULL REFERENCES sources (source_id),
    round       INTEGER NOT NULL DEFAULT 1,
    total_votes INTEGER NOT NULL CHECK (total_votes > 0),   -- all valid votes for the office, incl. write-ins
    notes       TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (contest_id, collection, round)
) STRICT;

-- One reconciled row per contest: the two leading candidates (or the D and R, see reconcile.py) and the evidence.
CREATE TABLE IF NOT EXISTS contest_final (
    contest_id        TEXT PRIMARY KEY REFERENCES contests (contest_id),
    dem_candidate     TEXT,
    dem_party         TEXT,
    dem_votes         INTEGER,
    rep_candidate     TEXT,
    rep_votes         INTEGER,
    total_votes       INTEGER NOT NULL,
    dem_margin_pct    REAL,
    primary_collection TEXT NOT NULL REFERENCES collections (collection),
    checked_by        TEXT NOT NULL DEFAULT '',     -- ';'-joined collections that were compared
    agreement         TEXT NOT NULL CHECK (agreement IN ('single source', 'agree', 'differ')),
    notes             TEXT NOT NULL DEFAULT ''
) STRICT;

CREATE TABLE IF NOT EXISTS ratings (
    id              INTEGER PRIMARY KEY,
    seat_id         TEXT NOT NULL REFERENCES seats (seat_id),
    cycle           INTEGER NOT NULL,
    rater           TEXT NOT NULL,                 -- e.g. 'Sabato''s Crystal Ball'
    date            TEXT NOT NULL,
    rating          TEXT NOT NULL CHECK (rating IN ('Safe Republican', 'Likely Republican', 'Leans Republican',
                        'Toss-up', 'Leans Democratic', 'Likely Democratic', 'Safe Democratic')),
    previous_rating TEXT,
    collection      TEXT NOT NULL REFERENCES collections (collection),
    source_id       TEXT NOT NULL REFERENCES sources (source_id),
    notes           TEXT NOT NULL DEFAULT '',
    UNIQUE (seat_id, cycle, rater, date, rating, collection)
) STRICT;

CREATE TABLE IF NOT EXISTS positions (
    id          INTEGER PRIMARY KEY,
    seat_id     TEXT NOT NULL REFERENCES seats (seat_id),
    cycle       INTEGER NOT NULL,
    candidate   TEXT NOT NULL,
    indicator   TEXT NOT NULL,
    value       TEXT NOT NULL,
    evidence    TEXT NOT NULL DEFAULT '',
    source_date TEXT NOT NULL DEFAULT '',
    collection  TEXT NOT NULL REFERENCES collections (collection),
    source_id   TEXT REFERENCES sources (source_id),
    notes       TEXT NOT NULL DEFAULT '',
    UNIQUE (seat_id, cycle, candidate, indicator, collection)
) STRICT;
