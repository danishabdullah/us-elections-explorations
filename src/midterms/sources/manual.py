"""Reviewed collections: results gathered by hand (or by an agent) from cited sources, one CSV per collection pass.

Used where no trusted bulk dataset exists yet, chiefly 2026 before certification, and for offices MEDSL doesn't
cover (governor). Each pass is collected independently from different sources; reconcile.py compares them.

File: data/manual/results/<collection>.csv, one row per contest:
    office,state,year,stage,special,district,dem_candidate,dem_party,dem_votes,rep_candidate,rep_votes,total_votes,
    dem_votes_final_round,rep_votes_final_round,status,as_of,source_publisher,source_title,source_url,retrieved,notes
dem_* holds the Democrat, or the independent the Democrats backed (dem_party 'IND'). total_votes is every valid vote
for the office, write-ins included, blanks excluded. Final-round columns are for ranked-choice races (round 99).

Ratings: data/manual/ratings/<rater-slug>_<cycle>_<collection>.csv with state,date,rating,previous_rating,
source_title,source_url,notes. Positions and candidate facts: see sources/positions.py.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from midterms import db
from midterms.models import Contest, ResultRow, Source, Total
from midterms.seats import seat_for

FINAL_ROUND = 99
COLUMNS = [
    "office",
    "state",
    "year",
    "stage",
    "special",
    "district",
    "dem_candidate",
    "dem_party",
    "dem_votes",
    "rep_candidate",
    "rep_votes",
    "total_votes",
    "dem_votes_final_round",
    "rep_votes_final_round",
    "status",
    "as_of",
    "source_publisher",
    "source_title",
    "source_url",
    "retrieved",
    "notes",
]
RATERS = {"crystal-ball": "Sabato's Crystal Ball"}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _source(r: dict[str, str]) -> Source:
    return Source(
        source_id=db.source_id_for(r["source_url"] or None, r["source_title"]),
        kind="web",
        publisher=r["source_publisher"] or r["source_title"],
        title=r["source_title"],
        url=r["source_url"] or None,
        retrieved_at=r["retrieved"] or None,
    )


def contest_for(r: dict[str, str], overrides: dict[tuple[str, int, str], int]) -> Contest:
    year, special = int(r["year"]), r["special"].strip().lower() in ("1", "true", "yes")
    seat_id = method = None
    if r["office"] == "sen":
        seat_id, method = seat_for(r["state"], year - 1 if year % 2 else year, special, overrides)
    return Contest.model_validate(
        {
            "office": r["office"],
            "state": r["state"],
            "year": year,
            "stage": r["stage"] or "gen",
            "special": special,
            "district": r["district"] or None,
            "seat_id": seat_id,
            "seat_method": method,
        }
    )


def load_results(con: sqlite3.Connection, path: Path, overrides: dict[tuple[str, int, str], int]) -> int:
    collection = path.stem
    rows = _read(path)
    if rows and list(rows[0]) != COLUMNS:
        raise ValueError(f"{path}: columns must be exactly {COLUMNS}")
    db.add_collection(con, collection, f"reviewed collection {collection} ({path.name})")
    n = 0
    for r in rows:
        c = contest_for(r, overrides)
        db.add_contest(con, c)
        src = _source(r)
        db.add_source(con, src)
        status = r["status"] or "unofficial"
        kw = {
            "contest_id": c.contest_id,
            "collection": collection,
            "source_id": src.source_id,
            "status": status,
            "as_of": r["as_of"],
        }
        dem = {
            "candidate": r["dem_candidate"],
            "party": r["dem_party"],
            "party_simplified": "INDEPENDENT" if r["dem_party"].upper() in ("I", "IND", "INDEPENDENT") else "DEMOCRAT",
        }
        rep = {"candidate": r["rep_candidate"], "party": "R", "party_simplified": "REPUBLICAN"}
        results = [
            ResultRow.model_validate(kw | dem | {"votes": int(r["dem_votes"])}),
            ResultRow.model_validate(kw | rep | {"votes": int(r["rep_votes"])}),
        ]
        if r["dem_votes_final_round"] and r["rep_votes_final_round"]:
            results += [
                ResultRow.model_validate(kw | dem | {"votes": int(r["dem_votes_final_round"]), "round": FINAL_ROUND}),
                ResultRow.model_validate(kw | rep | {"votes": int(r["rep_votes_final_round"]), "round": FINAL_ROUND}),
            ]
        # a pass may record no total when its source didn't publish one; that pass then can't be the primary
        totals = (
            [
                Total(
                    contest_id=c.contest_id,
                    collection=collection,
                    source_id=src.source_id,
                    total_votes=int(r["total_votes"]),
                    notes=r["notes"],
                )
            ]
            if r["total_votes"].strip()
            else []
        )
        n += db.replace_results(con, results, totals)
    con.commit()
    return n


def load_ratings(con: sqlite3.Connection, path: Path, overrides: dict[tuple[str, int, str], int]) -> int:
    rater_slug, cycle, collection = path.stem.rsplit("_", 2)
    db.add_collection(con, collection, f"reviewed collection {collection}")
    n = 0
    for r in _read(path):
        seat_id, _ = _seat_in_cycle(r["state"], int(cycle), overrides)
        src = Source(
            source_id=db.source_id_for(r["source_url"] or None, r["source_title"]),
            kind="web",
            publisher=RATERS[rater_slug],
            title=r["source_title"],
            url=r["source_url"] or None,
        )
        db.add_source(con, src)
        con.execute(
            """INSERT OR REPLACE INTO ratings
                   (seat_id, cycle, rater, date, rating, previous_rating, collection, source_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                seat_id,
                int(cycle),
                RATERS[rater_slug],
                r["date"],
                r["rating"],
                r["previous_rating"] or None,
                collection,
                src.source_id,
                r.get("notes", ""),
            ),
        )
        n += 1
    con.commit()
    return n


def _seat_in_cycle(state: str, cycle: int, overrides: dict[tuple[str, int, str], int]) -> tuple[str, str]:
    """The one seat a state elects in a cycle; ambiguous when it holds both a regular and a special."""
    from midterms.seats import seats_up

    mine = [s for s, _ in seats_up(cycle, overrides) if s.startswith(state + "-")]
    if len(mine) != 1:
        raise LookupError(f"{state} elects {len(mine)} seats in {cycle}; the file must name the seat")
    return mine[0], "calendar"
