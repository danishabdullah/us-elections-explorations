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

-- Candidate positions. Every collection pass is kept (positions_A, messaging_B, ig_stance_final, ...); the
-- 'reconciled' collection holds the final value per indicator. Coding scheme: data/manual/positions/<cycle>/SCHEMA.md.
CREATE TABLE IF NOT EXISTS positions (
    id          INTEGER PRIMARY KEY,
    seat_id     TEXT NOT NULL REFERENCES seats (seat_id),
    cycle       INTEGER NOT NULL,
    candidate   TEXT NOT NULL,
    indicator   TEXT NOT NULL,
    value       TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',    -- e.g. the wage figure ('$20'), or an assessor's confidence
    evidence    TEXT NOT NULL DEFAULT '',
    source_date TEXT NOT NULL DEFAULT '',
    retrieved   TEXT NOT NULL DEFAULT '',
    collection  TEXT NOT NULL REFERENCES collections (collection),
    source_id   TEXT REFERENCES sources (source_id),
    other_urls  TEXT NOT NULL DEFAULT '',    -- further sources cited for the same value, ' ; '-joined
    notes       TEXT NOT NULL DEFAULT '',
    UNIQUE (seat_id, cycle, candidate, indicator, collection)
) STRICT;

-- Dated quotes behind an assessed value (the Israel/Gaza stance cites up to four).
CREATE TABLE IF NOT EXISTS position_evidence (
    position_id INTEGER NOT NULL REFERENCES positions (id) ON DELETE CASCADE,
    ord         INTEGER NOT NULL,
    quote       TEXT NOT NULL,
    url         TEXT NOT NULL DEFAULT '',
    date        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (position_id, ord)
) STRICT;

-- Independent re-checks of a collection's values against the sources.
CREATE TABLE IF NOT EXISTS position_checks (
    id                 INTEGER PRIMARY KEY,
    cycle              INTEGER NOT NULL,
    collection         TEXT NOT NULL REFERENCES collections (collection),   -- the checker, e.g. 'verify_A'
    checked_collection TEXT NOT NULL,      -- the pass it checked, e.g. 'positions_A', or 'selection'
    state              TEXT NOT NULL,      -- a state, or a note such as '(all)' for a check across candidates
    seat_id            TEXT REFERENCES seats (seat_id),
    candidate          TEXT NOT NULL DEFAULT '',
    indicator          TEXT NOT NULL,
    original_value     TEXT NOT NULL DEFAULT '',
    verified_value     TEXT NOT NULL DEFAULT '',
    status             TEXT NOT NULL,      -- confirmed / changed / unresolved
    source_id          TEXT REFERENCES sources (source_id),
    evidence           TEXT NOT NULL DEFAULT '',
    notes              TEXT NOT NULL DEFAULT ''
) STRICT;

-- Values changed by the author under a revised coding rule, each with its reason.
CREATE TABLE IF NOT EXISTS rulings (
    seat_id   TEXT NOT NULL REFERENCES seats (seat_id),
    cycle     INTEGER NOT NULL,
    indicator TEXT NOT NULL,
    value     TEXT NOT NULL,
    reason    TEXT NOT NULL,
    PRIMARY KEY (seat_id, cycle, indicator)
) STRICT;

-- Facts about each candidate's race that aren't positions: endorsements, primaries.
CREATE TABLE IF NOT EXISTS candidates (
    seat_id               TEXT NOT NULL REFERENCES seats (seat_id),
    cycle                 INTEGER NOT NULL,
    candidate             TEXT NOT NULL,
    sanders_endorse_date  TEXT NOT NULL DEFAULT '',
    sanders_endorse_stage TEXT NOT NULL DEFAULT '',
    contested_primary     TEXT NOT NULL DEFAULT '',
    primary_result_note   TEXT NOT NULL DEFAULT '',
    source_notes          TEXT NOT NULL DEFAULT '',
    retrieved             TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (seat_id, cycle, candidate)
) STRICT;
