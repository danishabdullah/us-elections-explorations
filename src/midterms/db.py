"""SQLite storage. A build artifact: `midterms build` recreates it from cached sources and data/manual."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path

from midterms.models import Contest, ResultRow, Source, Total
from midterms.seats import seats

SCHEMA_VERSION = 1


def connect(path: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def init(con: sqlite3.Connection) -> None:
    con.executescript(files("midterms").joinpath("schema.sql").read_text())
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.executemany(
        "INSERT OR IGNORE INTO seats (seat_id, state, senate_class) VALUES (?, ?, ?)",
        [(s.seat_id, s.state, s.senate_class) for s in seats()],
    )
    con.commit()


def source_id_for(url: str | None, title: str) -> str:
    return "S-" + hashlib.sha1((url or title).encode()).hexdigest()[:12]


def add_collection(con: sqlite3.Connection, collection: str, description: str) -> None:
    con.execute(
        "INSERT INTO collections (collection, description) VALUES (?, ?) "
        "ON CONFLICT (collection) DO UPDATE SET description = excluded.description",
        (collection, description),
    )


def add_source(con: sqlite3.Connection, s: Source) -> str:
    con.execute(
        """INSERT INTO sources (source_id, kind, publisher, title, url, retrieved_at, sha256, raw_path, notes)
           VALUES (:source_id, :kind, :publisher, :title, :url, :retrieved_at, :sha256, :raw_path, :notes)
           ON CONFLICT (source_id) DO UPDATE SET retrieved_at = coalesce(excluded.retrieved_at, retrieved_at),
             sha256 = coalesce(excluded.sha256, sha256), raw_path = coalesce(excluded.raw_path, raw_path)""",
        s.model_dump(),
    )
    return s.source_id


def add_contest(con: sqlite3.Connection, c: Contest) -> str:
    con.execute(
        """INSERT INTO contests (contest_id, office, state, year, stage, special, district, seat_id, seat_method, notes)
           VALUES (:contest_id, :office, :state, :year, :stage, :special, :district, :seat_id, :seat_method, :notes)
           ON CONFLICT (contest_id) DO NOTHING""",
        c.model_dump() | {"contest_id": c.contest_id},
    )
    return c.contest_id


def replace_results(con: sqlite3.Connection, rows: Iterable[ResultRow], totals: Iterable[Total]) -> int:
    """Insert one collection's rows for some contests, replacing that collection's earlier rows for them."""
    rows, totals = list(rows), list(totals)
    keys = {(r.contest_id, r.collection) for r in rows} | {(t.contest_id, t.collection) for t in totals}
    for cid, coll in keys:
        con.execute("DELETE FROM results WHERE contest_id = ? AND collection = ?", (cid, coll))
        con.execute("DELETE FROM totals WHERE contest_id = ? AND collection = ?", (cid, coll))
    con.executemany(
        """INSERT INTO results (contest_id, collection, source_id, candidate, party, party_simplified, writein, votes,
                                round, status, as_of)
           VALUES (:contest_id, :collection, :source_id, :candidate, :party, :party_simplified, :writein, :votes,
                   :round, :status, :as_of)""",
        [r.model_dump() for r in rows],
    )
    con.executemany(
        """INSERT INTO totals (contest_id, collection, source_id, round, total_votes, notes)
           VALUES (:contest_id, :collection, :source_id, :round, :total_votes, :notes)""",
        [t.model_dump() for t in totals],
    )
    return len(rows)
