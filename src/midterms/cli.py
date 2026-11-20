"""Command line: `uv run midterms --help`."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from midterms import db, reconcile
from midterms.fetch import Blocked, Fetcher
from midterms.seats import STATES, seats, seats_up
from midterms.sources import manual, medsl

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DB_PATH = DATA / "midterms.sqlite"
OVERRIDES = DATA / "special_seats.json"

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _overrides() -> dict[tuple[str, int, str], int]:
    return medsl.load_overrides(OVERRIDES)


def _guestbook() -> dict[str, str] | None:
    """Dataverse guestbook answers from guestbook.local.json (git-ignored): name, email, institution, position."""
    p = ROOT / "guestbook.local.json"
    return json.loads(p.read_text()) if p.exists() else None


@app.command()
def fetch(
    dataset: Annotated[str, typer.Argument(help="senate, president, house or all")] = "all",
    refresh: Annotated[bool, typer.Option(help="Download again even if cached")] = False,
) -> None:
    """Download MEDSL datasets into data/raw (checksum-verified)."""
    f = Fetcher(DATA / "raw")
    for key in medsl.DATASETS if dataset == "all" else [dataset]:
        try:
            path, src = medsl.fetch(f, key, refresh=refresh, guestbook=_guestbook())
            typer.echo(f"{key}: {src.title} -> {path.relative_to(ROOT)}")
        except Blocked as e:
            typer.secho(f"{key}: not fetched: {e}", fg="yellow")


@app.command()
def build(refresh: Annotated[bool, typer.Option(help="Re-download MEDSL files")] = False) -> None:
    """Rebuild data/midterms.sqlite from MEDSL and data/manual, reconcile, and export JSON."""
    DB_PATH.unlink(missing_ok=True)
    con = db.connect(DB_PATH)
    db.init(con)
    ov = _overrides()
    f = Fetcher(DATA / "raw")
    for key in medsl.DATASETS:
        try:
            path, src = medsl.fetch(f, key, refresh=refresh, guestbook=_guestbook())
        except Blocked as e:
            typer.secho(f"{key}: skipped: {e}", fg="yellow")
            continue
        n = medsl.load(con, path, key, src, ov, medsl.load_fixes(DATA / "medsl_fixes.json"))
        typer.echo(f"{key}: {n} result rows")
    for p in sorted((DATA / "manual" / "results").glob("*.csv")):
        typer.echo(f"{p.name}: {manual.load_results(con, p, ov)} result rows")
    for p in sorted((DATA / "manual" / "ratings").glob("*.csv")):
        typer.echo(f"{p.name}: {manual.load_ratings(con, p, ov)} ratings")
    for p in sorted((DATA / "manual" / "positions").glob("*.csv")):
        typer.echo(f"{p.name}: {manual.load_positions(con, p, ov)} positions")
    typer.echo(f"reconciled: {reconcile.run(con, DATA / 'manual' / 'primary.json')}")
    export(con)


def export(con: sqlite3.Connection | None = None) -> None:
    """Write data/export: one JSON file per seat with its full history, plus presidential results by state."""
    con = con or db.connect(DB_PATH)
    out = DATA / "export"
    (out / "seats").mkdir(parents=True, exist_ok=True)
    q = """SELECT c.contest_id, c.year, c.stage, c.special, c.seat_method, f.* FROM contests c
           JOIN contest_final f USING (contest_id) WHERE c.seat_id = ? ORDER BY c.year, c.stage"""
    for s in seats():
        rows = [dict(r) for r in con.execute(q, (s.seat_id,))]
        ratings = [
            dict(r)
            for r in con.execute(
                "SELECT cycle, rater, date, rating, collection FROM ratings WHERE seat_id = ? "
                "ORDER BY cycle, date, collection",
                (s.seat_id,),
            )
        ]
        (out / "seats" / f"{s.seat_id}.json").write_text(
            json.dumps(
                {
                    "seat_id": s.seat_id,
                    "state": s.state,
                    "state_name": STATES[s.state],
                    "class": s.senate_class,
                    "contests": rows,
                    "ratings": ratings,
                },
                indent=1,
                ensure_ascii=False,
            )
            + "\n"
        )
    pres: dict[str, dict[int, dict]] = {}
    for r in con.execute("""SELECT c.state, c.year, f.* FROM contests c JOIN contest_final f USING (contest_id)
                            WHERE c.office = 'pres' ORDER BY c.state, c.year"""):
        pres.setdefault(r["state"], {})[r["year"]] = {k: v for k, v in dict(r).items() if k not in ("state", "year")}
    (out / "president.json").write_text(json.dumps(pres, indent=1, ensure_ascii=False) + "\n")
    house: dict[str, dict[str, list[dict]]] = {}
    for r in con.execute("""SELECT c.state, c.district, c.year, c.stage, c.special, f.* FROM contests c
                            JOIN contest_final f USING (contest_id) WHERE c.office = 'house'
                            ORDER BY c.state, c.district, c.year, c.stage"""):
        row = {k: v for k, v in dict(r).items() if k not in ("state", "district")}
        house.setdefault(r["state"], {}).setdefault(r["district"], []).append(row)
    (out / "house").mkdir(exist_ok=True)
    for st, districts in house.items():
        (out / "house" / f"{st}.json").write_text(json.dumps(districts, indent=1, ensure_ascii=False) + "\n")


@app.command()
def status(cycle: int = 2026) -> None:
    """Coverage for every seat up in a cycle: result, sources and agreement, prior race, ratings."""
    con = db.connect(DB_PATH)
    typer.echo(f"{'seat':6} {'result':>10} {'sources':22} {'agree':13} {'prior race':24} ratings")
    missing = 0
    for seat_id, special in seats_up(cycle, _overrides()):
        cur = con.execute(
            """SELECT f.* FROM contests c JOIN contest_final f USING (contest_id)
               WHERE c.seat_id = ? AND c.year IN (?, ?) AND c.stage = 'gen' AND c.special = ?""",
            (seat_id, cycle, cycle + 1, int(special)),
        ).fetchone()
        prior = con.execute(
            """SELECT c.year, c.special, f.dem_margin_pct FROM contests c JOIN contest_final f USING (contest_id)
               WHERE c.seat_id = ? AND c.year < ? AND c.stage = 'gen' ORDER BY c.year DESC LIMIT 1""",
            (seat_id, cycle),
        ).fetchone()
        nrat = con.execute("SELECT count(*) FROM ratings WHERE seat_id = ? AND cycle = ?", (seat_id, cycle)).fetchone()[
            0
        ]
        res = f"{cur['dem_margin_pct']:+.2f}" if cur and cur["dem_margin_pct"] is not None else "MISSING"
        missing += cur is None
        srcs = f"{cur['primary_collection']}+{cur['checked_by']}" if cur else ""
        pr = (
            f"{prior['year']}{' special' if prior['special'] else ''} {prior['dem_margin_pct']:+.2f}"
            if prior and prior["dem_margin_pct"] is not None
            else ("-" if not prior else f"{prior['year']} (no D-R margin)")
        )
        agree = cur["agreement"] if cur else ""
        typer.echo(f"{seat_id + ('*' if special else ''):6} {res:>10} {srcs:22} {agree:13} {pr:24} {nrat}")
    typer.echo(f"\n* special election. {missing} seats have no {cycle} result yet.")


if __name__ == "__main__":
    app()
