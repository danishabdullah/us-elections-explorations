"""Candidate positions: every collection pass, the verifier re-checks, author rulings, and the reconciled values.

Layout: data/manual/positions/<cycle>/ holds one CSV per collection, named for it, plus SCHEMA.md (the coding scheme
and its dated revisions). Candidate facts (Sanders endorsement, primary) are in data/manual/candidates/<cycle>.csv.

File shapes, recognised by their columns:
- long:     state,candidate,indicator,value,evidence,source_publisher,source_url,source_date,... (one value per row)
            includes positions_*, messaging_*, israel_gaza_*, health_wage_* and reconciled.csv
- stance:   state,candidate,stance,rationale,evidence_1,url_1,date_1,...,evidence_4,...,confidence (ig_stance_*)
- aid:      state,candidate,statement_value,... (israel_aid_statements: the latest 2025-26 statement on Israel aid)
- verify:   file,state,candidate,indicator[_or_field],original_value,verified_value,status,... (verify_*)
- rulings:  state,indicator,value,reason
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from midterms import db
from midterms.models import Source
from midterms.seats import seats_up


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _urls(field: str) -> list[str]:
    return [u.strip() for u in field.replace(";", " ").split() if u.strip().startswith("http")]


def _source(con: sqlite3.Connection, url: str, publisher: str = "") -> str:
    host = url.split("/")[2]
    return db.add_source(
        con, Source(source_id=db.source_id_for(url, url), kind="web", publisher=publisher or host, title=url, url=url)
    )


class SeatIndex:
    """State -> the one seat it elects in a cycle (2026: every state elects at most one)."""

    def __init__(self, cycle: int, overrides: dict[tuple[str, int, str], int]) -> None:
        by: dict[str, list[str]] = {}
        for seat_id, _ in seats_up(cycle, overrides):
            by.setdefault(seat_id.split("-")[0], []).append(seat_id)
        self.cycle, self.by = cycle, by

    def __call__(self, state: str) -> str:
        seats = self.by.get(state, [])
        if len(seats) != 1:
            raise LookupError(f"{state} elects {len(seats)} seats in {self.cycle}; the file must name the seat")
        return seats[0]

    def maybe(self, state: str) -> str | None:
        return self.by[state][0] if len(self.by.get(state, [])) == 1 else None


def _insert(con: sqlite3.Connection, row: dict, evidence: tuple[tuple[str, str, str], ...] | list = ()) -> None:
    cur = con.execute(
        """INSERT INTO positions (seat_id, cycle, candidate, indicator, value, detail, evidence, source_date, retrieved,
                                  collection, source_id, other_urls, notes)
           VALUES (:seat_id, :cycle, :candidate, :indicator, :value, :detail, :evidence, :source_date, :retrieved,
                   :collection, :source_id, :other_urls, :notes)""",
        row,
    )
    con.executemany(
        "INSERT INTO position_evidence (position_id, ord, quote, url, date) VALUES (?, ?, ?, ?, ?)",
        [(cur.lastrowid, i, q, u, d) for i, (q, u, d) in enumerate(evidence, 1)],
    )


def _long(con, rows, collection, seat, cycle) -> int:
    for r in rows:
        urls = _urls(r.get("source_url", ""))
        _insert(
            con,
            {
                "seat_id": seat(r["state"]),
                "cycle": cycle,
                "candidate": r["candidate"],
                "indicator": r["indicator"],
                "value": r["value"].strip(),
                "detail": r.get("figure", ""),
                "evidence": r.get("evidence", ""),
                "source_date": r.get("source_date", ""),
                "retrieved": r.get("retrieved", ""),
                "collection": collection,
                "source_id": _source(con, urls[0], r.get("source_publisher", "")) if urls else None,
                "other_urls": " ; ".join(urls[1:]),
                "notes": " | ".join(x for x in (r.get("verify_status", ""), r.get("notes", "")) if x),
            },
        )
    return len(rows)


def _stance(con, rows, collection, seat, cycle) -> int:
    for r in rows:
        ev = [
            (r[f"evidence_{i}"], r.get(f"url_{i}", ""), r.get(f"date_{i}", ""))
            for i in range(1, 5)
            if r.get(f"evidence_{i}")
        ]
        urls = [u for _, u, _ in ev if u.startswith("http")]
        _insert(
            con,
            {
                "seat_id": seat(r["state"]),
                "cycle": cycle,
                "candidate": r["candidate"],
                "indicator": "ig_stance",
                "value": r["stance"].strip(),
                "detail": r.get("confidence", ""),
                "evidence": r["rationale"],
                "source_date": ev[0][2] if ev else "",
                "retrieved": "",
                "collection": collection,
                "source_id": _source(con, urls[0]) if urls else None,
                "other_urls": " ; ".join(urls[1:]),
                "notes": " | ".join(x for x in (r.get("verify_status", ""), r.get("notes", "")) if x),
            },
            ev,
        )
    return len(rows)


def _aid(con, rows, collection, seat, cycle) -> int:
    rows = [r | {"indicator": "condition_aid_statement", "value": r["statement_value"]} for r in rows]
    return _long(con, rows, collection, seat, cycle)


def _verify(con, rows, collection, seat: SeatIndex, cycle) -> int:
    for r in rows:
        urls = _urls(r.get("source_url", ""))
        con.execute(
            """INSERT INTO position_checks (cycle, collection, checked_collection, state, seat_id, candidate, indicator,
                   original_value, verified_value, status, source_id, evidence, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cycle,
                collection,
                r["file"].removesuffix(".csv"),
                r["state"],
                seat.maybe(r["state"]),
                r.get("candidate", ""),
                r.get("indicator") or r.get("indicator_or_field", ""),
                r.get("original_value", ""),
                r.get("verified_value", ""),
                r["status"],
                _source(con, urls[0]) if urls else None,
                r.get("evidence", ""),
                r.get("notes", "") + (f" | other sources: {' ; '.join(urls[1:])}" if len(urls) > 1 else ""),
            ),
        )
    return len(rows)


def _rulings(con, rows, collection, seat, cycle) -> int:
    con.executemany(
        "INSERT INTO rulings (seat_id, cycle, indicator, value, reason) VALUES (?, ?, ?, ?, ?)",
        [(seat(r["state"]), cycle, r["indicator"], r["value"], r["reason"]) for r in rows],
    )
    return len(rows)


def _shape(cols: list[str]):
    if cols[0] == "file":
        return _verify
    if "stance" in cols:
        return _stance
    if "statement_value" in cols:
        return _aid
    if "reason" in cols:
        return _rulings
    if "indicator" in cols and "value" in cols:
        return _long
    raise ValueError(f"unrecognised position file columns: {cols}")


def load_cycle(con: sqlite3.Connection, folder: Path, overrides: dict[tuple[str, int, str], int]) -> dict[str, int]:
    cycle = int(folder.name)
    seat = SeatIndex(cycle, overrides)
    counts: dict[str, int] = {}
    for path in sorted(folder.glob("*.csv")):
        rows = _read(path)
        if not rows:
            continue
        collection = path.stem
        db.add_collection(con, collection, f"{cycle} positions: {path.name} (scheme: {folder.name}/SCHEMA.md)")
        counts[collection] = _shape(list(rows[0]))(con, rows, collection, seat, cycle)
    con.commit()
    return counts


def load_candidates(con: sqlite3.Connection, path: Path, overrides: dict[tuple[str, int, str], int]) -> int:
    cycle = int(path.stem)
    seat = SeatIndex(cycle, overrides)
    rows = _read(path)
    con.executemany(
        """INSERT INTO candidates (seat_id, cycle, candidate, sanders_endorse_date, sanders_endorse_stage,
               contested_primary, primary_result_note, source_notes, retrieved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                seat(r["state"]),
                cycle,
                r["candidate"],
                r.get("sanders_endorse_date", ""),
                r.get("sanders_endorse_stage", ""),
                r.get("contested_primary", ""),
                r.get("primary_result_note", ""),
                r.get("source_notes", ""),
                r.get("retrieved", ""),
            )
            for r in rows
        ],
    )
    con.commit()
    return len(rows)
