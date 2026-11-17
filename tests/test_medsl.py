import pytest

from midterms import reconcile
from midterms.sources import medsl
from tests.conftest import FIXTURES

SAMPLE = FIXTURES / "medsl_senate_sample.csv"


@pytest.fixture
def parsed(overrides, fixes):
    return {
        c.contest_id: (c, rows, total) for c, rows, total, _ in medsl.parse(SAMPLE, "senate", "src", overrides, fixes)
    }


def test_contests_get_seats_and_normalised_stages(parsed):
    assert set(parsed) == {
        "2008-sen-GA-2-gen",  # stage 'pre' is the general that went to a runoff
        "2021-sen-GA-3-special-runoff",  # Jan 2021 runoff belongs to the 2020 cycle, so the class III special
        "2020-sen-IA-2-gen",
        "2020-sen-WY-2-gen",
        "2020-sen-AZ-3-special-gen",  # resolved through data/special_seats.json
        "2000-sen-GA-3-special-gen",
        "2002-sen-LA-2-gen",
    }
    assert parsed["2020-sen-AZ-3-special-gen"][0].seat_method == "override"


def test_unnamed_rows_are_summed(parsed):
    _, rows, _ = parsed["2008-sen-GA-2-gen"]
    assert [r.votes for r in rows if r.candidate == "(other)"] == [72]


def test_total_excludes_blank_over_and_under_votes(parsed):
    _, rows, total = parsed["2020-sen-IA-2-gen"]
    assert {r.candidate for r in rows if r.party_simplified == medsl.NONVOTE} == {"UNDER VOTES", "OVER VOTES"}
    assert total.total_votes == 864997 + 754859 + 36961
    assert "MEDSL totalvotes 1700130" in total.notes


def test_party_labels_fixed_by_rule_and_by_file(parsed):
    wy = {r.candidate: r.party_simplified for r in parsed["2020-sen-WY-2-gen"][1]}
    assert wy == {"CYNTHIA M. LUMMIS": "REPUBLICAN", "MERAV BEN DAVID": "DEMOCRAT"}
    ga = {r.candidate: r.party_simplified for r in parsed["2000-sen-GA-3-special-gen"][1]}
    assert ga["MACK F. MATTINGLY"] == "REPUBLICAN"


def test_merged_rounds_are_flagged(parsed):
    assert "duplicate candidate rows" in parsed["2002-sen-LA-2-gen"][0].notes


def test_unofficial_rows_marked(parsed):
    assert {r.status for r in parsed["2021-sen-GA-3-special-runoff"][1]} == {"unofficial"}


def test_unresolvable_special_refuses_to_load(fixes):
    with pytest.raises(medsl.UnresolvedSpecials):
        list(medsl.parse(SAMPLE, "senate", "src", {}, fixes))


def test_load_and_reconcile_single_source(con, overrides, fixes, tmp_path):
    from midterms.models import Source

    src = Source(source_id="src", kind="dataset", publisher="MEDSL", title="sample")
    medsl.load(con, SAMPLE, "senate", src, overrides, fixes)
    reconcile.run(con, tmp_path / "none.json")
    row = con.execute("SELECT * FROM contest_final WHERE contest_id = '2020-sen-IA-2-gen'").fetchone()
    assert (row["dem_candidate"], row["rep_candidate"], row["agreement"]) == (
        "THERESA GREENFIELD",
        "JONI ERNST",
        "single source",
    )
    assert row["dem_margin_pct"] == round(100 * (754859 - 864997) / (864997 + 754859 + 36961), 2)
