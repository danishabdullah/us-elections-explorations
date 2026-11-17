import csv

from midterms import reconcile
from midterms.sources import manual


def write_pass(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=manual.COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: "" for k in manual.COLUMNS} | r)


BASE = dict(
    office="sen",
    state="ME",
    year="2026",
    stage="gen",
    special="0",
    dem_candidate="Troy Jackson",
    dem_party="D",
    rep_candidate="Susan Collins",
    status="unofficial",
    source_publisher="P",
    source_title="T",
)


def test_passes_agree_or_differ(con, overrides, tmp_path):
    write_pass(
        tmp_path / "passA.csv",
        [BASE | dict(dem_votes="100", rep_votes="90", total_votes="200", source_url="https://a")],
    )
    write_pass(
        tmp_path / "passB.csv",
        [BASE | dict(dem_votes="100", rep_votes="90", total_votes="200", source_url="https://b")],
    )
    write_pass(
        tmp_path / "passC.csv",
        [BASE | dict(dem_votes="101", rep_votes="90", total_votes="201", source_url="https://c")],
    )
    for p in ("passA", "passB"):
        manual.load_results(con, tmp_path / f"{p}.csv", overrides)
    reconcile.run(con, tmp_path / "none.json")
    row = con.execute("SELECT * FROM contest_final").fetchone()
    assert (row["contest_id"], row["primary_collection"], row["agreement"]) == ("2026-sen-ME-2-gen", "passA", "agree")
    manual.load_results(con, tmp_path / "passC.csv", overrides)
    reconcile.run(con, tmp_path / "none.json")
    row = con.execute("SELECT * FROM contest_final").fetchone()
    assert row["agreement"] == "differ" and "passC: D 101" in row["notes"]
    assert row["dem_margin_pct"] == 5.0


def test_pass_without_total_cannot_be_primary(con, overrides, tmp_path):
    write_pass(
        tmp_path / "passA.csv", [BASE | dict(dem_votes="100", rep_votes="90", total_votes="", source_url="https://a")]
    )
    write_pass(
        tmp_path / "passB.csv",
        [BASE | dict(dem_votes="100", rep_votes="90", total_votes="200", source_url="https://b")],
    )
    for p in ("passA", "passB"):
        manual.load_results(con, tmp_path / f"{p}.csv", overrides)
    (tmp_path / "primary.json").write_text('{"contests": {"2026-sen-ME-2-gen": "passA"}}')
    reconcile.run(con, tmp_path / "primary.json")
    row = con.execute("SELECT * FROM contest_final").fetchone()
    assert row is not None and row["total_votes"] == 200
