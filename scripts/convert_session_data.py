"""One-time conversion of the verified collections from the first analysis (16 Senate races) into data/manual.

Usage: uv run python scripts/convert_session_data.py <path to the earlier analysis's data/ folder>
Kept in the repo so the provenance of data/manual is reproducible.
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

from elections.sources.manual import COLUMNS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "manual"
OWN_PRIOR = {"OH": ("sen", ""), "NE": ("sen", ""), "AK": ("house", "00"), "NC": ("gov", "")}


def read(p: Path) -> list[dict[str, str]]:
    with p.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write(p: Path, cols: list[str], rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def convert_results(src: Path) -> None:
    for pass_dir in sorted(src.glob("pass?")):
        out = []
        for f in sorted(pass_dir.glob("*.csv")):
            for r in read(f):
                contest, etype = r["contest"], r["election_type"]
                office, district = "sen", ""
                if contest.startswith("pres_"):
                    office = "pres"
                elif contest == "own_prior":
                    office, district = OWN_PRIOR[r["state"]]
                final_d, final_r = r.get("dem_votes_final_round", ""), r.get("rep_votes_final_round", "")
                notes = r.get("notes", "")
                if contest == "own_prior" and r["state"] == "AK" and pass_dir.name == "passA":
                    # the final RCV round here rests only on an Internet Archive copy of a blocked state page
                    final_d = final_r = ""
                    notes += " [final RCV round dropped: only source was an archive copy of a blocked page]"
                if r.get("other_sources"):
                    notes += f" | other sources: {r['other_sources']}"
                status = (r["status"] or "unofficial").lower()
                out.append(
                    dict(
                        office=office,
                        state=r["state"],
                        year=r["year"],
                        stage="runoff" if etype == "runoff" else "gen",
                        special="1" if etype == "special" else "0",
                        district=district,
                        dem_candidate=r["dem_candidate"],
                        dem_party=r["dem_party"],
                        dem_votes=r["dem_votes"],
                        rep_candidate=r["rep_candidate"],
                        rep_votes=r["rep_votes"],
                        total_votes=r["total_votes"],
                        dem_votes_final_round=final_d,
                        rep_votes_final_round=final_r,
                        status=status if status in ("official", "certified", "unofficial") else "unofficial",
                        as_of=r.get("as_of", ""),
                        source_publisher=r["source_name"],
                        source_title=r["source_name"],
                        source_url=r["source_url"],
                        retrieved=r.get("retrieved", ""),
                        notes=notes.strip(),
                    )
                )
        write(OUT / "results" / f"{pass_dir.name}.csv", COLUMNS, out)
        print(f"{pass_dir.name}: {len(out)} contests")


def convert_ratings(al: Path) -> None:
    cols = ["state", "date", "rating", "previous_rating", "source_title", "source_url", "notes"]
    for p, coll in (("A", "passA"), ("B", "passB")):
        rows = [
            {k: r.get(k, "") for k in cols}
            for r in read(al / f"rating_history_{p}.csv")
            if r["previous_rating"] != r["rating"]
        ]
        write(OUT / "ratings" / f"crystal-ball_2026_{coll}.csv", cols, rows)
        print(f"ratings {coll}: {len(rows)}")


def convert_positions(al: Path) -> None:
    cols = [
        "state",
        "candidate",
        "indicator",
        "value",
        "evidence",
        "source_url",
        "source_publisher",
        "source_date",
        "notes",
    ]
    rows = [
        dict(
            state=r["state"],
            candidate=r["candidate"],
            indicator=r["indicator"],
            value=r["final_value"],
            evidence=r["verify_evidence"] or r["evidence"],
            source_url=r["verify_source"] or r["source_url"],
            source_publisher=r.get("source_publisher", ""),
            source_date=r.get("source_date", ""),
            notes=" | ".join(
                x for x in (r.get("verify_status", ""), r.get("verify_note", ""), r.get("notes", "")) if x
            ),
        )
        for r in read(al / "alignment_final.csv")
    ]
    out = OUT / "positions" / "2026"
    write(out / "reconciled.csv", cols, rows)
    # every collection pass, verifier re-check and ruling, copied as collected
    for name in PASSES:
        shutil.copy(al / f"{name}.csv", out / f"{name}.csv")
    shutil.copy(al / "SCHEMA.md", out / "SCHEMA.md")
    (OUT / "candidates").mkdir(parents=True, exist_ok=True)
    shutil.copy(al / "selection.csv", OUT / "candidates" / "2026.csv")
    print(f"positions: {len(rows)} reconciled values, {len(PASSES)} collection files")


# unused_partial_israel_gaza_substance.csv is left out: a stopped collection, superseded by ig_stance_*.
PASSES = [
    *(f"positions_{p}" for p in "ABC"),
    *(f"messaging_{p}" for p in "AB"),
    *(f"israel_gaza_{p}" for p in "AB"),
    *(f"health_wage_{p}" for p in ("A", "B", "final", "recent")),
    *(f"ig_stance_{p}" for p in ("A", "B", "final")),
    "israel_aid_statements",
    *(f"verify_{p}" for p in ("A", "BC", "israel_gaza", "messaging")),
    "rulings",
]


if __name__ == "__main__":
    src = Path(sys.argv[1])
    convert_results(src)
    convert_ratings(src / "alignment")
    convert_positions(src / "alignment")
