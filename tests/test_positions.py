import csv

from elections.sources import positions


def write(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


LONG = dict(
    state="ME",
    candidate="Troy Jackson",
    indicator="ceasefire_call",
    value="unclear",
    evidence="site heading",
    source_publisher="Campaign",
    source_url="https://a.example/1 ; https://b.example/2",
    source_date="2026-09-01",
    retrieved="2026-11-07",
    notes="",
)


def test_loads_every_file_shape(con, overrides, tmp_path):
    folder = tmp_path / "2026"
    folder.mkdir()
    write(folder / "positions_A.csv", [LONG])
    write(folder / "reconciled.csv", [LONG | {"value": "yes"}])
    stance = {
        "state": "TX",
        "candidate": "James Talarico",
        "stance": "3",
        "rationale": "restrict arms",
        "confidence": "high",
        "notes": "",
    }
    for i in range(1, 5):
        stance |= {
            f"evidence_{i}": f"quote {i}" if i < 3 else "",
            f"url_{i}": f"https://q.example/{i}",
            f"date_{i}": f"2026-0{i}-01",
        }
    write(folder / "ig_stance_A.csv", [stance])
    write(
        folder / "verify_A.csv",
        [
            {
                "file": "positions_A.csv",
                "state": "ME",
                "candidate": "Troy Jackson",
                "indicator_or_field": "ceasefire_call",
                "original_value": "unclear",
                "verified_value": "unclear",
                "status": "confirmed",
                "source_url": "https://a.example/1",
                "evidence": "",
                "notes": "",
            },
            {
                "file": "selection.csv",
                "state": "(all)",
                "candidate": "",
                "indicator_or_field": "x",
                "original_value": "",
                "verified_value": "",
                "status": "confirmed",
                "source_url": "",
                "evidence": "",
                "notes": "",
            },
        ],
    )
    write(
        folder / "rulings.csv",
        [{"state": "ME", "indicator": "ceasefire_call", "value": "yes", "reason": "revised rule"}],
    )

    counts = positions.load_cycle(con, folder, overrides)
    assert counts == {"ig_stance_A": 1, "positions_A": 1, "reconciled": 1, "rulings": 1, "verify_A": 2}

    p = con.execute("SELECT * FROM positions WHERE collection = 'positions_A'").fetchone()
    assert (p["seat_id"], p["value"], p["other_urls"]) == ("ME-2", "unclear", "https://b.example/2")
    s = con.execute("SELECT * FROM positions WHERE indicator = 'ig_stance'").fetchone()
    assert (s["seat_id"], s["value"], s["detail"]) == ("TX-2", "3", "high")
    assert con.execute("SELECT count(*) FROM position_evidence WHERE position_id = ?", (s["id"],)).fetchone()[0] == 2
    checks = con.execute("SELECT state, seat_id, checked_collection FROM position_checks ORDER BY id").fetchall()
    assert [tuple(c) for c in checks] == [("ME", "ME-2", "positions_A"), ("(all)", None, "selection")]
    assert con.execute("SELECT value FROM rulings").fetchone()[0] == "yes"
