"""Build contest_final: one reconciled row per contest, with every other collection compared against it.

Primary collection: MEDSL (certified, bulk) whenever it has the contest, unless MEDSL marks it unofficial and a
reviewed pass has certified counts; otherwise the per-contest choice in
data/manual/primary.json, otherwise the first of passA, passB, passC that has it. Observations are never edited.

The two sides: the leading Democrat (or, where no Democrat ran, the leading non-Republican, e.g. an independent the
party backed) and the leading Republican. Votes for one candidate on several party lines (fusion) are summed.
Same-party generals (California and Washington top-two) get no Republican side and no margin.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ORDER = ("medsl", "passA", "passB", "passC")


@dataclass(frozen=True, slots=True)
class Side:
    dem_candidate: str | None
    dem_party: str | None
    dem_votes: int | None
    rep_candidate: str | None
    rep_votes: int | None
    total: int | None


def summarize(rows: list[sqlite3.Row], total: int | None) -> Side:
    by: dict[str, int] = defaultdict(int)
    parties: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["candidate"] == "(other)" or r["party_simplified"] == "NONVOTE":
            continue
        by[r["candidate"]] += r["votes"]
        parties[r["candidate"]][r["party_simplified"]] += r["votes"]
    main = {c: max(p, key=lambda k: p[k]) for c, p in parties.items()}
    ranked = sorted(by, key=lambda c: -by[c])
    dems = [c for c in ranked if main[c] == "DEMOCRAT"]
    reps = [c for c in ranked if main[c] == "REPUBLICAN"]
    dem = dems[0] if dems else next((c for c in ranked if main[c] != "REPUBLICAN"), None)
    rep = reps[0] if reps else None
    return Side(
        dem, main.get(dem) if dem else None, by.get(dem) if dem else None, rep, by.get(rep) if rep else None, total
    )


def _primary_map(path: Path) -> dict[str, str]:
    return json.loads(path.read_text())["contests"] if path.exists() else {}


def run(con: sqlite3.Connection, primary_file: Path) -> dict[str, int]:
    chosen = _primary_map(primary_file)
    con.execute("DELETE FROM contest_final")
    counts: dict[str, int] = defaultdict(int)
    for cid, notes in con.execute("SELECT contest_id, notes FROM contests").fetchall():
        rows = con.execute("SELECT * FROM results WHERE contest_id = ? AND round = 1", (cid,)).fetchall()
        tots = {
            r["collection"]: r["total_votes"]
            for r in con.execute(
                "SELECT collection, total_votes FROM totals WHERE contest_id = ? AND round = 1", (cid,)
            )
        }
        per: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for r in rows:
            per[r["collection"]].append(r)
        if not per:
            continue
        sides = {c: summarize(rs, tots.get(c)) for c, rs in per.items()}
        able = [c for c in sides if sides[c].total]  # a collection with no total can check, not lead
        if not able:
            counts["no total"] += 1
            continue
        certified = [c for c in able if c != "medsl" and per[c][0]["status"] in ("certified", "official")]
        medsl_unofficial = "medsl" in per and per["medsl"][0]["status"] == "unofficial"
        if medsl_unofficial and certified:  # e.g. MEDSL's Jan 2021 Georgia runoffs predate certification
            primary = next((c for c in DEFAULT_ORDER if c in certified), certified[0])
        elif "medsl" in able:
            primary = "medsl"
        elif chosen.get(cid) in able:
            primary = chosen[cid]
        else:
            primary = next((c for c in DEFAULT_ORDER if c in able), sorted(able)[0])
        p = sides[primary]
        others = [c for c in sides if c != primary]
        diffs = []
        for c in others:
            o = sides[c]
            if (o.dem_votes, o.rep_votes, o.total) != (p.dem_votes, p.rep_votes, p.total):
                diffs.append(f"{c}: D {o.dem_votes} R {o.rep_votes} total {o.total} (margin {_margin(o)})")
        agreement = "single source" if not others else ("differ" if diffs else "agree")
        flag = notes if notes.startswith("medsl:") else ""
        con.execute(
            """INSERT INTO contest_final (contest_id, dem_candidate, dem_party, dem_votes, rep_candidate, rep_votes,
                   total_votes, dem_margin_pct, primary_collection, checked_by, agreement, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                p.dem_candidate,
                p.dem_party,
                p.dem_votes,
                p.rep_candidate,
                p.rep_votes,
                p.total,
                _margin(p),
                primary,
                ";".join(sorted(others)),
                agreement,
                " | ".join(x for x in [flag, f"primary margin {_margin(p)}" if diffs else "", *diffs] if x),
            ),
        )
        counts[agreement] += 1
    con.commit()
    return dict(counts)


def _margin(s: Side) -> float | None:
    if s.dem_votes is None or s.rep_votes is None or not s.total:
        return None
    return round(100 * (s.dem_votes - s.rep_votes) / s.total, 2)
