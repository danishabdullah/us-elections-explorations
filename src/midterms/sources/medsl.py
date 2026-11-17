"""MIT Election Data and Science Lab (MEDSL) datasets on Harvard Dataverse: certified results, every state, every cycle.

The dataset version and file are looked up through the Dataverse API at fetch time, and each download is checked
against the MD5 that Dataverse publishes. Files behind a Dataverse guestbook (a form asking for the downloader's
details) are not fetched: that is a gate for a person to answer, not something to automate.

Known quirks in the source, handled here and recorded in contest notes:
- stage is written 'gen', 'GEN', 'pre' (a Georgia general that went to a runoff), 'runoff' or 'GEN RUNOFF'.
- Georgia's Jan 2021 runoffs carry year 2021; they belong to the 2020 cycle.
- Unnamed rows (scattering, blanks counted as 'OTHER') are summed into one '(other)' line per contest.
- Louisiana 2002 lists the November primary and the December runoff as one contest; contests with the same
  candidate twice are flagged 'medsl: duplicate candidate rows' and left out of reconciliation.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from midterms import db
from midterms.fetch import Blocked, Fetcher
from midterms.models import Contest, ResultRow, Source, Total
from midterms.seats import seat_for

DATAVERSE = "https://dataverse.harvard.edu"
COLLECTION = "medsl"


@dataclass(frozen=True, slots=True)
class Dataset:
    key: str
    doi: str
    filename_prefix: str
    office: str


DATASETS = {
    "senate": Dataset("senate", "doi:10.7910/DVN/PEJ5QU", "1976-2024-senate", "sen"),
    "president": Dataset("president", "doi:10.7910/DVN/42MVDX", "1976-2024-president", "pres"),
    "house": Dataset("house", "doi:10.7910/DVN/IG0UN2", "1976-2024-house", "house"),
}

STAGES = {"gen": "gen", "pre": "gen", "runoff": "runoff", "gen runoff": "runoff"}


def _latest_file(fetcher: Fetcher, ds: Dataset) -> tuple[dict, dict]:
    meta = fetcher.get(f"{DATAVERSE}/api/datasets/:persistentId/?persistentId={ds.doi}", refresh=True)
    version = json.loads(meta.path.read_bytes())["data"]["latestVersion"]
    f = next(f["dataFile"] for f in version["files"] if f["dataFile"]["filename"].startswith(ds.filename_prefix))
    return version, f


def fetch(fetcher: Fetcher, key: str, *, refresh: bool = False) -> tuple[Path, Source]:
    ds = DATASETS[key]
    version, f = _latest_file(fetcher, ds)
    if f.get("restricted") or version.get("guestbook") or f.get("guestbookId"):
        raise Blocked(f"{ds.doi} {f['filename']} sits behind a Dataverse guestbook; download it by hand")
    url = f"{DATAVERSE}/api/access/datafile/{f['id']}?format=original"
    md5 = f.get("md5") or (f.get("checksum") or {}).get("value")
    dl = fetcher.get(url, refresh=refresh, expect_md5=md5)
    head = dl.path.read_bytes()[:2000]
    if head.startswith(b'{"status":"ERROR"'):
        dl.path.unlink()
        raise Blocked(f"{ds.doi}: {json.loads(head).get('message', 'Dataverse refused the download')}")
    vno = f"{version['versionNumber']}.{version['versionMinorNumber']}"
    src = Source(
        source_id=f"medsl-{key}-v{vno}",
        kind="dataset",
        publisher="MIT Election Data and Science Lab (Harvard Dataverse)",
        title=f"{f['filename']} ({ds.doi}, version {vno}, released {version.get('releaseTime', '')[:10]})",
        url=url,
        retrieved_at=dl.retrieved_at,
        sha256=dl.sha256,
        raw_path=str(dl.path.relative_to(fetcher.raw_dir)),
        notes=f"MD5 checked against Dataverse: {md5}",
    )
    return dl.path, src


def _contest(office: str, r: dict, overrides: dict[tuple[str, int, str], int]) -> Contest | None:
    """Build the contest; returns None for a Senate special whose seat class needs an override that is missing."""
    state, year = r["state_po"], int(r["year"])
    stage = STAGES[(r.get("stage") or "gen").strip().lower()]
    special = (r.get("special") or "False") == "True"
    if office == "pres":
        return Contest(office="pres", state=state, year=year)
    base = {"state": state, "year": year, "stage": stage, "special": special}
    if office == "house":
        return Contest.model_validate(base | {"office": "house", "district": f"{int(r['district']):02d}"})
    cycle = year - 1 if year % 2 else year  # Jan 2021 Georgia runoffs belong to 2020
    try:
        seat_id, method = seat_for(state, cycle, special, overrides)
    except LookupError:
        return None
    return Contest.model_validate(base | {"office": "sen", "seat_id": seat_id, "seat_method": method})


def parse(
    path: Path,
    key: str,
    source_id: str,
    overrides: dict[tuple[str, int, str], int],
    fixes: dict[tuple, str] | None = None,
):
    """Yield (contest, rows, total, problems) per contest."""
    fixes = fixes or {}
    office = DATASETS[key].office
    groups: dict[str, list[dict]] = defaultdict(list)
    contests: dict[str, Contest] = {}
    unresolved: set[tuple[str, int]] = set()
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = _contest(office, r, overrides)
            if c is None:
                unresolved.add((r["state_po"], int(r["year"])))
                continue
            contests[c.contest_id] = c
            groups[c.contest_id].append(r)
    if unresolved:  # refuse to load anything until every contest has a seat
        raise UnresolvedSpecials(sorted(unresolved))
    for cid, rs in groups.items():
        c = contests[cid]
        by: dict[tuple[str, str], int] = defaultdict(int)
        seen: dict[tuple[str, str], int] = defaultdict(int)
        meta: dict[tuple[str, str], dict] = {}
        for r in rs:
            name = r["candidate"].strip() or "(other)"
            party = (r.get("party_detailed") or r.get("party") or "").strip()
            k = (name, party)
            by[k] += int(float(r["candidatevotes"] or 0))
            seen[k] += 1
            meta[k] = r
        problems = []
        if any(n > 1 and k[0] != "(other)" for k, n in seen.items()):
            problems.append("medsl: duplicate candidate rows (likely two rounds merged)")
        listed = {int(float(r["totalvotes"])) for r in rs if r["totalvotes"]}
        if len(listed) > 1:
            problems.append(f"medsl: inconsistent totals {sorted(listed)}")
        unofficial = any((r.get("unofficial") or "False") == "True" for r in rs)
        rows = []
        for (name, party), v in by.items():
            m = meta[(name, party)]
            simple = party_simplified(c, name, party, m.get("party_simplified") or "", fixes)
            if MIXED_BLANKS.match(name.upper()):
                problems.append("medsl: blanks are combined with scattering here, so the total includes blanks")
            rows.append(
                ResultRow(
                    contest_id=cid,
                    collection=COLLECTION,
                    source_id=source_id,
                    candidate=name,
                    party=party,
                    party_simplified=simple,
                    writein=(m.get("writein") or "False") == "True",
                    votes=v,
                    status="unofficial" if unofficial else "certified",
                )
            )
        # Our total is every valid vote: candidates, write-ins and scattering; not blank, over- or under-votes.
        valid = sum(r.votes for r in rows if r.party_simplified != NONVOTE)
        listed_note = f"MEDSL totalvotes {max(listed)}" if listed else "MEDSL lists no total"
        total = (
            Total(
                contest_id=cid,
                collection=COLLECTION,
                source_id=source_id,
                total_votes=valid,
                notes=f"sum of valid votes ({listed_note})",
            )
            if valid
            else None
        )
        yield c.model_copy(update={"notes": "; ".join(dict.fromkeys(problems))}), rows, total, problems


NONVOTE = "NONVOTE"
NON_VOTES = re.compile(r"^(BLANK VOTES?|BLANK VOTE/VOID VOTE|BLANKS|OVER ?VOTES?|UNDER ?VOTES?|VOID VOTES?|SPOILED)$")
MIXED_BLANKS = re.compile(r"^BLANK VOTE.*SCATTER")


def party_simplified(c: Contest, name: str, party: str, given: str, fixes: dict[tuple, str]) -> str:
    """MEDSL's party_simplified, corrected: non-votes marked, labels inferred from party_detailed, known gaps fixed."""
    if NON_VOTES.match(name.upper()):
        return NONVOTE
    if (c.office, c.state, c.year, name) in fixes:
        return fixes[(c.office, c.state, c.year, name)]
    given = given.strip().upper()
    if given in ("DEMOCRAT", "REPUBLICAN", "LIBERTARIAN"):
        return given
    up = party.upper()
    if up.startswith("DEMOCRAT"):
        return "DEMOCRAT"
    if up.startswith("REPUBLICAN"):
        return "REPUBLICAN"
    return given or "OTHER"


def load_fixes(path: Path) -> dict[tuple, str]:
    if not path.exists():
        return {}
    return {
        (f["office"], f["state"], f["year"], f["candidate"]): f["party_simplified"]
        for f in json.loads(path.read_text())["party"]
    }


def load_overrides(path: Path) -> dict[tuple[str, int, str], int]:
    return {(s["state"], s["year"], "special"): s["class"] for s in json.loads(path.read_text())["specials"]}


class UnresolvedSpecials(Exception):
    """Senate specials whose seat class the calendar can't decide; add them to data/special_seats.json."""

    def __init__(self, items: list[tuple[str, int]]) -> None:
        self.items = items
        super().__init__(f"{len(items)} special elections need a seat class: {items}")


def load(
    con: sqlite3.Connection,
    path: Path,
    key: str,
    src: Source,
    overrides: dict[tuple[str, int, str], int],
    fixes: dict[tuple, str] | None = None,
) -> int:
    db.add_collection(con, COLLECTION, "MIT Election Data and Science Lab, certified results via Harvard Dataverse")
    db.add_source(con, src)
    n = 0
    for c, rows, total, _ in parse(path, key, src.source_id, overrides, fixes):
        db.add_contest(con, c)
        n += db.replace_results(con, rows, [total] if total else [])
    con.commit()
    return n
